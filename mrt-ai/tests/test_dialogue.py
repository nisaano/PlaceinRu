import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

from app.contracts import TripRequest
from app.dialogue import parse, reduce_trip
from app.main import ROOT, create_app

REFERENCE = datetime.fromisoformat("2026-10-03T22:00:00+03:00")


class ParserTests(unittest.TestCase):
    def parsed(self, message, trip=None, pending=None):
        return parse(message, trip or TripRequest(), pending, REFERENCE, "Europe/Moscow")

    def test_money_units(self):
        for text, expected in [("500 рублей", 50000), ("60 тысяч", 6000000), ("60к", 6000000), ("60 000 рублей", 6000000), ("1,5 тыс", 150000)]:
            with self.subTest(text=text):
                self.assertEqual(self.parsed(text)["updates"]["budget.amount_minor"], expected)

    def test_currency_not_assumed(self):
        result = self.parsed("500 евро")
        self.assertNotIn("budget.amount_minor", result["updates"])
        self.assertTrue(result["notices"])

    def test_negative_budget(self):
        result = self.parsed("бюджет -500 рублей")
        self.assertNotIn("budget.amount_minor", result["updates"])
        self.assertTrue(result["notices"])

    def test_short_budget_answer(self):
        self.assertEqual(self.parsed("60 000", pending="budget.amount_minor")["updates"]["budget.amount_minor"], 6000000)

    def test_budget_scope(self):
        u = self.parsed("80 тысяч на всех на всю поездку")["updates"]
        self.assertEqual(u["budget.basis"], "group")
        self.assertEqual(u["budget.period"], "trip")

    def test_duration_and_dates(self):
        result = self.parsed("Из Москвы в Сочи с 10.07.2027 на пять дней")
        trip = reduce_trip(TripRequest(), result["updates"], REFERENCE.date())
        self.assertEqual(trip.origin, "Москва")
        self.assertEqual(trip.destination, "Сочи")
        self.assertEqual(str(trip.dates.end_date), "2027-07-14")
        trip = reduce_trip(trip, self.parsed("давай лучше на неделю", trip)["updates"], REFERENCE.date())
        self.assertEqual(str(trip.dates.end_date), "2027-07-16")

    def test_date_range_uses_inclusive_days(self):
        u = self.parsed("25.07.2027 — 01.08.2027")["updates"]
        self.assertEqual(reduce_trip(TripRequest(), u, REFERENCE.date()).dates.duration_days, 8)

    def test_written_russian_date_range(self):
        updates = self.parsed("На выходные с 1 и 2 июля 2028 года")["updates"]
        trip = reduce_trip(TripRequest(), updates, REFERENCE.date())
        self.assertEqual(str(trip.dates.start_date), "2028-07-01")
        self.assertEqual(str(trip.dates.end_date), "2028-07-02")
        self.assertEqual(trip.dates.duration_days, 2)

    def test_invalid_written_russian_date_is_not_accepted(self):
        result = self.parsed("Поездка с 31 февраля 2028 года")
        self.assertNotIn("dates.start_date", result["updates"])
        self.assertTrue(result["notices"])

    def test_destination_before_origin_and_destination_without_preposition(self):
        first = self.parsed("Карелия из Санкт-Петербурга")["updates"]
        self.assertEqual(first["destination"], "Карелия")
        self.assertEqual(first["origin"], "Санкт-Петербург")
        second = self.parsed("Планирую Москву из Казани")["updates"]
        self.assertEqual(second["destination"], "Москва")
        self.assertEqual(second["origin"], "Казань")

    def test_party_size_colloquialisms_and_adult_count(self):
        for phrase, expected in [
            ("Едем вчетвером", 4),
            ("Едем парой", 2),
            ("нас двое взрослых", 2),
            ("четыре взрослых путешественника", 4),
            ("два путешественника", 2),
        ]:
            with self.subTest(phrase=phrase):
                self.assertEqual(self.parsed(phrase)["updates"]["party.total_count"], expected)

    def test_relative_date(self):
        self.assertEqual(self.parsed("послезавтра")["updates"]["dates.start_date"], "2026-10-05")

    def test_invalid_calendar_date(self):
        result = self.parsed("31.02.2027")
        self.assertNotIn("dates.start_date", result["updates"])
        self.assertTrue(result["notices"])

    def test_children_unknown(self):
        trip = reduce_trip(TripRequest(), self.parsed("нас двое")["updates"], REFERENCE.date())
        self.assertEqual(trip.party.adults, 2)
        self.assertIsNone(trip.party.children_count)
        self.assertEqual(trip.party.total_count, 2)

    def test_negations(self):
        u = self.parsed("Любим природу, не хочу музеи, без самолётов и без гида")["updates"]
        self.assertIn("природа", u["interests"])
        self.assertIn("музеи", u["excluded_interests"])
        self.assertNotIn("FLIGHT", u["transport.allowed_modes"])
        self.assertIs(u["guide.required"], False)

    def test_party_count_and_children_presence(self):
        updates = self.parsed("Нас четверо, будут дети")["updates"]
        trip = reduce_trip(TripRequest(), updates, REFERENCE.date())
        self.assertEqual(trip.party.total_count, 4)
        self.assertIs(trip.party.has_children, True)
        self.assertIsNone(trip.party.children_count)

        updates = self.parsed("нет", pending="party.has_children")["updates"]
        trip = reduce_trip(trip, updates, REFERENCE.date())
        self.assertIs(trip.party.has_children, False)
        self.assertEqual(trip.party.children_count, 0)

    def test_numeric_party_answer(self):
        self.assertEqual(self.parsed("3", pending="party.total_count")["updates"]["party.total_count"], 3)

    def test_trip_word_not_train(self):
        self.assertNotIn("transport.allowed_modes", self.parsed("бюджет на всю поездку")["updates"])

    def test_invalid_dates_atomic(self):
        with self.assertRaises(ValueError):
            reduce_trip(TripRequest(), {"dates.start_date": "2027-07-20", "dates.end_date": "2027-07-10"}, REFERENCE.date())

    def test_past_date(self):
        with self.assertRaises(ValueError):
            reduce_trip(TripRequest(), {"dates.start_date": "2020-01-01"}, REFERENCE.date())


class ApiTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / ".test-tmp"
        scratch.mkdir(exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(dir=scratch)
        self.database = Path(self.directory.name) / "sessions.sqlite3"
        self.client = TestClient(create_app(self.database, clock=lambda: REFERENCE))
        self.state = self.client.post("/v1/sessions", json={}).json()
        self.counter = 0

    def tearDown(self):
        self.client.close()
        self.directory.cleanup()

    def turn(self, message):
        self.counter += 1
        response = self.client.post(f'/v1/sessions/{self.state["session_id"]}/turns', json={"request_id": f"request-{self.counter}", "expected_state_version": self.state["state_version"], "message": message})
        self.assertEqual(response.status_code, 200, response.text)
        self.state = response.json()["state"]
        return response.json()

    def edit(self, updates):
        self.counter += 1
        return self.client.patch(f'/v1/sessions/{self.state["session_id"]}/trip', json={"request_id": f"request-{self.counter}", "expected_state_version": self.state["state_version"], "updates": updates})

    def test_complete_conversation(self):
        self.turn("Хотим вдвоём на пять дней, бюджет 80 тысяч на всех на всю поездку. Любим природу и музеи. Без детей. Темп спокойный, любой транспорт.")
        self.assertEqual(self.state["pending_question"], "origin")
        self.turn("Москва")
        self.assertEqual(self.state["pending_question"], "dates.start_date")
        self.turn("10.07.2027")
        self.assertEqual(self.state["status"], "ready_for_search")
        self.assertEqual(self.state["trip"]["mode"], "DISCOVER")
        self.turn("давай лучше на неделю")
        self.assertEqual(self.state["trip"]["dates"]["duration_days"], 7)
        self.assertEqual(self.state["trip"]["budget"]["amount_minor"], 8000000)
        self.assertEqual(self.state["trip"]["origin"], "Москва")

    def test_core_request_needs_no_budget_or_optional_preferences(self):
        self.turn("Из Москвы в Московскую область, с 10.07.2027 по 12.07.2027, нас трое, есть дети. Любим природу.")
        self.assertEqual(self.state["status"], "ready_for_search")
        self.assertEqual(self.state["trip"]["party"]["total_count"], 3)
        self.assertTrue(self.state["trip"]["party"]["has_children"])
        self.assertIsNone(self.state["trip"]["party"]["children_count"])
        self.assertEqual(self.state["trip"]["dates"]["duration_days"], 3)
        self.assertEqual(self.state["trip"]["destination"], "Московская область")
        self.assertIsNone(self.state["trip"]["budget"]["amount_minor"])
        self.assertEqual([option["region_id"] for option in self.state["recommendations"]["options"]], ["ru:region:50"])

    def test_calendar_iso_dates_update_trip(self):
        response = self.edit({
            "origin": "Москва",
            "destination": "Московская область",
            "dates.start_date": "2027-07-10",
            "dates.end_date": "2027-07-12",
            "party.total_count": 2,
            "party.has_children": False,
            "interests": ["природа"],
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.state = response.json()["state"]
        self.assertEqual(self.state["trip"]["dates"]["duration_days"], 3)
        self.assertEqual(self.state["trip"]["dates"]["start_date"], "2027-07-10")
        self.assertEqual(self.state["trip"]["dates"]["end_date"], "2027-07-12")
        self.assertEqual(self.state["status"], "ready_for_search")

    def test_structured_form_update_preserves_user_facing_summary(self):
        request = {
            "request_id": "form-request-001",
            "expected_state_version": self.state["state_version"],
            "updates": {
                "origin": "Москва",
                "destination": "Московская область",
                "dates.start_date": "2027-07-10",
                "dates.duration_days": 3,
                "party.total_count": 2,
                "party.has_children": False,
                "interests": ["природа", "гастрономия"],
                "guide.required": True,
                "budget.amount_minor": 1_000_000,
                "budget.basis": "group",
                "budget.period": "trip",
            },
            "message": "Запрос из формы: Москва → Московская область, 10.07.2027, двое, природа и гастрономия, с гидом.",
        }
        response = self.client.patch(
            f'/v1/sessions/{self.state["session_id"]}/trip',
            json=request,
        )
        self.assertEqual(response.status_code, 200, response.text)
        state = response.json()["state"]
        self.assertEqual(state["messages"][-2]["role"], "user")
        self.assertEqual(state["messages"][-2]["text"], request["message"])
        self.assertEqual(state["trip"]["dates"]["end_date"], "2027-07-12")
        self.assertEqual(state["trip"]["guide"]["required"], True)
        self.assertEqual(state["trip"]["budget"]["amount_minor"], 1_000_000)
        self.assertEqual(state["trip"]["budget"]["basis"], "group")
        self.assertEqual(state["trip"]["budget"]["period"], "trip")

    def test_initial_question(self):
        self.assertEqual(self.state["pending_question"], "origin")
        self.assertNotIn("destination", self.state["missing_parameters"])

    def test_parser_api_reference_timezone(self):
        response = self.client.post('/v1/parse', json={"message": "завтра", "reference_datetime": "2026-10-03T23:30:00+00:00", "timezone": "Europe/Moscow"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["trip"]["dates"]["start_date"], "2026-10-05")

    def test_manual_then_chat(self):
        result = self.edit({"origin": "Псков", "budget.amount_minor": 50000})
        self.assertEqual(result.status_code, 200, result.text)
        self.state = result.json()["state"]
        self.turn("на неделю")
        self.assertEqual(self.state["trip"]["origin"], "Псков")
        self.assertEqual(self.state["trip"]["budget"]["amount_minor"], 50000)

    def test_conflict_and_idempotency(self):
        url = f'/v1/sessions/{self.state["session_id"]}/turns'
        body = {"request_id": "idempotent-001", "expected_state_version": 0, "message": "на неделю"}
        first = self.client.post(url, json=body)
        self.assertEqual(first.json(), self.client.post(url, json=body).json())
        self.assertEqual(self.client.post(url, json={**body, "message": "на пять дней"}).status_code, 409)
        self.assertEqual(self.client.post(url, json={**body, "request_id": "another-001"}).status_code, 409)

    def test_invalid_edit_does_not_mutate(self):
        self.assertEqual(self.edit({"origin": "Казань", "party.adults": -1}).status_code, 422)
        saved = self.client.get(f'/v1/sessions/{self.state["session_id"]}').json()
        self.assertEqual(saved["state_version"], 0)
        self.assertIsNone(saved["trip"]["origin"])

    def test_unknown_path(self):
        self.assertEqual(self.edit({"__dict__": "bad"}).status_code, 422)

    def test_explicit_clear(self):
        self.turn("Из Москвы на неделю")
        self.state = self.edit({"origin": None}).json()["state"]
        self.assertIsNone(self.state["trip"]["origin"])
        self.assertEqual(self.state["trip"]["dates"]["duration_days"], 7)

    def test_restart_persistence(self):
        self.turn("Из Москвы")
        with TestClient(create_app(self.database)) as other:
            saved = other.get(f'/v1/sessions/{self.state["session_id"]}').json()
        self.assertEqual(saved, self.state)

    def test_sessions_isolated(self):
        self.turn("Из Москвы")
        another = self.client.post("/v1/sessions", json={}).json()
        self.assertNotEqual(another["session_id"], self.state["session_id"])
        self.assertIsNone(another["trip"]["origin"])

    def test_no_fake_offers(self):
        result = self.turn("Забронируй отель")
        self.assertEqual(result["options"], [])
        self.assertTrue(result["notices"])

    def test_api_has_no_frontend(self):
        self.assertEqual(self.client.get("/").status_code, 404)
        self.assertEqual(self.client.get("/static/app.js").status_code, 404)
        self.assertFalse(self.client.get("/health").json()["providers_connected"])
        self.assertIn("/v1/parse", self.client.get("/openapi.json").json()["paths"])

    def test_empty_and_invalid_timezone(self):
        self.assertEqual(self.client.post("/v1/sessions", json={"timezone": "invalid"}).status_code, 422)
        url = f'/v1/sessions/{self.state["session_id"]}/turns'
        self.assertEqual(self.client.post(url, json={"request_id": "empty-001", "expected_state_version": 0, "message": "   "}).status_code, 422)


if __name__ == "__main__":
    unittest.main()
