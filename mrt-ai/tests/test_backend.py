import json
import tempfile
import unittest
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from app.backend import BackendTripsClient
from app.main import ROOT, create_app


TRIP = json.loads((ROOT / "data" / "fixtures" / "backend-trips.json").read_text(encoding="utf-8"))["trips"][0]


class BackendApiTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / ".test-tmp"
        scratch.mkdir(exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(dir=scratch)
        self.requests = []
        self.backend_status = 200
        self.backend_payload = [TRIP]

        def handler(request):
            self.requests.append(request)
            if self.backend_status == 302:
                return httpx.Response(302, headers={"Location": "https://other.example/"})
            if self.backend_status >= 400:
                return httpx.Response(self.backend_status)
            return httpx.Response(self.backend_status, json=self.backend_payload)

        self.client = TestClient(create_app(
            Path(self.directory.name) / "sessions.sqlite3",
            backend_url="http://backend.test",
            backend_transport_factory=lambda: httpx.MockTransport(handler),
        ))

    def tearDown(self):
        self.client.close()
        self.directory.cleanup()

    def test_list_trips_forwards_user_token_and_maps_backend_response(self):
        response = self.client.get("/v1/backend/trips", headers={"Authorization": "Bearer user-jwt"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()[0]["destination"], "Москва")
        self.assertEqual(response.json()[0]["days"][0]["items"][0]["objectId"], "fixture:place-123")
        self.assertEqual(self.requests[0].url.path, "/api/v1/trips")
        self.assertEqual(self.requests[0].headers["Authorization"], "Bearer user-jwt")

    def test_get_trip_uses_fixed_backend_path(self):
        self.backend_payload = TRIP
        response = self.client.get("/v1/backend/trips/27", headers={"Authorization": "Bearer user-jwt"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["id"], 27)
        self.assertEqual(self.requests[0].url.path, "/api/v1/trips/27")

    def test_missing_or_invalid_user_token_is_rejected_before_backend_call(self):
        self.assertEqual(self.client.get("/v1/backend/trips").status_code, 401)
        self.assertEqual(self.client.get("/v1/backend/trips", headers={"Authorization": "Basic abc"}).status_code, 401)
        self.assertEqual(self.requests, [])

    def test_backend_errors_are_explicit_and_do_not_leak_token(self):
        for status, expected in [(401, 401), (403, 403), (404, 404), (429, 503), (500, 503), (302, 502)]:
            with self.subTest(status=status):
                self.backend_status = status
                response = self.client.get("/v1/backend/trips/27", headers={"Authorization": "Bearer secret-token"})
                self.assertEqual(response.status_code, expected)
                self.assertNotIn("secret-token", response.text)

    def test_invalid_backend_payload_returns_bad_gateway(self):
        self.backend_status = 200
        self.backend_payload = [{"title": "missing required id"}]
        response = self.client.get("/v1/backend/trips", headers={"Authorization": "Bearer user-jwt"})
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["detail"]["code"], "BACKEND_INVALID_RESPONSE")

    def test_backend_must_be_configured_and_url_is_constrained(self):
        client = TestClient(create_app(Path(self.directory.name) / "unconfigured.sqlite3", backend_url=""))
        try:
            response = client.get("/v1/backend/trips", headers={"Authorization": "Bearer user-jwt"})
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json()["detail"]["code"], "BACKEND_NOT_CONFIGURED")
        finally:
            client.close()
        for url in ("file:///tmp/backend", "http://user:password@backend.test", "http://backend.test?token=secret"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                BackendTripsClient(url)


if __name__ == "__main__":
    unittest.main()
