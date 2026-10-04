from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Header, HTTPException
from pydantic import ValidationError

from app.contracts import Edit, IntentProbe, Message, ParseRequest, RecommendRequest, SelectRegion, SessionCreate, SessionState, Turn
from app.catalog import CatalogUnavailable, RegionCatalog
from app.backend import BackendError, BackendTrip, BackendTripsClient
from mrt_ai.contracts.catalog import CandidateBatch, CandidateQuery, Catalog, PlaceSearchRequest, PlaceSearchResponse, RegionRecommendations
from app.providers import LocalCandidateProvider
from mrt_ai.retrieval.encoders.sbert import EmbeddingModelUnavailable, LocalSbertPlaceSearch
from mrt_ai.retrieval.pipeline import MrtAiRetrievalPipeline
from app.dialogue import QUESTIONS, get, missing, parse, reduce_trip
from app.store import Conflict, Store

ROOT = Path(__file__).resolve().parent.parent


def create_app(database: Path | None = None, clock=None, catalog_path: Path | None = None,
               backend_url: str | None = None, backend_transport_factory=None,
               embedding_searcher: LocalSbertPlaceSearch | None = None,
               enable_intent_test: bool = False, intent_classifier=None):
    api = FastAPI(title="mrt-ai · Миша", version="0.3.0", description="Локальная ML-система mrt-ai и интеллектуальный помощник Миша для подбора поездок. Реальные услуги пока не подключены.")
    api.state.store = Store(database or ROOT / "data/runtime/sessions.sqlite3")
    now = clock or (lambda: datetime.now(timezone.utc))
    catalog = RegionCatalog(catalog_path or ROOT / "data/normalized/catalog.json")
    provider = LocalCandidateProvider(catalog, ROOT / "data/fixtures/places.json")
    backend = BackendTripsClient(backend_url, backend_transport_factory)
    retrieval_pipeline = MrtAiRetrievalPipeline(embedding_searcher or LocalSbertPlaceSearch(
        ROOT / "models" / "embeddings" / "sbert_large_nlu_ru"
    ))
    api.state.intent_classifier = intent_classifier

    def backend_error(error):
        raise HTTPException(status_code=error.status_code, detail={"code": error.code, "message": error.message}) from error

    @api.get("/health")
    def health():
        try:
            snapshot = catalog.load().snapshot_id
        except CatalogUnavailable:
            snapshot = None
        return {"status": "ok", "stage": "region-catalog", "parser": "rules-v1", "providers_connected": False, "backend_configured": backend.configured, "catalog_ready": snapshot is not None, "catalog_snapshot_id": snapshot}

    @api.get("/v1/backend/trips", response_model=list[BackendTrip])
    def backend_trips(authorization: str | None = Header(default=None)):
        try:
            return backend.list_trips(authorization)
        except BackendError as error:
            backend_error(error)

    @api.get("/v1/backend/trips/{trip_id}", response_model=BackendTrip)
    def backend_trip(trip_id: int, authorization: str | None = Header(default=None)):
        try:
            return backend.get_trip(trip_id, authorization)
        except BackendError as error:
            backend_error(error)

    @api.get("/v1/catalog/regions", response_model=Catalog)
    def regions():
        try:
            return catalog.load()
        except CatalogUnavailable as error:
            raise HTTPException(503, detail={"code": "CATALOG_UNAVAILABLE", "message": str(error)})

    @api.post("/v1/recommend", response_model=RegionRecommendations)
    def recommend(body: RecommendRequest):
        return catalog.recommend(body.trip, today=now().astimezone(ZoneInfo("Europe/Moscow")).date())

    @api.post("/v1/candidates/query", response_model=CandidateBatch)
    def candidates(body: CandidateQuery):
        try:
            return provider.query(body)
        except (CatalogUnavailable, OSError, ValueError) as error:
            raise HTTPException(503, detail={"code": "PROVIDER_UNAVAILABLE", "message": "Локальный источник недоступен. Проверьте импорт и fixtures."}) from error

    @api.post("/v1/search/places", response_model=PlaceSearchResponse)
    def search_places(body: PlaceSearchRequest):
        try:
            batch = provider.query(CandidateQuery(
                region_id=body.region_id,
                data_mode=body.data_mode,
                kinds=body.kinds,
                excluded_tags=body.excluded_tags,
            ))
            ranking_version = retrieval_pipeline.version_for(body.ranking_method)
            if batch.status == "outside_coverage":
                return PlaceSearchResponse(
                    status="outside_coverage",
                    data_mode="fixture",
                    ranking_version=ranking_version,
                    snapshot_id=batch.snapshot_id,
                    warnings=batch.warnings,
                )
            ranked = retrieval_pipeline.search(
                body.query,
                batch.candidates,
                body.top_k,
                body.ranking_method,
            )
            return PlaceSearchResponse(
                status="partial" if ranked.results else "no_candidates",
                data_mode="fixture",
                ranking_version=ranked.ranking_version,
                snapshot_id=batch.snapshot_id,
                results=ranked.results,
                warnings=batch.warnings + [ranked.warning],
            )
        except EmbeddingModelUnavailable as error:
            raise HTTPException(status_code=503, detail={
                "code": "EMBEDDING_MODEL_UNAVAILABLE",
                "message": str(error),
            }) from error
        except (CatalogUnavailable, OSError, ValueError) as error:
            raise HTTPException(status_code=503, detail={"code": "SEARCH_UNAVAILABLE", "message": "Локальный каталог поиска недоступен или повреждён."}) from error

    @api.post("/v1/sessions", response_model=SessionState, status_code=201)
    def create_session(body: SessionCreate):
        return api.state.store.create(body.timezone)

    @api.get("/v1/sessions/{session_id}", response_model=SessionState)
    def get_session(session_id: str):
        try:
            state = api.state.store.get(session_id)
            # Recompute against the current snapshot; old persisted results cannot stay fresh.
            state.recommendations = catalog.recommend(state.trip, state.state_version, now().astimezone(ZoneInfo(state.timezone)).date())
            return state
        except KeyError:
            raise HTTPException(404, detail={"code": "SESSION_NOT_FOUND", "message": "Сессия не найдена"})

    @api.post("/v1/parse")
    def parse_only(body: ParseRequest):
        result = parse(body.message, body.state, body.pending_question, body.reference_datetime, body.timezone)
        try:
            proposed = reduce_trip(body.state, result["updates"], body.reference_datetime.astimezone(ZoneInfo(body.timezone)).date())
        except (ValidationError, ValueError) as error:
            raise HTTPException(422, detail={"code": "INVALID_TRIP", "message": str(error)})
        return {**result, "trip": proposed, "missing_parameters": missing(proposed)}

    if enable_intent_test:
        @api.post("/v1/dev/intent")
        def test_intent(body: IntentProbe):
            classifier = api.state.intent_classifier
            if classifier is None:
                try:
                    from mrt_ai.nlp.intent.classifier import MrtAiIntentClassifier
                    classifier = MrtAiIntentClassifier.load(
                        ROOT / "models" / "classifiers" / "misha-intent-rubert-tiny2"
                    )
                except ImportError as error:
                    raise HTTPException(503, detail={
                        "code": "INTENT_DEPENDENCIES_UNAVAILABLE",
                        "message": "Для тестирования RuBERT установите зависимости: python -m pip install -r requirements-ml.txt",
                    }) from error
                except FileNotFoundError as error:
                    raise HTTPException(503, detail={
                        "code": "INTENT_MODEL_UNAVAILABLE",
                        "message": "Локальный intent checkpoint не найден. Выполните обучение по инструкции в README.md.",
                    }) from error
                except (OSError, RuntimeError, ValueError) as error:
                    raise HTTPException(503, detail={
                        "code": "INTENT_MODEL_INVALID",
                        "message": f"Не удалось загрузить локальный intent checkpoint: {error}",
                    }) from error
                api.state.intent_classifier = classifier

            trip_data = body.state.model_dump(exclude_defaults=True, mode="json")
            previous_trip = "partial" if trip_data else "empty"
            scores = classifier.predict_scores(
                body.message,
                body.pending_question,
                previous_trip,
            )
            rules = parse(
                body.message,
                body.state,
                body.pending_question,
                now(),
                "Europe/Moscow",
            )
            return {
                "model": "mrt-ai-misha-intent-rubert-tiny2",
                "threshold": classifier.threshold,
                "classifier": [
                    {**row, "selected": row["score"] >= classifier.threshold}
                    for row in scores
                ],
                "rules_v1": rules["intents"],
            }

    def apply_turn(state, request, manual=False):
        instant = now()
        if len(state.messages) >= 400:
            raise ValueError("Достигнут лимит локального диалога. Экспортируйте поездку и начните новую.")
        result = {"updates": request.updates, "intents": ["CHANGE_TRIP"], "notices": []} if manual else parse(request.message, state.trip, state.pending_question, instant, state.timezone)
        before = state.trip.model_dump(mode="json")
        try:
            proposed = reduce_trip(state.trip, result["updates"], instant.astimezone(ZoneInfo(state.timezone)).date())
        except (ValidationError, ValueError) as error:
            if manual:
                raise
            # No partial update from an inconsistent message. Keep the conversation usable.
            proposed = state.trip
            result["updates"] = {}
            result["notices"].append("Параметры не изменены: " + str(error).split("\n")[0])
        if proposed.destination:
            try:
                region = catalog.resolve(catalog.load(), proposed.destination)
                proposed.destination_region_id = region.region_id if region else None
            except CatalogUnavailable:
                proposed.destination_region_id = None
        changes = []
        after = proposed.model_dump(mode="json")
        paths = set(result["updates"]) | {"mode", "destination", "destination_region_id", "dates.end_date", "dates.duration_days", "party.children_ages"}
        for path in sorted(paths):
            old, new = get(before, path), get(after, path)
            if old != new:
                changes.append({"field": path, "before": old, "after": new})
                state.slot_metadata[path] = {"source": "manual" if manual else "user" if path in result["updates"] else "derived", "request_id": request.request_id, "parser": "rules-v1"}
        state.trip = proposed
        state.state_version += 1
        state.missing_parameters = missing(proposed)
        state.pending_question = state.missing_parameters[0] if state.missing_parameters else None
        state.status = "needs_clarification" if state.pending_question else "ready_for_search"
        state.recommendations = catalog.recommend(proposed, state.state_version, instant.astimezone(ZoneInfo(state.timezone)).date())
        answer = "Параметры обновлены." if changes else "Пока не удалось выделить новые параметры. Уточните пожелания следующим сообщением."
        if result["notices"]:
            answer += "\n\n" + "\n".join(result["notices"])
        if state.pending_question:
            answer += "\n\n" + QUESTIONS[state.pending_question]
        else:
            if state.recommendations.options:
                names = ", ".join(option.name for option in state.recommendations.options)
                answer += f"\n\nПо карточкам региона вашим пожеланиям соответствуют: {names}. Напишите, какое направление выбираете. Стоимость поездки и наличие услуг пока не проверены."
            else:
                answer += "\n\n" + " ".join(state.recommendations.warnings or ["Для подбора обновите дату поездки."])
        user_message = (
            request.message or "Параметры изменены через API."
            if manual else request.message
        )
        state.messages.extend([Message(role="user", text=user_message), Message(role="assistant", text=answer)])
        return {"schema_version": "1.0", "request_id": request.request_id, "reference_datetime": instant.isoformat(), "state": state, "changes": changes, "intents": result["intents"], "notices": result["notices"], "options": [option.model_dump(mode="json") for option in state.recommendations.options]}

    def mutate(session_id, request, manual=False, operation=None):
        try:
            return api.state.store.mutate(session_id, request, "select_region" if operation else "edit" if manual else "turn", operation or (lambda state: apply_turn(state, request, manual)))
        except KeyError:
            raise HTTPException(404, detail={"code": "SESSION_NOT_FOUND", "message": "Сессия не найдена"})
        except Conflict as error:
            raise HTTPException(409, detail={"code": "VERSION_CONFLICT", "message": str(error)})
        except (ValidationError, ValueError) as error:
            raise HTTPException(422, detail={"code": "INVALID_TRIP", "message": str(error)})

    @api.post("/v1/sessions/{session_id}/turns")
    def turn(session_id: str, body: Turn):
        return mutate(session_id, body)

    @api.patch("/v1/sessions/{session_id}/trip")
    def edit(session_id: str, body: Edit):
        return mutate(session_id, body, manual=True)

    @api.post("/v1/sessions/{session_id}/select-region")
    def select_region(session_id: str, body: SelectRegion):
        def operation(state):
            result = catalog.recommend(state.trip, state.state_version, now().astimezone(ZoneInfo(state.timezone)).date())
            if result.catalog_snapshot_id != body.catalog_snapshot_id:
                raise Conflict("Каталог изменился или недоступен. Обновите варианты.")
            chosen = next((option for option in result.options if option.region_id == body.region_id), None)
            if not chosen:
                raise ValueError("Направление отсутствует среди текущих рекомендаций")
            return apply_turn(state, Edit(request_id=body.request_id, expected_state_version=body.expected_state_version,
                                         updates={"mode": "PLAN", "destination": chosen.name}), manual=True)
        return mutate(session_id, body, operation=operation)

    return api
