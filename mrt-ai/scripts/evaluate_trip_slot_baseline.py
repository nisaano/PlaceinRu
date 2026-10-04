"""Measure exact normalized trip-slot extraction by the current rules parser."""
import json
from datetime import datetime
from pathlib import Path

from app.contracts import TripRequest
from app.dialogue import parse, reduce_trip
from mrt_ai.nlp.slot_extraction import load_trip_slot_dataset


ROOT = Path(__file__).resolve().parent.parent
def get_slot(trip: dict, path: str):
    value = trip
    for part in path.split("."):
        value = value[part]
    return value


def evaluate(path: Path | None = None) -> dict:
    payload = load_trip_slot_dataset(path) if path else load_trip_slot_dataset()
    reference = datetime.fromisoformat(payload["reference_datetime"])
    timezone = payload["timezone"]
    counts = {
        split: {slot: {"correct": 0, "total": 0} for slot in payload["slot_paths"]}
        for split in ("train", "validation", "test")
    }
    exact_matches = {split: 0 for split in counts}
    rows = {split: 0 for split in counts}
    test_errors = []

    for row in payload["examples"]:
        split = row["split"]
        parsed = parse(
            row["text"],
            TripRequest(),
            row.get("pending_question"),
            reference,
            timezone,
        )
        try:
            proposed = reduce_trip(TripRequest(), parsed["updates"], reference.date())
        except (ValueError, TypeError) as error:
            raise ValueError(
                f"Trip-slot example {row['id']} cannot be reduced: {error}"
            ) from error
        actual_trip = proposed.model_dump(mode="json")
        correct_slots = 0
        example_errors = {}
        for slot in payload["slot_paths"]:
            expected = row["expected"][slot]
            actual = get_slot(actual_trip, slot)
            if slot == "interests":
                expected = sorted(expected)
                actual = sorted(actual)
            correct = actual == expected
            counts[split][slot]["correct"] += int(correct)
            counts[split][slot]["total"] += 1
            correct_slots += int(correct)
            if not correct:
                example_errors[slot] = {"expected": expected, "actual": actual}
        exact_matches[split] += int(correct_slots == len(payload["slot_paths"]))
        rows[split] += 1
        if split == "test" and example_errors:
            test_errors.append({
                "id": row["id"],
                "text": row["text"],
                "mismatches": example_errors,
            })

    per_split = {}
    for split in rows:
        slot_accuracy = {
            slot: counts[split][slot]["correct"] / counts[split][slot]["total"]
            for slot in payload["slot_paths"]
        }
        per_split[split] = {
            "examples": rows[split],
            "exact_match": exact_matches[split] / rows[split],
            "macro_slot_accuracy": sum(slot_accuracy.values()) / len(slot_accuracy),
            "slot_accuracy": slot_accuracy,
        }
    total_rows = sum(rows.values())
    return {
        "dataset_version": payload["dataset_version"],
        "data_mode": payload["data_mode"],
        "examples": total_rows,
        "slot_count": len(payload["slot_paths"]),
        "overall_exact_match": sum(exact_matches.values()) / total_rows,
        "overall_macro_slot_accuracy": sum(
            sum(value["correct"] / value["total"] for value in split.values()) / len(split)
            for split in counts.values()
        ) / len(counts),
        "per_split": per_split,
        "test_errors": test_errors,
    }


def main() -> None:
    print(json.dumps(evaluate(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
