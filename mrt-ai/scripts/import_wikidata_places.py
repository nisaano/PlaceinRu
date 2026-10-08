"""Build a Moscow / Moscow Oblast place snapshot from Wikidata via QLever."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from mrt_ai.contracts.catalog import Candidate, Coordinates, Source, WikidataPlacesSnapshot

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / "data" / "normalized" / "wikidata-places.json"
RAW_DIR = ROOT / "data" / "raw" / "open-data" / "wikidata"
ENDPOINT = "https://qlever.dev/api/wikidata"
WIKIDATA_ENTITY = "https://www.wikidata.org/entity/"
LICENSE = "CC0 1.0: https://creativecommons.org/publicdomain/zero/1.0/"
ATTRIBUTION = (
    "Wikidata contributors; data is dedicated to the public domain under CC0 1.0. "
    "Retrieved through the QLever Wikidata SPARQL endpoint."
)

PREFIXES = """PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>"""
REGIONS = {
    "Q649": "ru:region:77",  # Moscow
    "Q1697": "ru:region:50",  # Moscow Oblast
}
# Wikidata classes selected for museums, landmarks, culture, architecture and nature.
CLASS_TAGS = {
    "Q33506": ("музей", "культура", "история"),
    "Q570116": ("достопримечательность", "культура", "история"),
    "Q22698": ("парк", "природа", "прогулка"),
    "Q46169": ("национальный парк", "природа", "активный отдых"),
    "Q43501": ("зоопарк", "животные", "семейный отдых"),
    "Q194195": ("парк аттракционов", "активный отдых", "семейный отдых"),
    "Q207694": ("художественный музей", "искусство", "культура"),
    "Q839954": ("археология", "история", "культура"),
    "Q16970": ("церковь", "архитектура", "история"),
    "Q44613": ("монастырь", "архитектура", "история"),
    "Q23413": ("замок", "архитектура", "история"),
    "Q16560": ("дворец", "архитектура", "история"),
    "Q4989906": ("памятник", "история", "культура"),
    "Q860861": ("скульптура", "искусство", "культура"),
    "Q24354": ("театр", "искусство", "культура"),
    "Q153562": ("оперный театр", "искусство", "культура"),
    "Q12280": ("мост", "архитектура", "городская прогулка"),
    "Q167346": ("ботанический сад", "природа", "прогулка"),
    "Q179049": ("природный заповедник", "природа", "активный отдых"),
    "Q173387": ("научный музей", "наука", "культура"),
    "Q15243209": ("объект наследия", "история", "архитектура"),
}
MOSCOW_BOUNDS = (36.60, 37.99, 55.05, 56.05)  # lon min/max, lat min/max
OBLAST_BOUNDS = (35.00, 40.60, 54.15, 56.95)
POINT_RE = re.compile(r"^POINT\((-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?)\)$")


def build_place_query() -> str:
    roots = " ".join(f"wd:{qid}" for qid in REGIONS)
    classes = " ".join(f"wd:{qid}" for qid in CLASS_TAGS)
    return PREFIXES + f""" SELECT DISTINCT ?item ?label ?coord ?class ?root WHERE {{
  VALUES ?root {{ {roots} }}
  VALUES ?class {{ {classes} }}
  ?item wdt:P131+ ?root; wdt:P31 ?class; wdt:P625 ?coord; rdfs:label ?label.
  FILTER(LANG(?label)="ru")
}} LIMIT 10000"""


def fetch_query(query: str) -> dict:
    request = Request(
        ENDPOINT + "?" + urlencode({"query": query}),
        headers={
            "Accept": "application/sparql-results+json",
            "User-Agent": "mrt-ai/1.0 (PlaceinRu open place snapshot importer)",
        },
    )
    try:
        with urlopen(request, timeout=120) as response:
            payload = json.loads(response.read())
    except HTTPError as error:
        raise RuntimeError(f"QLever returned HTTP {error.code}") from error
    except (TimeoutError, URLError, json.JSONDecodeError) as error:
        raise RuntimeError(f"QLever Wikidata endpoint is unavailable: {error}") from error
    if payload.get("status") == "ERROR" or not isinstance(payload.get("results", {}).get("bindings"), list):
        raise RuntimeError(f"QLever returned an invalid SPARQL result: {payload.get('exception', 'no bindings')}")
    return payload


def build_live_payload() -> tuple[bytes, str]:
    place_query = build_place_query()
    payload = fetch_query(place_query)
    query_digest = hashlib.sha256(place_query.encode("utf-8")).hexdigest()
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), query_digest


def coordinates_for(row: dict) -> tuple[float, float] | None:
    match = POINT_RE.fullmatch(row["coord"]["value"])
    if not match:
        return None
    longitude, latitude = map(float, match.groups())
    return latitude, longitude


def resolve_region(root_id: str, coordinates: tuple[float, float]) -> str | None:
    latitude, longitude = coordinates
    region_id = REGIONS.get(root_id)
    if region_id is None:
        return None
    if root_id == "Q649":
        bounds = MOSCOW_BOUNDS
    else:
        bounds = OBLAST_BOUNDS
    lon_min, lon_max, lat_min, lat_max = bounds
    if not (lon_min <= longitude <= lon_max and lat_min <= latitude <= lat_max):
        return None
    return region_id


def candidate_tags(class_ids: set[str]) -> list[str]:
    tags = []
    for class_id in sorted(class_ids):
        tags.extend(CLASS_TAGS.get(class_id, ()))
    return list(dict.fromkeys(tags))


def canonical_hash(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_snapshot(raw_payload: bytes, output: Path, retrieved_at: datetime, query_sha256: str) -> WikidataPlacesSnapshot:
    parsed = json.loads(raw_payload)
    rows = parsed.get("results", {}).get("bindings")
    if not isinstance(rows, list):
        raise ValueError("Wikidata snapshot has no SPARQL bindings")
    payload_sha256 = hashlib.sha256(raw_payload).hexdigest()
    source_file = output.resolve().relative_to(ROOT).as_posix()
    grouped: dict[str, dict] = {}
    rejected_coordinates = 0
    for row in rows:
        item_url = row.get("item", {}).get("value", "")
        item_id = item_url.rsplit("/", 1)[-1]
        if not re.fullmatch(r"Q\d+", item_id):
            continue
        name = row.get("label", {}).get("value", "").strip()
        class_id = row.get("class", {}).get("value", "").rsplit("/", 1)[-1]
        root_id = row.get("root", {}).get("value", "").rsplit("/", 1)[-1]
        coordinates = coordinates_for(row)
        if not name or class_id not in CLASS_TAGS or coordinates is None:
            rejected_coordinates += 1
            continue
        region_id = resolve_region(root_id, coordinates)
        if region_id is None:
            rejected_coordinates += 1
            continue
        record = grouped.setdefault(item_id, {
            "name": name,
            "region_id": region_id,
            "coordinates": coordinates,
            "classes": set(),
        })
        if record["region_id"] != region_id:
            rejected_coordinates += 1
            continue
        record["classes"].add(class_id)

    candidates = []
    for item_id, record in sorted(grouped.items()):
        classes = record["classes"]
        labels = [CLASS_TAGS[class_id][0] for class_id in sorted(classes)]
        tags = candidate_tags(classes)
        natural = bool(set(tags).intersection({"природа", "активный отдых", "семейный отдых"}))
        candidates.append(Candidate(
            object_id=f"wikidata:{item_id}",
            kind="ACTIVITY" if natural else "ATTRACTION",
            region_id=record["region_id"],
            name=record["name"],
            description=(
                f"Тип: {', '.join(labels)}. Категория и координаты взяты из Wikidata; "
                "режим работы, стоимость и доступность не проверялись."
            ),
            tags=tags,
            coordinates=Coordinates(latitude=record["coordinates"][0], longitude=record["coordinates"][1]),
            source_tags={"wikidata_id": item_id, "wikidata_classes": ";".join(sorted(classes))},
            source=Source(
                provider="Wikidata",
                source_file=source_file,
                source_url=f"{WIKIDATA_ENTITY}{item_id}",
                source_sha256=payload_sha256,
                data_mode="cached",
                verification="provider_reported",
                license_reference=LICENSE,
                attribution=ATTRIBUTION,
                checked_at=retrieved_at,
            ),
        ))

    payload = {
        "schema_version": "1.0",
        "data_mode": "cached",
        "provider": "Wikidata",
        "endpoint": ENDPOINT,
        "license_reference": LICENSE,
        "attribution": ATTRIBUTION,
        "retrieved_at": retrieved_at,
        "query_sha256": query_sha256,
        "candidates": candidates,
    }
    payload["snapshot_id"] = canonical_hash({
        "schema_version": payload["schema_version"],
        "data_mode": payload["data_mode"],
        "provider": payload["provider"],
        "endpoint": payload["endpoint"],
        "license_reference": payload["license_reference"],
        "attribution": payload["attribution"],
        "retrieved_at": retrieved_at.isoformat(),
        "query_sha256": query_sha256,
        "candidates": [candidate.model_dump(mode="json") for candidate in candidates],
    })
    snapshot = WikidataPlacesSnapshot.model_validate(payload)
    if not snapshot.candidates:
        raise ValueError("No supported named Wikidata places fell within the two regional bounds")
    print(f"Skipped {rejected_coordinates} unnamed, unsupported, or out-of-bounds rows")
    return snapshot


def atomic_write(path: Path, snapshot: WikidataPlacesSnapshot) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=f".{path.name}.", suffix=".tmp", delete=False) as stream:
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
    parser = argparse.ArgumentParser(description="Import Wikidata places for Moscow and Moscow Oblast.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--input", type=Path, help="Use a saved SPARQL JSON response instead of making a network request.")
    args = parser.parse_args()
    if args.input:
        raw_payload = args.input.read_bytes()
        query_sha256 = hashlib.sha256(build_place_query().encode("utf-8")).hexdigest()
    else:
        raw_payload, query_sha256 = build_live_payload()
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        (RAW_DIR / "admin-pois.json").write_bytes(raw_payload)
    snapshot = build_snapshot(raw_payload, args.output, datetime.now(timezone.utc), query_sha256)
    atomic_write(args.output, snapshot)
    counts = {}
    for candidate in snapshot.candidates:
        counts[candidate.region_id] = counts.get(candidate.region_id, 0) + 1
    print(f"Saved {len(snapshot.candidates)} places; snapshot={snapshot.snapshot_id}")
    for region_id in ("ru:region:77", "ru:region:50"):
        print(f"{region_id}: {counts.get(region_id, 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
