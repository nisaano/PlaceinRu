"""Provider port: reference/manual and explicit synthetic adapters, no live APIs."""
import json
from pathlib import Path
from typing import Protocol

from app.catalog import RegionCatalog, normalized
from app.catalog_import import digest
from mrt_ai.contracts.catalog import (
    Candidate,
    CandidateBatch,
    CandidateQuery,
    FixturePlaceCatalog,
    OSMPlacesSnapshot,
    WikidataPlacesSnapshot,
    Offer,
    Source,
)


class CandidateProvider(Protocol):
    def query(self, request: CandidateQuery) -> CandidateBatch: ...


class LocalCandidateProvider:
    def __init__(self, catalog: RegionCatalog, fixtures: Path, osm_places: Path | None = None,
                 wikidata_places: Path | None = None):
        self.catalog = catalog
        self.fixtures = fixtures
        self.osm_places = osm_places
        self.wikidata_places = wikidata_places

    def query(self, request):
        catalog = self.catalog.load()
        fingerprint = digest(request.model_dump(mode="json"))
        provider_name = {
            "fixture": "local-fixtures",
            "cached": "OpenStreetMap",
            "manual": "user-region-cards",
        }[request.data_mode]
        base = {"provider": provider_name,
                "data_mode": request.data_mode, "query_fingerprint": fingerprint, "snapshot_id": catalog.snapshot_id}
        region = next((r for r in catalog.regions if r.region_id == request.region_id), None)
        excluded = {normalized(tag) for tag in request.excluded_tags}
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
        if request.data_mode == "cached":
            snapshots = []
            if self.osm_places is not None and self.osm_places.is_file():
                try:
                    snapshots.append(OSMPlacesSnapshot.model_validate_json(
                        self.osm_places.read_text(encoding="utf-8")
                    ))
                except (OSError, ValueError) as error:
                    raise ValueError("OpenStreetMap snapshot is invalid; re-import the source.") from error
            if self.wikidata_places is not None and self.wikidata_places.is_file():
                try:
                    snapshots.append(WikidataPlacesSnapshot.model_validate_json(
                        self.wikidata_places.read_text(encoding="utf-8")
                    ))
                except (OSError, ValueError) as error:
                    raise ValueError("Wikidata snapshot is invalid; re-import the source.") from error
            if not snapshots:
                raise ValueError(
                    "No cached place snapshot is available. Run scripts.import_wikidata_places "
                    "or scripts.import_osm_places."
                )
            known_regions = {item.region_id for item in catalog.regions}
            for snapshot in snapshots:
                if any(candidate.region_id not in known_regions for candidate in snapshot.candidates):
                    raise ValueError(f"{snapshot.provider} snapshot contains an unknown region.")
            if len(snapshots) == 1:
                base["snapshot_id"] = snapshots[0].snapshot_id
            else:
                base["snapshot_id"] = digest({"snapshots": sorted(s.snapshot_id for s in snapshots)})
            base["provider"] = "+".join(sorted(snapshot.provider for snapshot in snapshots))
            source_candidates = [candidate for snapshot in snapshots for candidate in snapshot.candidates]
            candidates = [
                candidate for candidate in source_candidates
                if candidate.region_id == region.region_id
                and candidate.kind in request.kinds
                and not excluded.intersection(normalized(tag) for tag in candidate.tags)
            ]
            offers = [
                Offer(
                    offer_id=candidate.object_id + ":offer",
                    object_id=candidate.object_id,
                    query_fingerprint=fingerprint,
                    data_mode="cached",
                )
                for candidate in candidates
            ]
            warnings = []
            for snapshot in snapshots:
                warnings.append(f"Source: {snapshot.attribution}")
                if isinstance(snapshot, OSMPlacesSnapshot):
                    warnings.append(
                        f"OSM snapshot retrieved {snapshot.retrieved_at.isoformat()}, "
                        f"OSM data timestamp {snapshot.osm_data_timestamp.isoformat()}; "
                        "contributor tags do not verify current existence, hours, price, or access."
                    )
                else:
                    warnings.append(
                        "Wikidata categories and coordinates are contributor-reported; "
                        "opening hours, price, current existence, and access were not verified."
                    )
            return CandidateBatch(
                **base,
                status="partial" if candidates else "no_candidates",
                candidates=candidates,
                offers=offers,
                unavailable_kinds=sorted(set(request.kinds) - {candidate.kind for candidate in candidates}),
                warnings=warnings,
            )
        try:
            fixture_catalog = FixturePlaceCatalog.model_validate_json(self.fixtures.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise ValueError("Синтетический каталог объектов недоступен или имеет неверный формат.") from error
        if any(candidate.region_id not in {item.region_id for item in catalog.regions} for candidate in fixture_catalog.candidates):
            raise ValueError("В синтетическом каталоге объекта указан регион вне доступного каталога.")
        base["snapshot_id"] = digest({"catalog": catalog.snapshot_id, "fixtures": fixture_catalog.model_dump(mode="json")})
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
