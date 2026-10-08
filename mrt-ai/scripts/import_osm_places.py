"""Download named Moscow and Moscow Oblast places from OpenStreetMap Overpass."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from mrt_ai.contracts.catalog import (
    Candidate,
    Coordinates,
    OSMPlacesSnapshot,
    OSMRegionImport,
    Source,
)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / "data" / "normalized" / "osm-places.json"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_FALLBACK_URLS = (
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)
OSM_COPYRIGHT = "https://www.openstreetmap.org/copyright"
ODBL_LICENSE = "https://opendatacommons.org/licenses/odbl/1-0/"
ATTRIBUTION = f"© OpenStreetMap contributors ({OSM_COPYRIGHT}); data available under ODbL 1.0."
PROVIDER_KEYS = {
    "ru:region:77": {
        "name": "Москва",
        "relation_id": 102269,
        "area_id": 3600102269,
    },
    "ru:region:50": {
        "name": "Московская область",
        "relation_id": 51490,
        "area_id": 3600051490,
    },
}
CATEGORY_TAGS = (
    ("tourism", "museum", "ATTRACTION", ("музеи", "культура", "история")),
    ("leisure", "park", "ACTIVITY", ("парк", "природа", "прогулка")),
    ("amenity", "restaurant", "RESTAURANT", ("ресторан", "еда", "гастрономия")),
)
PRESERVED_TAGS = {
    "name",
    "name:ru",
    "name:en",
    "tourism",
    "leisure",
    "amenity",
    "cuisine",
    "opening_hours",
    "wheelchair",
    "outdoor_seating",
    "addr:city",
    "addr:suburb",
    "addr:street",
    "addr:housenumber",
    "addr:postcode",
}


def build_query(area_id: int) -> str:
    return (
        "[out:json][timeout:180];\n"
        f"area({area_id})->.searchArea;\n"
        "(\n"
        '  nwr(area.searchArea)["tourism"="museum"]["name"];\n'
        '  nwr(area.searchArea)["leisure"="park"]["name"];\n'
        '  nwr(area.searchArea)["amenity"="restaurant"]["name"];\n'
        ");\n"
        "out center tags;"
    )


def fetch_overpass(query: str, attempts_per_endpoint: int = 1) -> bytes:
    body = urlencode({"data": query}).encode("utf-8")
    retryable_statuses = {429, 500, 502, 503, 504}
    endpoint_errors = []
    for endpoint in (OVERPASS_URL, *OVERPASS_FALLBACK_URLS):
        for attempt in range(attempts_per_endpoint):
            request = Request(
                endpoint,
                data=body,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "User-Agent": "mrt-ai/1.0 (local OpenStreetMap place snapshot importer)",
                },
                method="POST",
            )
            try:
                with urlopen(request, timeout=90) as response:
                    payload = response.read()
                parsed = json.loads(payload)
                if not isinstance(parsed.get("elements"), list):
                    raise RuntimeError("Overpass response has no elements array")
                return payload
            except HTTPError as error:
                endpoint_errors.append(f"{endpoint}: HTTP {error.code}")
                if error.code not in retryable_statuses:
                    break
            except (TimeoutError, URLError) as error:
                endpoint_errors.append(f"{endpoint}: {error}")
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise RuntimeError("Overpass API returned invalid JSON data") from error
            if attempt + 1 < attempts_per_endpoint:
                time.sleep(2 ** (attempt + 1))
        time.sleep(2)
    raise RuntimeError(
        "OpenStreetMap Overpass endpoints are unavailable: " + "; ".join(endpoint_errors)
    )


def candidate_from_element(element: dict, region_id: str, payload_hash: str, source_file: str, checked_at: datetime) -> Candidate | None:
    tags = element.get("tags", {})
    name = (tags.get("name") or tags.get("name:ru") or tags.get("name:en") or "").strip()
    if not name:
        return None

    category = next(
        (
            (kind, semantic_tags)
            for key, value, kind, semantic_tags in CATEGORY_TAGS
            if tags.get(key) == value
        ),
        None,
    )
    if category is None:
        return None
    kind, semantic_tags = category

    coordinates = (
        {"lat": element["lat"], "lon": element["lon"]}
        if "lat" in element and "lon" in element
        else element.get("center")
    )
    if not coordinates or "lat" not in coordinates or "lon" not in coordinates:
        return None

    osm_type = element.get("type")
    osm_id = element.get("id")
    if osm_type not in {"node", "way", "relation"} or not isinstance(osm_id, int):
        return None

    source_tags = {
        key: str(tags[key])
        for key in PRESERVED_TAGS
        if key in tags and isinstance(tags[key], (str, int, float))
    }
    if tags.get("cuisine"):
        semantic_tags = (*semantic_tags, *[
            part.strip().replace("_", " ")
            for part in str(tags["cuisine"]).split(";")
            if part.strip()
        ])
    verified_tags = [
        f"{key}={tags[key]}"
        for key in ("tourism", "leisure", "amenity")
        if key in tags
    ]
    descriptive_tags = [
        f"{key}={source_tags[key]}"
        for key in ("cuisine", "opening_hours", "wheelchair", "outdoor_seating")
        if key in source_tags
    ]
    description = "OpenStreetMap: " + "; ".join(verified_tags + descriptive_tags)
    if not descriptive_tags:
        description += "; дополнительные свойства не указаны."

    return Candidate(
        object_id=f"osm:{osm_type}:{osm_id}",
        kind=kind,
        region_id=region_id,
        name=name,
        description=description,
        tags=list(dict.fromkeys(semantic_tags)),
        coordinates=Coordinates(latitude=coordinates["lat"], longitude=coordinates["lon"]),
        opening_hours=source_tags.get("opening_hours"),
        source_tags=source_tags,
        source=Source(
            provider="OpenStreetMap",
            source_file=source_file,
            source_url=f"https://www.openstreetmap.org/{osm_type}/{osm_id}",
            source_sha256=payload_hash,
            data_mode="cached",
            verification="provider_reported",
            license_reference=f"Open Database License (ODbL) 1.0: {ODBL_LICENSE}",
            attribution=ATTRIBUTION,
            checked_at=checked_at,
        ),
    )


def canonical_hash(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_snapshot(region_payloads: dict[str, bytes], output: Path, retrieved_at: datetime) -> OSMPlacesSnapshot:
    candidates = []
    imports = []
    osm_timestamps = []
    seen_object_ids = set()
    source_file = output.resolve().relative_to(ROOT).as_posix()

    for region_id, payload in region_payloads.items():
        region = PROVIDER_KEYS[region_id]
        parsed = json.loads(payload)
        metadata = parsed.get("osm3s", {})
        osm_timestamp = datetime.fromisoformat(
            metadata["timestamp_osm_base"].replace("Z", "+00:00")
        )
        osm_timestamps.append(osm_timestamp)
        payload_hash = hashlib.sha256(payload).hexdigest()
        query_hash = hashlib.sha256(build_query(region["area_id"]).encode("utf-8")).hexdigest()
        region_candidates = []
        skipped_without_coordinates = 0
        skipped_duplicate_ids = 0

        for element in parsed["elements"]:
            candidate = candidate_from_element(
                element,
                region_id,
                payload_hash,
                source_file,
                retrieved_at,
            )
            if candidate is None:
                skipped_without_coordinates += 1
            elif candidate.object_id in seen_object_ids:
                skipped_duplicate_ids += 1
            else:
                region_candidates.append(candidate)
                seen_object_ids.add(candidate.object_id)

        if skipped_without_coordinates or skipped_duplicate_ids:
            print(
                f"{region['name']}: {len(parsed['elements'])} source elements; "
                f"skipped {skipped_without_coordinates} unnamed/unmapped/coordinate-less "
                f"and {skipped_duplicate_ids} already assigned elements"
            )
        candidates.extend(region_candidates)
        imports.append(OSMRegionImport(
            region_id=region_id,
            name=region["name"],
            relation_id=region["relation_id"],
            area_id=region["area_id"],
            query_sha256=query_hash,
            element_count=len(region_candidates),
        ))

    payload = {
        "schema_version": "1.0",
        "data_mode": "cached",
        "provider": "OpenStreetMap",
        "license_reference": f"Open Database License (ODbL) 1.0: {ODBL_LICENSE}",
        "attribution": ATTRIBUTION,
        "retrieved_at": retrieved_at,
        "osm_data_timestamp": min(osm_timestamps),
        "regions": imports,
        "candidates": candidates,
    }
    payload["snapshot_id"] = canonical_hash({
        "schema_version": payload["schema_version"],
        "data_mode": payload["data_mode"],
        "provider": payload["provider"],
        "license_reference": payload["license_reference"],
        "attribution": payload["attribution"],
        "retrieved_at": retrieved_at.isoformat(),
        "osm_data_timestamp": min(osm_timestamps).isoformat(),
        "regions": [item.model_dump(mode="json") for item in imports],
        "candidates": [item.model_dump(mode="json") for item in candidates],
    })
    snapshot = OSMPlacesSnapshot.model_validate(payload)
    if not snapshot.candidates:
        raise ValueError("The Overpass query returned no named supported objects.")
    return snapshot


def atomic_write(path: Path, snapshot: OSMPlacesSnapshot) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary_name = stream.name
            stream.write(snapshot.model_dump_json(indent=2) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
        temporary_name = None
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import named museums, parks, and restaurants from OpenStreetMap."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--region",
        choices=tuple(PROVIDER_KEYS),
        action="append",
        help="Import one region; repeat to select both. Default imports both regions.",
    )
    args = parser.parse_args()
    selected_regions = [
        region_id for region_id in PROVIDER_KEYS
        if not args.region or region_id in args.region
    ]
    region_payloads = {}
    for index, region_id in enumerate(selected_regions):
        if index:
            time.sleep(1.1)
        region = PROVIDER_KEYS[region_id]
        print(f"Downloading {region['name']} from OpenStreetMap Overpass…", flush=True)
        region_payloads[region_id] = fetch_overpass(build_query(region["area_id"]))

    snapshot = build_snapshot(region_payloads, args.output, datetime.now(timezone.utc))
    atomic_write(args.output, snapshot)
    print(
        f"Saved {len(snapshot.candidates)} named places to {args.output}; "
        f"snapshot={snapshot.snapshot_id}"
    )
    for region in snapshot.regions:
        count = sum(candidate.region_id == region.region_id for candidate in snapshot.candidates)
        print(f"{region.name}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
