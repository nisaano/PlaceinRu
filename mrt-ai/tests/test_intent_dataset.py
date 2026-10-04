import unittest
from pathlib import Path

from mrt_ai.nlp.intent.taxonomy import INTENTS
from mrt_ai.nlp.intent.dataset import load_dataset, model_input
from scripts.build_intent_dataset import build

ROOT = Path(__file__).resolve().parent.parent


class IntentDatasetTests(unittest.TestCase):
    def test_synthetic_dataset_is_balanced_and_family_separated(self):
        payload = build()
        self.assertEqual(len(payload["examples"]), 135)
        self.assertEqual(payload["labels"], list(INTENTS))
        families: dict[str, set[str]] = {}
        label_support: dict[str, dict[str, int]] = {}
        for row in payload["examples"]:
            families.setdefault(row["split"], set()).add(row["family_id"])
            for label in row["labels"]:
                label_support.setdefault(label, {}).setdefault(row["split"], 0)
                label_support[label][row["split"]] += 1
            self.assertEqual(row["provenance"], "synthetic_manual")
        self.assertFalse(families["train"] & families["validation"])
        self.assertFalse(families["train"] & families["test"])
        self.assertFalse(families["validation"] & families["test"])
        self.assertTrue(all(set(counts) == {"train", "validation", "test"} for counts in label_support.values()))
        self.assertEqual(
            {split: sum(row["split"] == split for row in payload["examples"])
             for split in ("train", "validation", "test")},
            {"train": 81, "validation": 27, "test": 27},
        )

    def test_checked_in_dataset_matches_reproducible_builder(self):
        payload = load_dataset(ROOT / "data" / "datasets" / "intent-v1.json")
        self.assertEqual(payload, build())

    def test_model_input_includes_dialogue_context(self):
        self.assertEqual(
            model_input({
                "text": "Казань",
                "pending_question": "origin",
                "previous_trip": "partial",
            }),
            "[trip=partial] [pending=origin] Казань",
        )


if __name__ == "__main__":
    unittest.main()
