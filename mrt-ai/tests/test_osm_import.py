import json
from datetime import datetime
from pathlib import Path
import tempfile
import unittest

from pydantic import ValidationError

from app.contracts import TripRequest
from app.catalog import RegionCatalog
from app.main import create_app
from app.providers import LocalCandidateProvider
from mrt_ai.contracts.catalog import CandidateQuery, OSMPlacesSnapshot
from scripts.import_osm_places import ROOT, build_snapshot, candidate_from_element
from fastapi.testclient import TestClient

NOW = datetime.fromisoformat("2026-10-06T12:00:00+03:00")
REGION_ID = "ru:region:50"
PAYLOAD = {
    "osm3s": {"timestamp_osm_base": "2026-10-06T09:00:00Z"},
    "elements": [
        {
            "type": "node",
            "id": 123456,
            "lat": 55.75,
            "lon": 37.61,
            "tags": {
                "name": "Ресторан Пример",
                "amenity": "restaurant",
                "cuisine": "russian;georgian",
                "phone": "+7 000 000-00-00",
            },
        },
        {
            "type": "way",
            "id": 654321,
            "center": {"lat": 55.8, "lon": 37.4},
            "tags": {"name": "Парк Пример", "leisure": "park"},
        },
        {
            "type": "relation",
            "id": 112233,
            "center": {"lat": 55.77, "lon": 37.55},
            "tags": {"name": "Музей Пример", "tourism": "museum"},
        },
    ],
}


def encoded_payload(elements=None):
    value = dict(PAYLOAD)
    value["elements"] = PAYLOAD["elements"] if elements is None else elements
    return json.dumps(value, ensure_ascii=False).encode("utf-8")


class OSMImportTests(unittest.TestCase):
    def setUp(self):
        (ROOT / ".test-tmp").mkdir(exist_ok=True)

    def test_element_conversion_preserves_osm_provenance_and_limits_tags(self):
        digest = "a" * 64
        candidate = candidate_from_element(
            PAYLOAD["elements"][0],
            REGION_ID,
            digest,
            "data/normalized/osm-places.json",
            NOW,
        )
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate.object_id, "osm:node:123456")
        self.assertEqual(candidate.kind, "RESTAURANT")
        self.assertEqual(candidate.tags[:3], ["ресторан", "еда", "гастрономия"])
        self.assertEqual(candidate.source_tags["cuisine"], "russian;georgian")
        self.assertNotIn("phone", candidate.source_tags)
        self.assertEqual(candidate.source.data_mode, "cached")
        self.assertEqual(candidate.source.verification, "provider_reported")
        self.assertEqual(candidate.source.source_sha256, digest)
        self.assertIn("odbl", candidate.source.license_reference.lower())

    def test_snapshot_maps_three_requested_categories_and_deduplicates_ids(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".test-tmp") as directory:
            output = Path(directory) / "osm-places.json"
            snapshot = build_snapshot(
                {
                    "ru:region:77": encoded_payload(),
                    "ru:region:50": encoded_payload(),
                },
                output,
                NOW,
            )
            self.assertIsInstance(snapshot, OSMPlacesSnapshot)
            self.assertEqual(len(snapshot.candidates), 3)
            self.assertEqual(
                {candidate.kind for candidate in snapshot.candidates},
                {"RESTAURANT", "ACTIVITY", "ATTRACTION"},
            )
            self.assertEqual(
                [region.element_count for region in snapshot.regions],
                [3, 0],
            )
            self.assertEqual(len({candidate.object_id for candidate in snapshot.candidates}), 3)
            self.assertEqual(snapshot.candidates[0].region_id, "ru:region:77")

    def test_snapshot_rejects_synthetic_or_non_osm_source(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".test-tmp") as directory:
            snapshot = build_snapshot(
                {"ru:region:50": encoded_payload()},
                Path(directory) / "osm-places.json",
                NOW,
            )
            payload = snapshot.model_dump(mode="json")
            payload["candidates"][0]["source"]["verification"] = "synthetic"
            with self.assertRaises(ValidationError):
                OSMPlacesSnapshot.model_validate(payload)

    def test_provider_uses_only_explicit_cached_snapshot(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".test-tmp") as directory:
            data_path = Path(directory) / "osm-places.json"
            snapshot = build_snapshot(
                {"ru:region:50": encoded_payload()},
                data_path,
                NOW,
            )
            data_path.write_text(snapshot.model_dump_json(), encoding="utf-8")
            provider = LocalCandidateProvider(
                RegionCatalog(ROOT / "data/normalized/catalog.json"),
                ROOT / "data/fixtures/places.json",
                data_path,
            )
            cached = provider.query(CandidateQuery(
                region_id=REGION_ID,
                data_mode="cached",
                kinds=["RESTAURANT", "ACTIVITY", "ATTRACTION"],
            ))
            self.assertEqual(cached.data_mode, "cached")
            self.assertEqual(len(cached.candidates), 3)
            self.assertTrue(all(item.object_id.startswith("osm:") for item in cached.candidates))
            self.assertTrue(all(offer.availability == "unknown" for offer in cached.offers))
            self.assertTrue(any("OpenStreetMap" in warning for warning in cached.warnings))

    def test_provider_does_not_fallback_when_real_snapshot_is_missing(self):
        provider = LocalCandidateProvider(
            RegionCatalog(ROOT / "data/normalized/catalog.json"),
            ROOT / "data/fixtures/places.json",
            ROOT / ".test-tmp" / "missing-osm-places.json",
        )
        with self.assertRaisesRegex(ValueError, "cached place snapshot"):
            provider.query(CandidateQuery(region_id=REGION_ID, data_mode="cached"))

    def test_api_ranks_and_builds_proposal_from_cached_osm_records(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".test-tmp") as directory:
            data_path = Path(directory) / "osm-places.json"
            snapshot = build_snapshot(
                {"ru:region:50": encoded_payload()},
                data_path,
                NOW,
            )
            data_path.write_text(snapshot.model_dump_json(), encoding="utf-8")
            with TestClient(create_app(
                Path(directory) / "sessions.sqlite3",
                osm_places_path=data_path,
                wikidata_places_path=Path(directory) / "missing-wikidata.json",
            )) as client:
                response = client.post("/v1/candidates/query", json={
                    "region_id": REGION_ID,
                    "data_mode": "cached",
                    "kinds": ["RESTAURANT", "ACTIVITY", "ATTRACTION"],
                })
                self.assertEqual(response.status_code, 200, response.text)
                batch = response.json()
                self.assertTrue(any("OpenStreetMap contributors" in warning for warning in batch["warnings"]))
                trip = TripRequest(
                    mode="PLAN",
                    destination="Московская область",
                    destination_region_id=REGION_ID,
                    dates={"start_date": "2026-10-10", "duration_days": 2},
                    interests=["гастрономия"],
                )
                ranked = client.post("/v1/rank", json={
                    "trip": trip.model_dump(mode="json"),
                    "candidates": batch,
                })
                self.assertEqual(ranked.status_code, 200, ranked.text)
                self.assertEqual(ranked.json()["results"][0]["candidate"]["object_id"], "osm:node:123456")
                proposal = client.post("/v1/route/proposal", json={
                    "trip": trip.model_dump(mode="json"),
                    "candidates": batch,
                })
                self.assertEqual(proposal.status_code, 200, proposal.text)
                self.assertEqual(proposal.json()["status"], "provisional")
                item = proposal.json()["days"][0]["items"][0]
                self.assertEqual(item["object_id"], "osm:node:123456")
                self.assertIsNone(item["start_at"])
                self.assertIsNone(item["visit_duration_minutes"])


if __name__ == "__main__":
    unittest.main()
