"""Dependency-free loading and validation for the versioned intent corpus."""
import json
from pathlib import Path
from typing import Any

from mrt_ai.nlp.intent.taxonomy import INTENTS

DATASET_PATH = Path(__file__).resolve().parents[3] / "data" / "datasets" / "intent-v1.json"


def model_input(record: dict[str, Any]) -> str:
    pending = record.get("pending_question") or "none"
    previous_trip = record.get("previous_trip", "unknown")
    return f"[trip={previous_trip}] [pending={pending}] {record['text']}"


def load_dataset(path: Path = DATASET_PATH) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("labels") != list(INTENTS):
        raise ValueError("Dataset labels do not match the current MRT-AI intent taxonomy.")
    examples = payload.get("examples")
    if not isinstance(examples, list) or not examples:
        raise ValueError("Intent dataset is empty.")
    ids = set()
    for row in examples:
        if row.get("id") in ids:
            raise ValueError(f"Duplicate intent example id: {row.get('id')}.")
        ids.add(row.get("id"))
        if row.get("split") not in {"train", "validation", "test"}:
            raise ValueError(f"Invalid split for example {row.get('id')}.")
        if not row.get("text") or not row.get("family_id"):
            raise ValueError(f"Incomplete intent example {row.get('id')}.")
        if row.get("provenance") != "synthetic_manual":
            raise ValueError(f"Unsupported provenance for intent example {row.get('id')}.")
        if not row.get("labels") or set(row["labels"]) - set(INTENTS):
            raise ValueError(f"Invalid labels for intent example {row.get('id')}.")
    families_by_split: dict[str, set[str]] = {}
    for row in examples:
        families_by_split.setdefault(row["split"], set()).add(row["family_id"])
    splits = list(families_by_split)
    for index, split in enumerate(splits):
        for other in splits[index + 1:]:
            overlap = families_by_split[split] & families_by_split[other]
            if overlap:
                raise ValueError(f"Intent family leakage between {split} and {other}: {sorted(overlap)}")
    return payload
