"""Local inference adapter for an experimental MRT-AI intent checkpoint."""
import json
from pathlib import Path

import torch
from safetensors.torch import load_file
from transformers import AutoModel, AutoTokenizer

from mrt_ai.nlp.intent.taxonomy import INTENTS
from mrt_ai.nlp.intent.training import MAX_LENGTH, MrtAiIntentModel, model_input


class MrtAiIntentClassifier:
    def __init__(self, model, tokenizer, threshold: float = 0.5):
        if not 0 < threshold < 1:
            raise ValueError("Intent threshold must be between 0 and 1.")
        self.model = model.eval()
        self.tokenizer = tokenizer
        self.threshold = threshold

    @classmethod
    def load(cls, model_dir: Path, threshold: float | None = None):
        manifest_path = model_dir / "mrt-ai-intent-model.json"
        classifier_path = model_dir / "classifier.safetensors"
        encoder_dir = model_dir / "encoder"
        if not manifest_path.is_file() or not classifier_path.is_file():
            raise FileNotFoundError(f"Incomplete MRT-AI intent checkpoint: {model_dir}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (
            manifest.get("model_name") != "mrt-ai-misha-intent-rubert-tiny2"
            or manifest.get("model_role") != "multilabel_intent_classifier"
            or manifest.get("labels") != list(INTENTS)
            or manifest.get("encoder", {}).get("id") != "cointegrated/rubert-tiny2"
        ):
            raise ValueError("Intent checkpoint manifest does not match the MRT-AI classifier contract.")
        if threshold is None:
            threshold = manifest.get("classification_threshold", 0.5)
        tokenizer = AutoTokenizer.from_pretrained(encoder_dir, local_files_only=True)
        encoder = AutoModel.from_pretrained(
            encoder_dir,
            local_files_only=True,
            use_safetensors=True,
        )
        model = MrtAiIntentModel(encoder)
        model.classifier.load_state_dict(load_file(str(classifier_path), device="cpu"))
        return cls(model, tokenizer, threshold)

    def predict(self, text: str, pending_question: str | None = None, previous_trip: str = "unknown") -> list[dict]:
        return [
            row for row in self.predict_scores(text, pending_question, previous_trip)
            if row["score"] >= self.threshold
        ]

    def predict_scores(self, text: str, pending_question: str | None = None, previous_trip: str = "unknown") -> list[dict]:
        if not text.strip():
            raise ValueError("Intent input must not be blank.")
        row = {
            "text": text,
            "pending_question": pending_question,
            "previous_trip": previous_trip,
        }
        encoded = self.tokenizer(
            model_input(row),
            truncation=True,
            max_length=MAX_LENGTH,
            return_tensors="pt",
        )
        with torch.inference_mode():
            probabilities = torch.sigmoid(self.model(
                encoded["input_ids"],
                encoded["attention_mask"],
            )[0])
        return [
            {"intent": intent, "score": float(probabilities[index])}
            for index, intent in enumerate(INTENTS)
        ]
