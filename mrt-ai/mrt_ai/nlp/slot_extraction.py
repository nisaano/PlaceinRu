"""Loading helpers for the versioned trip-slot extraction benchmark."""
import json
from pathlib import Path


DATASET_PATH = Path(__file__).resolve().parents[2] / "data" / "datasets" / "trip-slots-v1.json"
SPLITS = {"train", "validation", "test"}


def load_trip_slot_dataset(path: Path = DATASET_PATH) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    slot_paths = payload.get("slot_paths")
    examples = payload.get("examples")
    if payload.get("dataset_version") != "trip-slots-synthetic-v2" or payload.get("data_mode") != "fixture":
        raise ValueError("Unsupported trip-slot dataset version or data mode.")
    if not isinstance(slot_paths, list) or not slot_paths or len(slot_paths) != len(set(slot_paths)):
        raise ValueError("Trip-slot dataset must declare unique slot paths.")
    if not isinstance(examples, list) or not examples:
        raise ValueError("Trip-slot dataset is empty.")

    ids = set()
    families_by_split: dict[str, set[str]] = {}
    for row in examples:
        if not isinstance(row, dict):
            raise ValueError("Trip-slot example must be an object.")
        example_id = row.get("id")
        family_id = row.get("family_id")
        split = row.get("split")
        if not example_id or example_id in ids:
            raise ValueError(f"Missing or duplicate trip-slot example id: {example_id}.")
        ids.add(example_id)
        if not family_id or split not in SPLITS:
            raise ValueError(f"Invalid family or split for trip-slot example {example_id}.")
        if not row.get("text") or row.get("provenance") != "synthetic_manual":
            raise ValueError(f"Incomplete or unsupported trip-slot example {example_id}.")
        expected = row.get("expected")
        if not isinstance(expected, dict) or set(expected) != set(slot_paths):
            raise ValueError(f"Example {example_id} must annotate every declared slot.")
        families_by_split.setdefault(split, set()).add(family_id)

    splits = sorted(families_by_split)
    for index, split in enumerate(splits):
        for other in splits[index + 1:]:
            overlap = families_by_split[split] & families_by_split[other]
            if overlap:
                raise ValueError(f"Trip-slot family leakage between {split} and {other}: {sorted(overlap)}")
    if splits != ["test", "train", "validation"]:
        raise ValueError("Trip-slot dataset must contain train, validation, and test families.")
    return payload
