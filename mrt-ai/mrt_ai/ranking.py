"""Explainable request-to-candidate ranking for the local trip pipeline."""
from __future__ import annotations

from mrt_ai.contracts.catalog import (
    Candidate,
    CandidateBatch,
    CandidateFitScore,
    CandidateRankingResponse,
)
from mrt_ai.retrieval.bm25 import BM25PlaceSearch, tokenize
from app.contracts import TripRequest


_INTEREST_GROUPS = (
    (
        {"природа", "лес", "лесной", "парк", "парк-отель", "озеро", "озера", "озёрный", "тропа", "заповедник", "заповедный", "птицы", "животные", "сад", "река", "водопад", "пейзаж"},
        {"ACTIVITY", "ATTRACTION"},
    ),
    (
        {"горы", "горный", "гора", "треккинг", "трекинг", "поход", "альпинизм", "скалолазание", "восхождение"},
        {"ACTIVITY", "ATTRACTION"},
    ),
    (
        {"море", "пляж", "побережье", "купание", "солнце", "курорт"},
        {"ACTIVITY", "ATTRACTION"},
    ),
    (
        {"озеро", "озера", "озёрный", "озерный", "рыбалка", "лодка", "каяк", "набережная"},
        {"ACTIVITY", "ATTRACTION"},
    ),
    (
        {"активный", "активность", "экстрим", "велосипед", "велопрогулка", "пешком", "квест", "спорт", "лыжи", "сноуборд", "сплав", "рафтинг"},
        {"ACTIVITY"},
    ),
    (
        {"музей", "музеи", "культура", "история", "искусство", "выставка", "театр", "архитектура", "памятник", "наследие", "ремесло", "традиции", "церковь", "монастырь"},
        {"ATTRACTION", "ACTIVITY", "GUIDE"},
    ),
    (
        {"гастрономия", "гастрономический", "еда", "кухня", "кафе", "ресторан", "дегустация", "дегустационный", "рынок", "фермерский", "местная кухня", "вино"},
        {"RESTAURANT", "ACTIVITY", "ATTRACTION"},
    ),
    (
        {"экскурсия", "экскурсии", "экскурсионный", "гид", "экскурсовод", "тур", "туристический маршрут"},
        {"GUIDE", "ACTIVITY", "ATTRACTION"},
    ),
    (
        {"семья", "семейный", "дети", "ребенок"},
        {"ATTRACTION", "ACTIVITY", "RESTAURANT", "HOTEL"},
    ),
)
_PACE_TERMS = {
    "active": {"активный", "экстрим", "велосипед", "пешком", "квест", "спорт", "тропа", "поход", "лыжи", "сноуборд", "сплав", "скалолазание"},
    "balanced": set(),
    "relaxed": {"спокойный", "расслабленный", "отдых", "прогулка"},
}
_FAMILY_TERMS = {"семья", "семейный", "дети", "ребенок"}


def _tokens(values: set[str]) -> set[str]:
    return {token for value in values for token in tokenize(value)}


def _expanded_interest(interest: str) -> tuple[set[str], set[str]]:
    interest_tokens = set(tokenize(interest))
    matching_groups = [
        (tokens, kinds)
        for tokens, kinds in _INTEREST_GROUPS
        if interest_tokens & _tokens(tokens)
    ]
    if not matching_groups:
        return interest_tokens, set()
    terms = set().union(*(tokens for tokens, _ in matching_groups))
    kinds = set().union(*(kinds for _, kinds in matching_groups))
    return interest_tokens | _tokens(terms), kinds


def _candidate_tokens(candidate: Candidate) -> set[str]:
    return set(tokenize(" ".join((candidate.name, candidate.description, *candidate.tags))))


class TripCandidateRanker:
    """Ranks candidates by relative lexical and structured-preference fit.

    The score is a transparent 0–100 ranking signal within this candidate batch,
    not a probability or a prediction of availability, quality, or price.
    """

    version = "trip-fit-bm25-v3"

    def rank(self, trip: TripRequest, batch: CandidateBatch) -> CandidateRankingResponse:
        if batch.status == "outside_coverage":
            return CandidateRankingResponse(
                status="outside_coverage",
                data_mode=batch.data_mode,
                snapshot_id=batch.snapshot_id,
                warnings=batch.warnings,
            )

        candidates = batch.candidates
        if trip.destination_region_id is not None:
            wrong_region = [
                candidate.object_id
                for candidate in candidates
                if candidate.region_id != trip.destination_region_id
            ]
            if wrong_region:
                raise ValueError("Кандидаты и направление поездки относятся к разным регионам.")
            candidates = [
                candidate for candidate in candidates
                if candidate.region_id == trip.destination_region_id
            ]

        excluded_terms = [set(tokenize(interest)) for interest in trip.excluded_interests]
        excluded_ids = []
        exclusion_reasons = {}
        eligible = []
        candidate_tokens: dict[str, set[str]] = {}
        for candidate in candidates:
            all_tokens = _candidate_tokens(candidate)
            if candidate.kind == "GUIDE" and trip.guide.required is False:
                excluded_ids.append(candidate.object_id)
                exclusion_reasons[candidate.object_id] = "guide_not_requested"
                continue
            if any(terms & all_tokens for terms in excluded_terms):
                excluded_ids.append(candidate.object_id)
                exclusion_reasons[candidate.object_id] = "excluded_interest"
                continue
            eligible.append(candidate)
            candidate_tokens[candidate.object_id] = all_tokens

        if not eligible:
            warnings = list(batch.warnings)
            if excluded_ids:
                warnings.append("Все объекты в каталоге исключены по нежелательным интересам.")
            elif not candidates:
                warnings.append("В переданном CandidateBatch нет объектов для ранжирования.")
            return CandidateRankingResponse(
                status="no_candidates",
                data_mode=batch.data_mode,
                snapshot_id=batch.snapshot_id,
                excluded_object_ids=excluded_ids,
                exclusion_reasons=exclusion_reasons,
                warnings=warnings,
            )

        query_parts = list(trip.interests)
        if trip.format.pace == "active":
            query_parts.append("активный отдых")
        elif trip.format.pace == "relaxed":
            query_parts.append("спокойный отдых")
        if trip.party.has_children:
            query_parts.append("семья дети")
        query = " ".join(query_parts).strip()
        lexical_hits = BM25PlaceSearch(eligible).search(query, len(eligible)) if query else []
        raw_scores = {hit.candidate.object_id: hit.score for hit in lexical_hits}
        matched_terms = {hit.candidate.object_id: hit.matched_terms for hit in lexical_hits}
        max_raw_score = max(raw_scores.values(), default=0.0)
        weights = {
            "interest_match": 0.50,
            "text_relevance": 0.30,
            "category_fit": 0.10,
            "pace_fit": 0.10,
            "family_fit": 0.10,
            "guide_fit": 0.10,
        }
        component_names = {"text_relevance"}
        if trip.interests:
            component_names.update({"interest_match", "category_fit"})
        if trip.format.pace:
            component_names.add("pace_fit")
        if trip.party.has_children:
            component_names.add("family_fit")
        if trip.guide.required is True:
            component_names.add("guide_fit")
        active_weights = {key: weights[key] for key in component_names}
        total_weight = sum(active_weights.values())
        normalized_weights = {
            key: weight / total_weight for key, weight in active_weights.items()
        }

        results = []
        for candidate in eligible:
            all_tokens = candidate_tokens[candidate.object_id]
            matched_interests = []
            interest_strengths = []
            interest_category_fits = []
            for interest in trip.interests:
                terms, preferred_kinds = _expanded_interest(interest)
                direct_terms = set(tokenize(interest))
                direct_match = bool(direct_terms & all_tokens)
                related_match = bool((terms - direct_terms) & all_tokens)
                if direct_match:
                    matched_interests.append(interest)
                    interest_strengths.append(1.0)
                    interest_category_fits.append(
                        1.0 if candidate.kind in preferred_kinds else 0.35
                    )
                elif related_match:
                    # A broad thematic association is useful, but must not count
                    # as an exact match (e.g. "museum" -> any cultural activity).
                    interest_strengths.append(0.25)
                    interest_category_fits.append(
                        0.25 if candidate.kind in preferred_kinds else 0.1
                    )
                else:
                    interest_strengths.append(0.0)
                    interest_category_fits.append(0.0)

            components = {}
            if trip.interests:
                components["interest_match"] = sum(interest_strengths) / len(trip.interests)
                components["category_fit"] = sum(interest_category_fits) / len(trip.interests)

            lexical = raw_scores.get(candidate.object_id, 0.0)
            components["text_relevance"] = lexical / max_raw_score if max_raw_score else 0.0

            if trip.format.pace:
                pace_terms = _tokens(_PACE_TERMS[trip.format.pace])
                components["pace_fit"] = (
                    1.0 if pace_terms & all_tokens else 0.0
                ) if pace_terms else 0.5
            if trip.party.has_children:
                components["family_fit"] = (
                    1.0 if _tokens(_FAMILY_TERMS) & all_tokens else 0.5
                )
            if trip.guide.required is True:
                components["guide_fit"] = 1.0 if candidate.kind == "GUIDE" else 0.0

            score = (
                100 * sum(components[key] * weight for key, weight in normalized_weights.items())
                if normalized_weights
                else 0.0
            )

            reasons = []
            if trip.interests:
                reasons.append(
                    f"Совпали интересы: {len(matched_interests)} из {len(trip.interests)}."
                )
            if matched_terms.get(candidate.object_id):
                reasons.append(
                    "BM25 нашёл слова запроса: " + ", ".join(matched_terms[candidate.object_id]) + "."
                )
            if "pace_fit" in components:
                reasons.append(
                    "Подходит темпу поездки." if components["pace_fit"] else
                    "Явных признаков выбранного темпа в карточке нет."
                )
            if "family_fit" in components:
                reasons.append(
                    "В карточке отмечена семейная тематика."
                    if components["family_fit"] == 1.0
                    else "Семейная пригодность объекта не подтверждена."
                )
            if "guide_fit" in components:
                reasons.append(
                    "Это карточка гида, которого запросил пользователь."
                    if components["guide_fit"] == 1.0
                    else "Пользователь запросил гида; эта карточка относится к другой категории."
                )
            if not reasons:
                reasons.append("В запросе недостаточно предпочтений для содержательного сравнения.")

            results.append(CandidateFitScore(
                candidate=candidate,
                score=round(score, 2),
                score_components={
                    key: round(value, 4) for key, value in components.items()
                },
                matched_interests=matched_interests,
                unmatched_interests=[
                    interest for interest in trip.interests
                    if interest not in matched_interests
                ],
                matched_terms=matched_terms.get(candidate.object_id, []),
                reasons=reasons,
            ))

        results.sort(key=lambda result: (-result.score, result.candidate.object_id))
        warnings = list(batch.warnings)
        warnings.append(
            "Score нормирован внутри текущего набора кандидатов: это не вероятность. "
            "Неизвестные цены, наличие услуг и переезды в ranking не оцениваются."
        )
        matched_interest_set = {
            interest for result in results for interest in result.matched_interests
        }
        unsupported_interests = [
            interest for interest in trip.interests
            if interest not in matched_interest_set
        ]
        if unsupported_interests:
            warnings.append(
                "В каталоге нет прямого совпадения по интересам: "
                + ", ".join(unsupported_interests)
                + ". Тематически близкие объекты могли получить только частичный score; уточните запрос."
            )
            if len({result.score for result in results}) == 1:
                warnings.append("Все кандидаты имеют одинаковый score; порядок карточек нейтральный и не является рекомендацией.")
        unscored_factors = []
        if trip.dates.start_date is not None:
            unscored_factors.append("seasonal_suitability")
        if trip.budget.amount_minor is not None:
            unscored_factors.append("budget_fit")
        if trip.party.total_count is not None:
            unscored_factors.append("group_capacity")
        if trip.transport.allowed_modes:
            unscored_factors.append("transport_fit")
        if unscored_factors:
            warnings.append(
                "Эти параметры сохранены, но не участвуют в score, потому что каталог не содержит нужных фактов: "
                + ", ".join(unscored_factors) + "."
            )
        return CandidateRankingResponse(
            status="ranked" if results else "no_candidates",
            data_mode=batch.data_mode,
            snapshot_id=batch.snapshot_id,
            score_weights={
                key: round(weight, 4) for key, weight in normalized_weights.items()
            },
            results=results,
            excluded_object_ids=sorted(excluded_ids),
            exclusion_reasons=exclusion_reasons,
            unscored_factors=unscored_factors,
            warnings=warnings,
        )


def rank_trip_candidates(
    trip: TripRequest,
    batch: CandidateBatch,
) -> CandidateRankingResponse:
    return TripCandidateRanker().rank(trip, batch)
