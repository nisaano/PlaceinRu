import json
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.catalog import CatalogUnavailable, RegionCatalog
from app.catalog_import import ROOT, build_catalog, file_hash, parse_card
from app.contracts import TripRequest
from mrt_ai.retrieval.encoders.sbert import LocalSbertPlaceSearch
from mrt_ai.contracts.catalog import CandidateBatch, CandidateQuery, FixturePlaceCatalog, Offer, Price
from app.main import create_app
from app.providers import LocalCandidateProvider

NOW = datetime.fromisoformat("2026-10-04T12:00:00+03:00")
CATALOG_PATH = ROOT / "data/normalized/catalog.json"


def trip(interests=None, **overrides):
    data = {"origin": "Казань", "dates": {"start_date": "2027-07-10", "duration_days": 3},
            "budget": {"amount_minor": 5000000, "basis": "group", "period": "trip"},
            "party": {"adults": 2, "children_count": 0}, "interests": interests or ["природа"],
            "format": {"pace": "balanced"}, "transport": {"allowed_modes": ["TRAIN"]}}
    data.update(overrides)
    return TripRequest.model_validate(data)


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.catalog = RegionCatalog(CATALOG_PATH)
        self.cards = sorted((ROOT / "data").glob("карточка*.csv"))
        (ROOT / ".test-tmp").mkdir(exist_ok=True)

    def test_import_reproducible_and_non_destructive(self):
        before = [file_hash(p) for p in self.cards]
        catalog, report = build_catalog(self.cards)
        repeat, _ = build_catalog(reversed(self.cards))
        self.assertEqual(catalog, repeat)
        self.assertEqual(catalog, self.catalog.load())
        self.assertEqual(before, [file_hash(p) for p in self.cards])
        self.assertEqual(sum(r["row_count"] for r in report["sources"]), 226)
        self.assertTrue(all(r["row_count"] == len(r["records"]) for r in report["sources"]))

    def test_region_values_and_source(self):
        regions = {r.code: r for r in self.catalog.load().regions}
        self.assertEqual(regions["77"].scores["tourism_score_culture"], 5)
        self.assertEqual(regions["50"].car_required, "preferred")
        self.assertEqual(regions["50"].month_scores["3"], 2)
        self.assertFalse(regions["50"].has_sea)
        self.assertEqual(regions["77"].source.data_mode, "manual")
        self.assertEqual(regions["77"].source.source_lines["technical.region_id"], [88])

    def test_duplicates_rejected(self):
        with self.assertRaises(ValidationError):
            build_catalog([self.cards[0], self.cards[0]])

    def test_duplicate_source_field_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".test-tmp") as directory:
            path = Path(directory) / "card.csv"
            path.write_bytes(self.cards[0].read_bytes() + '\n10.,Технические,признаки,backend,/,ML,region_id,77\n'.encode())
            with self.assertRaises(ValueError):
                parse_card(path)

    def test_changed_source_invalidates_snapshot(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".test-tmp") as directory:
            data = Path(directory)
            (data / "normalized").mkdir()
            shutil.copy2(CATALOG_PATH, data / "normalized/catalog.json")
            for card in self.cards:
                shutil.copy2(card, data / card.name)
            reader = RegionCatalog(data / "normalized/catalog.json")
            self.assertEqual(len(reader.load().regions), 2)
            with (data / self.cards[0].name).open("ab") as stream:
                stream.write(b"\n")
            with self.assertRaises(CatalogUnavailable):
                reader.load()

    def test_tampered_snapshot_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".test-tmp") as directory:
            path = Path(directory) / "catalog.json"
            payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
            payload["regions"][0]["budget_level"] = 1
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(CatalogUnavailable):
                RegionCatalog(path).load()

    def test_nature_and_culture_change_order(self):
        self.assertEqual(self.catalog.recommend(trip(["природа"])).options[0].region_id, "ru:region:50")
        self.assertEqual(self.catalog.recommend(trip(["музеи"])).options[0].region_id, "ru:region:77")

    def test_no_alpine_or_sea_claims(self):
        for interests in (["море"], ["горы"], ["неизвестный интерес"]):
            result = self.catalog.recommend(trip(interests))
            self.assertEqual(result.status, "no_matches")
            self.assertEqual(result.options, [])

    def test_budget_unknown_even_when_zero(self):
        result = self.catalog.recommend(trip(budget={"amount_minor": 0, "basis": "group", "period": "trip"}))
        self.assertEqual(result.status, "partial")
        self.assertTrue(all(o.budget_status == "unknown" and o.total_price_minor is None for o in result.options))

    def test_no_automatic_destination_replacement(self):
        result = self.catalog.recommend(trip(mode="PLAN", destination="Сочи"))
        self.assertEqual(result.status, "outside_coverage")
        self.assertEqual(result.options, [])

    def test_aliases_and_missing(self):
        result = self.catalog.recommend(trip(mode="PLAN", destination="Подмосковье"))
        self.assertEqual([o.region_id for o in result.options], ["ru:region:50"])
        result = self.catalog.recommend(TripRequest())
        self.assertEqual(result.status, "needs_parameters")
        self.assertNotIn("destination", result.missing_parameters)

    def test_recommendation_for_past_dates_blocked(self):
        result = self.catalog.recommend(trip(), today=datetime(2028, 1, 1).date())
        self.assertEqual(result.status, "needs_parameters")
        self.assertEqual(result.options, [])


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.provider = LocalCandidateProvider(RegionCatalog(CATALOG_PATH), ROOT / "data/fixtures/places.json")

    def test_fixture_place_catalog_is_complete_and_explicitly_synthetic(self):
        path = ROOT / "data/fixtures/places.json"
        fixtures = FixturePlaceCatalog.model_validate_json(path.read_text(encoding="utf-8"))
        self.assertEqual(len(fixtures.candidates), 17)
        self.assertEqual({candidate.region_id for candidate in fixtures.candidates}, {"ru:region:77", "ru:region:50"})
        self.assertEqual(
            {candidate.kind for candidate in fixtures.candidates},
            {"HOTEL", "TRANSPORT", "ATTRACTION", "RESTAURANT", "ACTIVITY", "GUIDE"},
        )
        self.assertTrue(all(candidate.coordinates for candidate in fixtures.candidates))
        self.assertTrue(all(candidate.visit_duration_minutes is None or candidate.visit_duration_minutes > 0 for candidate in fixtures.candidates))

    def test_fixture_catalog_rejects_unlabelled_or_real_mode_candidates(self):
        payload = json.loads((ROOT / "data/fixtures/places.json").read_text(encoding="utf-8"))
        payload["candidates"][0]["name"] = "Unnamed place"
        with self.assertRaises(ValidationError):
            FixturePlaceCatalog.model_validate(payload)
        payload = json.loads((ROOT / "data/fixtures/places.json").read_text(encoding="utf-8"))
        payload["candidates"][0]["source"]["data_mode"] = "live"
        with self.assertRaises(ValidationError):
            FixturePlaceCatalog.model_validate(payload)

    def test_default_mode_does_not_fall_back_to_fixtures(self):
        result = self.provider.query(CandidateQuery(region_id="ru:region:77"))
        self.assertEqual(result.status, "no_candidates")
        self.assertEqual(result.candidates, [])
        self.assertEqual(len(result.unavailable_kinds), 6)
        self.assertEqual(result.data_mode, "manual")

    def test_explicit_fixture_mode_all_categories(self):
        result = self.provider.query(CandidateQuery(region_id="ru:region:50", data_mode="fixture"))
        self.assertEqual(len(result.candidates), 9)
        self.assertEqual(len(result.offers), 9)
        self.assertTrue(all(c.name.startswith("ДЕМО · ") and c.coordinates is not None for c in result.candidates))
        self.assertTrue(all(c.opening_hours.startswith("ДЕМО:") for c in result.candidates))
        self.assertTrue(all(o.price is None and o.booking_url is None and o.availability == "unknown" for o in result.offers))

    def test_filters_and_query_fingerprint(self):
        query = CandidateQuery(region_id="ru:region:77", data_mode="fixture", excluded_tags=["музеи"], start_date="2027-07-10")
        result = self.provider.query(query)
        self.assertNotIn("ATTRACTION", [c.kind for c in result.candidates])
        later = self.provider.query(query.model_copy(update={"start_date": datetime(2027, 7, 11).date()}))
        self.assertNotEqual(result.query_fingerprint, later.query_fingerprint)

    def test_fixture_booking_links_rejected(self):
        with self.assertRaises(ValidationError):
            Offer(offer_id="o", object_id="c", query_fingerprint="q", data_mode="fixture", booking_url="https://example.com", booking_link_type="offer")

    def test_unknown_price_distinct_from_zero(self):
        price = Price(amount_minor=0, basis="group", quantity=1, status="quoted")
        self.assertEqual(price.amount_minor, 0)
        with self.assertRaises(ValidationError):
            Price(amount_minor=-1, basis="group", quantity=1, status="quoted")

    def test_mixed_sources_and_dangling_ids_rejected(self):
        result = self.provider.query(CandidateQuery(region_id="ru:region:77", data_mode="fixture")).model_dump()
        result["offers"][0]["object_id"] = "unknown-id"
        with self.assertRaises(ValidationError):
            CandidateBatch.model_validate(result)
        result["offers"] = []
        result["candidates"][0]["source"]["data_mode"] = "live"
        with self.assertRaises(ValidationError):
            CandidateBatch.model_validate(result)


class CatalogApiTests(unittest.TestCase):
    def setUp(self):
        (ROOT / ".test-tmp").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".test-tmp")
        self.client = TestClient(create_app(Path(self.temp.name) / "test.sqlite3", clock=lambda: NOW))
        self.state = self.client.post("/v1/sessions", json={}).json()
        response = self.client.post(f'/v1/sessions/{self.state["session_id"]}/turns', json={"request_id": "create-test", "expected_state_version": 0,
            "message": "Из Казани на пять дней с 10.07.2027. Бюджет 80 тысяч на всех на всю поездку. Едем вдвоём, без детей. Любим природу, темп спокойный, любой транспорт."})
        self.assertEqual(response.status_code, 200, response.text)
        self.state = response.json()["state"]

    def tearDown(self):
        self.client.close()
        self.temp.cleanup()

    def selection(self, **updates):
        body = {"request_id": "select-test", "expected_state_version": self.state["state_version"], "region_id": "ru:region:50",
                "catalog_snapshot_id": self.state["recommendations"]["catalog_snapshot_id"]}
        body.update(updates)
        return self.client.post(f'/v1/sessions/{self.state["session_id"]}/select-region', json=body)

    def test_selection_persists_and_changes_recompute(self):
        selected = self.selection()
        self.assertEqual(selected.status_code, 200, selected.text)
        self.state = selected.json()["state"]
        self.assertEqual(self.state["trip"]["destination_region_id"], "ru:region:50")
        saved = self.client.get(f'/v1/sessions/{self.state["session_id"]}').json()
        self.assertEqual(saved["trip"], self.state["trip"])
        changed = self.client.patch(f'/v1/sessions/{self.state["session_id"]}/trip', json={"request_id": "change-test", "expected_state_version": 2, "updates": {"destination": "Сочи"}}).json()["state"]
        self.assertIsNone(changed["trip"]["destination_region_id"])
        self.assertEqual(changed["recommendations"]["status"], "outside_coverage")
        self.assertEqual(changed["recommendations"]["based_on_state_version"], 3)

    def test_stale_selection_and_bad_ids(self):
        self.assertEqual(self.selection(expected_state_version=0).status_code, 409)
        self.assertEqual(self.selection(catalog_snapshot_id="0" * 64).status_code, 409)
        self.assertEqual(self.selection(region_id="ru:region:999").status_code, 422)

    def test_selection_idempotent(self):
        first = self.selection()
        self.assertEqual(first.json(), self.selection().json())

    def test_source_endpoint_and_candidate_modes(self):
        self.assertEqual(len(self.client.get("/v1/catalog/regions").json()["regions"]), 2)
        default = self.client.post("/v1/candidates/query", json={"region_id": "ru:region:77"}).json()
        self.assertEqual(default["candidates"], [])
        self.assertEqual(self.client.post("/v1/candidates/query", json={"region_id": "ru:region:77", "data_mode": "live"}).status_code, 422)

    def test_fixture_candidates_are_explicit_and_synthetic(self):
        response = self.client.post("/v1/candidates/query", json={"region_id": "ru:region:77", "data_mode": "fixture"})
        self.assertEqual(response.status_code, 200, response.text)
        batch = response.json()
        self.assertEqual(len(batch["candidates"]), 8)
        self.assertTrue(all(candidate["source"]["data_mode"] == "fixture" for candidate in batch["candidates"]))
        self.assertTrue(all(candidate["source"]["verification"] == "synthetic" for candidate in batch["candidates"]))
        self.assertTrue(batch["warnings"])

    def test_place_search_returns_ranked_fixture_matches_only(self):
        response = self.client.post("/v1/search/places", json={
            "region_id": "ru:region:50",
            "query": "спокойная прогулка по лесной тропе",
            "data_mode": "fixture",
            "top_k": 3,
        })
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["ranking_version"], "bm25-lexical-v1")
        self.assertEqual(payload["status"], "partial")
        self.assertEqual(payload["results"][0]["candidate"]["object_id"], "fixture:50:activity:forest-trail")
        self.assertTrue(payload["results"][0]["matched_terms"])
        self.assertTrue(all(hit["candidate"]["source"]["verification"] == "synthetic" for hit in payload["results"]))

    def test_place_search_requires_explicit_fixture_mode_and_filters(self):
        missing_mode = self.client.post("/v1/search/places", json={
            "region_id": "ru:region:77", "query": "история"
        })
        self.assertEqual(missing_mode.status_code, 422)
        filtered = self.client.post("/v1/search/places", json={
            "region_id": "ru:region:77",
            "query": "музей история",
            "data_mode": "fixture",
            "excluded_tags": ["музеи"],
        })
        self.assertEqual(filtered.status_code, 200)
        self.assertTrue(all(
            "музеи" not in candidate["tags"]
            for hit in filtered.json()["results"]
            for candidate in [hit["candidate"]]
        ))

    def test_place_search_has_no_match_for_unrelated_terms(self):
        response = self.client.post("/v1/search/places", json={
            "region_id": "ru:region:77",
            "query": "космический запуск ракеты",
            "data_mode": "fixture",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "no_candidates")
        self.assertEqual(response.json()["results"], [])

    def test_embedding_search_reports_unavailable_model_without_fallback(self):
        searcher = LocalSbertPlaceSearch(Path(self.temp.name) / "missing-model")
        with TestClient(create_app(
            Path(self.temp.name) / "embedding.sqlite3",
            clock=lambda: NOW,
            embedding_searcher=searcher,
        )) as client:
            response = client.post("/v1/search/places", json={
                "region_id": "ru:region:50",
                "query": "хочу спокойный отдых на природе",
                "data_mode": "fixture",
                "ranking_method": "embedding",
            })
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"]["code"], "EMBEDDING_MODEL_UNAVAILABLE")

    def test_embedding_search_api_reports_semantic_ranking_method(self):
        searcher = LocalSbertPlaceSearch(
            Path(self.temp.name) / "unused-model",
            encode_texts=lambda texts: [[1.0, 0.0] for _ in texts],
        )
        with TestClient(create_app(
            Path(self.temp.name) / "embedding-success.sqlite3",
            clock=lambda: NOW,
            embedding_searcher=searcher,
        )) as client:
            response = client.post("/v1/search/places", json={
                "region_id": "ru:region:50",
                "query": "отдых на природе",
                "data_mode": "fixture",
                "ranking_method": "embedding",
            })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["ranking_version"], "sbert-large-nlu-ru-mean-v1")
        self.assertEqual(response.json()["results"][0]["matched_terms"], [])

    def test_corrupt_catalog_does_not_break_chat(self):
        with TestClient(create_app(Path(self.temp.name) / "other.sqlite3", clock=lambda: NOW, catalog_path=Path(self.temp.name) / "missing.json")) as client:
            self.assertEqual(client.get("/v1/catalog/regions").status_code, 503)
            result = client.post("/v1/recommend", json={"trip": trip().model_dump(mode="json")})
            self.assertEqual(result.json()["status"], "unavailable")
            self.assertEqual(client.post("/v1/sessions", json={}).status_code, 201)


if __name__ == "__main__":
    unittest.main()
