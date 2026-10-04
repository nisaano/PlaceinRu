import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from mrt_ai.nlp.intent.taxonomy import INTENTS


REFERENCE = datetime.fromisoformat("2026-10-04T12:00:00+03:00")


class FakeIntentClassifier:
    threshold = 0.7

    def __init__(self):
        self.inputs = []

    def predict_scores(self, message, pending_question, previous_trip):
        self.inputs.append((message, pending_question, previous_trip))
        return [
            {"intent": intent, "score": 0.91 if intent == "CHANGE_BUDGET" else 0.2}
            for intent in INTENTS
        ]


class IntentChatTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.database = Path(self.directory.name) / "sessions.sqlite3"

    def tearDown(self):
        self.directory.cleanup()

    def test_developer_probe_compares_model_and_rules_with_dialogue_context(self):
        classifier = FakeIntentClassifier()
        app = create_app(
            self.database,
            clock=lambda: REFERENCE,
            enable_intent_test=True,
            intent_classifier=classifier,
        )
        with TestClient(app) as client:
            response = client.post("/v1/dev/intent", json={
                "message": "60000",
                "pending_question": "budget.amount_minor",
            })

        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(result["model"], "mrt-ai-misha-intent-rubert-tiny2")
        self.assertEqual(result["threshold"], 0.7)
        self.assertEqual(len(result["classifier"]), len(INTENTS))
        self.assertIn("CHANGE_BUDGET", [
            row["intent"] for row in result["classifier"] if row["selected"]
        ])
        self.assertEqual(result["rules_v1"], ["CREATE_TRIP", "CHANGE_BUDGET"])
        self.assertEqual(
            classifier.inputs,
            [("60000", "budget.amount_minor", "empty")],
        )

    def test_classifier_probe_is_not_exposed_by_regular_api(self):
        app = create_app(self.database)
        with TestClient(app) as client:
            response = client.post("/v1/dev/intent", json={"message": "хочу в поездку"})
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
