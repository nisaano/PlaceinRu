import json
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from app.catalog import RegionCatalog
from app.providers import LocalCandidateProvider
from mrt_ai.contracts.catalog import CandidateQuery, WikidataPlacesSnapshot
from scripts.import_wikidata_places import ROOT, build_snapshot


NOW = datetime.fromisoformat("2026-10-06T18:00:00+00:00")
QUERY_HASH = "a" * 64


def raw_payload():
    rows = [
        ("Q111", "Музей пример", "Q33506", "Q1697", "POINT(38.4000 55.8000)"),
        ("Q222", "Городской парк", "Q22698", "Q649", "POINT(37.6000 55.7500)"),
        ("Q333", "Место за пределами охвата", "Q33506", "Q1697", "POINT(30.0000 58.0000)"),
    ]
    return json.dumps({"results": {"bindings": [
        {
            "item": {"type": "uri", "value": f"http://www.wikidata.org/entity/{qid}"},
            "label": {"type": "literal", "xml:lang": "ru", "value": name},
            "class": {"type": "uri", "value": f"http://www.wikidata.org/entity/{class_id}"},
            "root": {"type": "uri", "value": f"http://www.wikidata.org/entity/{admin_id}"},
            "coord": {"type": "literal", "value": coordinate},
        }
        for qid, name, class_id, admin_id, coordinate in rows
    ]}}).encode("utf-8")


class WikidataImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT / ".test-tmp").mkdir(exist_ok=True)

    def test_committed_snapshot_has_real_provenanced_places_in_both_regions(self):
        snapshot = WikidataPlacesSnapshot.model_validate_json(
            (ROOT / "data/normalized/wikidata-places.json").read_text(encoding="utf-8")
        )
        self.assertGreaterEqual(len(snapshot.candidates), 400)
        self.assertEqual(
            {candidate.region_id for candidate in snapshot.candidates},
            {"ru:region:77", "ru:region:50"},
        )
        self.assertTrue(all(candidate.coordinates is not None for candidate in snapshot.candidates))
        self.assertTrue(all(candidate.source.source_url for candidate in snapshot.candidates))

    def test_snapshot_filters_bounds_and_keeps_provider_provenance(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".test-tmp") as directory:
            output = Path(directory) / "places.json"
            snapshot = build_snapshot(raw_payload(), output, NOW, QUERY_HASH)

        self.assertIsInstance(snapshot, WikidataPlacesSnapshot)
        self.assertEqual(len(snapshot.candidates), 2)
        by_region = {candidate.region_id: candidate for candidate in snapshot.candidates}
        self.assertEqual(set(by_region), {"ru:region:77", "ru:region:50"})
        self.assertEqual(by_region["ru:region:77"].kind, "ACTIVITY")
        self.assertEqual(by_region["ru:region:50"].kind, "ATTRACTION")
        self.assertEqual(by_region["ru:region:50"].source_tags["wikidata_id"], "Q111")
        self.assertEqual(by_region["ru:region:50"].source.source_sha256, snapshot.candidates[0].source.source_sha256)
        self.assertIn("cc0", by_region["ru:region:50"].source.license_reference.lower())

    def test_cached_provider_serves_wikidata_records_without_a_live_api_call(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".test-tmp") as directory:
            path = Path(directory) / "wikidata-places.json"
            snapshot = build_snapshot(raw_payload(), path, NOW, QUERY_HASH)
            path.write_text(snapshot.model_dump_json(), encoding="utf-8")
            provider = LocalCandidateProvider(
                RegionCatalog(ROOT / "data/normalized/catalog.json"),
                ROOT / "data/fixtures/places.json",
                wikidata_places=path,
            )

            result = provider.query(CandidateQuery(
                region_id="ru:region:50",
                data_mode="cached",
                kinds=["ATTRACTION", "ACTIVITY"],
            ))

        self.assertEqual(result.provider, "Wikidata")
        self.assertEqual([candidate.object_id for candidate in result.candidates], ["wikidata:Q111"])
        self.assertTrue(all(offer.availability == "unknown" for offer in result.offers))
        self.assertTrue(any("not verified" in warning for warning in result.warnings))


if __name__ == "__main__":
    unittest.main()
