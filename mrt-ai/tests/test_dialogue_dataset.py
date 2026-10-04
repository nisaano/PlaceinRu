import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import ROOT, create_app


DATASET = ROOT / "data" / "fixtures" / "dialogue-smoke.json"


class DialogueDatasetTests(unittest.TestCase):
    def test_synthetic_smoke_dialogues_cover_trip_request(self):
        dataset = json.loads(DATASET.read_text(encoding="utf-8"))
        self.assertEqual(dataset["data_mode"], "fixture")
        self.assertGreaterEqual(len(dataset["scenarios"]), 4)
        reference = datetime.fromisoformat(dataset["reference_datetime"])

        with tempfile.TemporaryDirectory(dir=ROOT / ".test-tmp") as directory:
            for scenario in dataset["scenarios"]:
                with self.subTest(scenario=scenario["id"]):
                    client = TestClient(create_app(
                        Path(directory) / f'{scenario["id"]}.sqlite3',
                        clock=lambda: reference,
                    ))
                    try:
                        state = client.post("/v1/sessions", json={"timezone": dataset["timezone"]}).json()
                        result = None
                        for index, message in enumerate(scenario["turns"]):
                            response = client.post(
                                f'/v1/sessions/{state["session_id"]}/turns',
                                json={
                                    "request_id": f'{scenario["id"]}-{index:03}',
                                    "expected_state_version": state["state_version"],
                                    "message": message,
                                },
                            )
                            self.assertEqual(response.status_code, 200, response.text)
                            result = response.json()
                            state = result["state"]
                            if "expected_pending_questions" in scenario:
                                self.assertEqual(
                                    state["pending_question"],
                                    scenario["expected_pending_questions"][index],
                                )

                        expected = scenario["expected"]
                        trip = state["trip"]
                        self.assertEqual(state["status"], expected["status"])
                        self.assertEqual(trip["mode"], expected["mode"])
                        self.assertEqual(trip["origin"], expected["origin"])
                        self.assertEqual(trip["destination"], expected["destination"])
                        self.assertEqual(trip["dates"]["start_date"], expected["start_date"])
                        self.assertEqual(trip["dates"]["duration_days"], expected["duration_days"])
                        self.assertEqual(trip["party"]["total_count"], expected["total_count"])
                        self.assertEqual(trip["party"]["has_children"], expected["has_children"])
                        self.assertEqual(trip["party"]["children_count"], expected["children_count"])
                        self.assertEqual(trip["interests"], expected["interests"])
                        recommended = {option["region_id"] for option in result["options"]}
                        self.assertTrue(set(expected["recommended_region_ids"]) <= recommended)
                    finally:
                        client.close()


if __name__ == "__main__":
    unittest.main()
