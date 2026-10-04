"""Provider port: reference/manual and explicit synthetic adapters, no live APIs."""
import json
from pathlib import Path
from typing import Protocol

from app.catalog import RegionCatalog, normalized
from app.catalog_import import digest
from mrt_ai.contracts.catalog import Candidate, CandidateBatch, CandidateQuery, FixturePlaceCatalog, Offer, Source


class CandidateProvider(Protocol):
    def query(self, request: CandidateQuery) -> CandidateBatch: ...


class LocalCandidateProvider:
    def __init__(self, catalog: RegionCatalog, fixtures: Path):
        self.catalog = catalog
        self.fixtures = fixtures

    def query(self, request):
        catalog = self.catalog.load()
        fingerprint = digest(request.model_dump(mode="json"))
        base = {"provider": "local-fixtures" if request.data_mode == "fixture" else "user-region-cards",
                "data_mode": request.data_mode, "query_fingerprint": fingerprint, "snapshot_id": catalog.snapshot_id}
        region = next((r for r in catalog.regions if r.region_id == request.region_id), None)
        if not region:
            return CandidateBatch(**base, status="outside_coverage", unavailable_kinds=sorted(set(request.kinds)), warnings=["Регион отсутствует в пилотном каталоге."])
        if request.data_mode == "manual":
            candidates = []
            if "REGION" in request.kinds:
                candidates = [Candidate(object_id=region.region_id, kind="REGION", region_id=region.region_id, name=region.name,
                                        description=region.description, tags=region.tags, source=region.source)]
            return CandidateBatch(**base, status="partial" if candidates else "no_candidates", candidates=candidates,
                                  unavailable_kinds=sorted(set(request.kinds) - {c.kind for c in candidates}),
                                  warnings=["Карточки описывают регионы. Они не содержат проверенных предложений отелей, билетов, ресторанов или гидов."])
        try:
            fixture_catalog = FixturePlaceCatalog.model_validate_json(self.fixtures.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise ValueError("Синтетический каталог объектов недоступен или имеет неверный формат.") from error
        if any(candidate.region_id not in {item.region_id for item in catalog.regions} for candidate in fixture_catalog.candidates):
            raise ValueError("В синтетическом каталоге объекта указан регион вне доступного каталога.")
        base["snapshot_id"] = digest({"catalog": catalog.snapshot_id, "fixtures": fixture_catalog.model_dump(mode="json")})
        excluded = {normalized(tag) for tag in request.excluded_tags}
        candidates = [
            candidate for candidate in fixture_catalog.candidates
            if candidate.region_id == region.region_id
            and candidate.kind in request.kinds
            and not excluded.intersection(normalized(tag) for tag in candidate.tags)
        ]
        offers = [Offer(offer_id=c.object_id + ":offer", object_id=c.object_id, query_fingerprint=fingerprint, data_mode="fixture") for c in candidates]
        return CandidateBatch(**base, status="partial" if candidates else "no_candidates", candidates=candidates, offers=offers,
                              unavailable_kinds=sorted(set(request.kinds) - {c.kind for c in candidates}),
                              warnings=["ДЕМО: все места, расписания и координаты вымышленные; цены и доступность неизвестны. Бронирование и реальная навигация невозможны."])
