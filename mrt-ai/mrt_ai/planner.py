"""Build a provisional date-by-date proposal from ranked local candidates."""
from __future__ import annotations

from datetime import timedelta

from app.contracts import RoutePlannerRequest, TripRequest
from mrt_ai.contracts.catalog import (
    CandidateBatch,
    CandidateFitScore,
    RouteBudgetSummary,
    RouteDay,
    RouteItem,
    RouteProposal,
    RouteValidation,
    RouteValidationIssue,
)
from mrt_ai.ranking import rank_trip_candidates


class MrtAiRoutePlanner:
    def propose(self, trip: TripRequest, candidates: CandidateBatch) -> RouteProposal:
        if trip.destination_region_id is None:
            raise ValueError("Для построения маршрута нужно выбрать регион назначения.")
        if candidates.data_mode not in {"fixture", "cached"}:
            raise ValueError("Черновой планировщик принимает только явно отмеченные локальные snapshots.")
        if trip.dates.start_date is None:
            raise ValueError("Для построения маршрута укажите дату начала поездки.")
        if candidates.status == "outside_coverage":
            return self._empty_proposal(trip, candidates, "outside_coverage")

        ranked = rank_trip_candidates(trip, candidates)
        eligible = [
            result for result in ranked.results
            if result.score > 0
            and result.candidate.kind in {"ATTRACTION", "ACTIVITY", "RESTAURANT"}
        ]
        if not eligible:
            return self._empty_proposal(
                trip,
                candidates,
                "no_candidates",
                ranked_candidates=ranked.results,
                score_weights=ranked.score_weights,
                issue=RouteValidationIssue(
                    code="no_relevant_places",
                    severity="warning",
                    explanation="В текущем наборе нет мест, которые набрали ненулевой score по запросу.",
                    suggested_actions=["Уточнить интересы или расширить каталог подходящих объектов."],
                ),
            )

        end = trip.dates.end_date
        if end is None:
            duration = trip.dates.duration_days
            if duration is None:
                raise ValueError("Укажите дату окончания или длительность поездки.")
            end = trip.dates.start_date + timedelta(days=duration - 1)
        day_count = (end - trip.dates.start_date).days + 1
        if day_count < 1:
            raise ValueError("Дата окончания поездки должна быть не раньше даты начала.")

        offers_by_object = {offer.object_id: offer for offer in candidates.offers}
        days = []
        # Give each day one distinct place first, then add remaining places
        # without inventing travel times or opening-hour feasibility.
        capacity = {"relaxed": 1, "balanced": 2, "active": 3}.get(trip.format.pace, 2)
        allocations = [[] for _ in range(day_count)]
        for result in eligible:
            target = next((items for items in allocations if not items), None)
            if target is None:
                target = next((items for items in allocations if len(items) < capacity), None)
            if target is None:
                break
            target.append(result)
        for index in range(day_count):
            current_date = trip.dates.start_date + timedelta(days=index)
            items = []
            for order, result in enumerate(allocations[index], start=1):
                candidate = result.candidate
                offer = offers_by_object.get(candidate.object_id)
                items.append(RouteItem(
                    item_id=f"route:{trip.destination_region_id}:{current_date.isoformat()}:{order}",
                    object_id=candidate.object_id,
                    kind=candidate.kind,
                    offer_id=offer.offer_id if offer else None,
                    start_at=None,
                    end_at=None,
                    visit_duration_minutes=candidate.visit_duration_minutes,
                    order=order,
                    relevance_score=result.score,
                    coordinates=candidate.coordinates,
                    pinned=False,
                    cost_line_ids=[],
                ))
            days.append(RouteDay(
                day_id=f"day:{index + 1}",
                date=current_date,
                timezone="Europe/Moscow",
                items=items,
            ))

        candidate_by_id = {candidate.object_id: candidate for candidate in candidates.candidates}
        offer_ids_by_kind = {
            kind: [
                offer.offer_id for offer in candidates.offers
                if candidate_by_id.get(offer.object_id)
                and candidate_by_id[offer.object_id].kind == kind
            ]
            for kind in ("TRANSPORT", "HOTEL", "GUIDE")
        }
        unscheduled_days = sum(not items for items in allocations)
        issues = [RouteValidationIssue(
            code="source_not_operationally_verified",
            severity="warning",
            item_ids=[item.item_id for day in days for item in day.items],
            explanation=self._source_warning(candidates.data_mode),
            suggested_actions=["Проверить существование объекта, график, доступность, цены и переезды перед публикацией."],
        )]
        if unscheduled_days:
            issues.append(RouteValidationIssue(
                code="insufficient_candidate_coverage",
                severity="warning",
                item_ids=[],
                explanation=f"Для {unscheduled_days} дн. не найдено отдельного релевантного объекта; места не повторяются автоматически.",
                suggested_actions=["Добавить объекты в каталог или вручную выбрать повторный визит."],
            ))

        return RouteProposal(
            proposal_id=f"proposal:{trip.destination_region_id}:{trip.dates.start_date.isoformat()}:{day_count}",
            trip_version=1,
            candidate_snapshot_id=candidates.snapshot_id,
            ranking_version=ranked.ranking_version,
            score_weights=ranked.score_weights,
            ranked_candidates=ranked.results,
            status="provisional",
            region=trip.destination_region_id,
            transport_offer_ids=offer_ids_by_kind["TRANSPORT"],
            hotel_offer_ids=offer_ids_by_kind["HOTEL"],
            guide_offer_ids=offer_ids_by_kind["GUIDE"] if trip.guide.required else [],
            days=days,
            budget_summary=self._unknown_budget(trip),
            validation=RouteValidation(
                status="provisional",
                validator="trip-fit-bm25-v3+fixture-planner",
                input_version=1,
                issues=issues,
            ),
            explanations=[
                "Кандидаты ранжированы по соответствию интересам, BM25-релевантности и указанным предпочтениям.",
                "Score относительный для текущего набора и не является вероятностью.",
                "План — распределение по датам, не оптимизированный маршрут и не подтверждённая услуга.",
                "Порядок точек внутри дня предварительный: время посещения и переезды не рассчитаны.",
            ],
        )

    def _empty_proposal(
        self,
        trip: TripRequest,
        candidates: CandidateBatch,
        status: str,
        ranked_candidates: list[CandidateFitScore] | None = None,
        score_weights: dict[str, float] | None = None,
        issue: RouteValidationIssue | None = None,
    ) -> RouteProposal:
        issues = [issue] if issue else []
        if status == "outside_coverage":
            issues.append(RouteValidationIssue(
                code="outside_coverage",
                severity="warning",
                explanation="Для выбранного региона нет покрытия в текущем каталоге.",
                suggested_actions=["Выбрать пилотный регион или добавить данные."],
            ))
        return RouteProposal(
            proposal_id=f"proposal:{trip.destination_region_id}:draft",
            trip_version=1,
            candidate_snapshot_id=candidates.snapshot_id,
            ranking_version="trip-fit-bm25-v3",
            score_weights=score_weights or {},
            ranked_candidates=ranked_candidates or [],
            status=status,
            region=trip.destination_region_id or "",
            budget_summary=self._unknown_budget(trip),
            validation=RouteValidation(
                status="provisional",
                validator="trip-fit-bm25-v3+fixture-planner",
                input_version=1,
                issues=issues,
            ),
            explanations=["Стоимость, наличие услуг и возможность построить маршрут не подтверждены."],
        )

    @staticmethod
    def _unknown_budget(trip: TripRequest) -> RouteBudgetSummary:
        return RouteBudgetSummary(
            known_total_minor=0,
            currency="RUB",
            line_items=[],
            unknown_categories=["activities", "food", "transport", "hotel", "guide"],
            budget_limit_minor=trip.budget.amount_minor,
            budget_scope=trip.budget.period or "trip",
            complete=False,
            within_budget=None,
            calculated_by="synthetic-demo-planner",
        )

    @staticmethod
    def _source_warning(data_mode: str) -> str:
        if data_mode == "fixture":
            return (
                "Объекты и координаты синтетические. Стоимость, доступность, "
                "часы работы и переезды не подтверждены."
            )
        return (
            "Это объекты, внесённые участниками OpenStreetMap; snapshot не подтверждает "
            "их текущее существование, часы работы, цены, доступность или переезды."
        )


def build_route_proposal(trip: TripRequest, candidates: CandidateBatch) -> RouteProposal:
    return MrtAiRoutePlanner().propose(trip, candidates)


def build_route_proposal_from_request(request: RoutePlannerRequest) -> RouteProposal:
    return build_route_proposal(request.trip, request.candidates)
