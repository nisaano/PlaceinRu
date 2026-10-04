import json
import tempfile
import unittest
from pathlib import Path

from mrt_ai.nlp.slot_extraction import DATASET_PATH, load_trip_slot_dataset
from scripts.build_trip_slot_dataset import build
from scripts.evaluate_trip_slot_baseline import evaluate


class TripSlotDatasetTests(unittest.TestCase):
    def test_dataset_is_reproducible_and_splits_whole_families(self):
        dataset = load_trip_slot_dataset()
        self.assertEqual(dataset, build())
        self.assertEqual(len(dataset["examples"]), 63)
        self.assertEqual(
            {split: sum(row["split"] == split for row in dataset["examples"])
             for split in ("train", "validation", "test")},
            {"train": 15, "validation": 33, "test": 15},
        )
        families = {
            split: {row["family_id"] for row in dataset["examples"] if row["split"] == split}
            for split in ("train", "validation", "test")
        }
        self.assertFalse(families["train"] & families["validation"])
        self.assertFalse(families["train"] & families["test"])
        self.assertFalse(families["validation"] & families["test"])

    def test_loader_rejects_family_leakage(self):
        dataset = build()
        dataset["examples"][15]["family_id"] = dataset["examples"][0]["family_id"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_text(json.dumps(dataset), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "family leakage"):
                load_trip_slot_dataset(path)

    def test_baseline_evaluator_reports_all_slots_and_splits(self):
        result = evaluate(DATASET_PATH)
        self.assertEqual(result["examples"], 63)
        self.assertEqual(result["slot_count"], 8)
        self.assertEqual(set(result["per_split"]), {"train", "validation", "test"})
        self.assertEqual(set(result["per_split"]["test"]["slot_accuracy"]), set(build()["slot_paths"]))
        self.assertGreaterEqual(result["overall_macro_slot_accuracy"], 0)
        self.assertLessEqual(result["overall_macro_slot_accuracy"], 1)


if __name__ == "__main__":
    unittest.main()
