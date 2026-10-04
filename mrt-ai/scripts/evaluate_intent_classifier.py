"""Evaluate the experimental multi-label classifier on its synthetic test split."""
import argparse
import json
from datetime import datetime
from pathlib import Path

import torch
from torch.utils.data import DataLoader

from app.contracts import TripRequest
from app.dialogue import parse
from mrt_ai.nlp.intent.classifier import MrtAiIntentClassifier
from mrt_ai.nlp.intent.dataset import load_dataset
from mrt_ai.nlp.intent.taxonomy import INTENTS
from mrt_ai.nlp.intent.training import (
    MAX_LENGTH,
    IntentDataset,
    evaluate_model,
)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL_DIR = ROOT / "models" / "classifiers" / "misha-intent-rubert-tiny2"


def rules_baseline(rows: list[dict]) -> dict:
    true_positive = torch.zeros(len(INTENTS))
    false_positive = torch.zeros(len(INTENTS))
    false_negative = torch.zeros(len(INTENTS))
    exact_matches = 0
    reference = datetime.fromisoformat("2026-10-04T12:00:00+03:00")
    for row in rows:
        trip = TripRequest() if row["previous_trip"] == "empty" else TripRequest(
            origin="Москва",
            interests=["природа"],
        )
        actual = set(row["labels"])
        predicted = set(parse(
            row["text"],
            trip,
            row.get("pending_question"),
            reference,
            "Europe/Moscow",
        )["intents"])
        exact_matches += int(actual == predicted)
        for index, label in enumerate(INTENTS):
            truth = label in actual
            prediction = label in predicted
            if truth and prediction:
                true_positive[index] += 1
            elif prediction:
                false_positive[index] += 1
            elif truth:
                false_negative[index] += 1
    precision = true_positive / (true_positive + false_positive).clamp(min=1)
    recall = true_positive / (true_positive + false_negative).clamp(min=1)
    f1 = 2 * precision * recall / (precision + recall).clamp(min=1e-12)
    return {
        "macro_f1": f1.mean().item(),
        "micro_f1": (2 * true_positive.sum() / (
            2 * true_positive.sum() + false_positive.sum() + false_negative.sum()
        ).clamp(min=1)).item(),
        "exact_match": exact_matches / len(rows) if rows else 0.0,
        "per_intent": {
            intent: {
                "precision": precision[index].item(),
                "recall": recall[index].item(),
                "f1": f1[index].item(),
                "support": int(sum(intent in row["labels"] for row in rows)),
            }
            for index, intent in enumerate(INTENTS)
        },
    }


def evaluate(model_dir: Path = DEFAULT_MODEL_DIR) -> dict:
    payload = load_dataset()
    test_rows = [row for row in payload["examples"] if row["split"] == "test"]
    if not test_rows:
        raise ValueError("Synthetic intent test split is empty.")
    classifier = MrtAiIntentClassifier.load(model_dir)
    tokenizer = classifier.tokenizer
    loader = DataLoader(IntentDataset(test_rows, tokenizer, MAX_LENGTH), batch_size=8)
    model_metrics, _, _ = evaluate_model(
        classifier.model,
        loader,
        torch.device("cpu"),
        classifier.threshold,
    )
    model_metrics["threshold"] = classifier.threshold
    return {
        "dataset_version": payload["dataset_version"],
        "data_mode": payload["data_mode"],
        "test_examples": len(test_rows),
        "mrt_ai_classifier": model_metrics,
        "rules_v1": rules_baseline(test_rows),
        "note": (
            "Synthetic pilot split only. Neither result estimates performance on "
            "real user traffic; classifier is not connected to Misha."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    args = parser.parse_args()
    print(json.dumps(evaluate(args.model_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
