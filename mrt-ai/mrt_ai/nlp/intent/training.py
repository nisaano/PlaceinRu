"""Training and evaluation primitives for the MRT-AI multi-label intent head."""
import random
from pathlib import Path
import json

import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModel, AutoTokenizer

from mrt_ai.nlp.intent.dataset import DATASET_PATH, load_dataset, model_input
from mrt_ai.nlp.intent.taxonomy import INTENTS

ENCODER_ID = "cointegrated/rubert-tiny2"
ENCODER_REVISION = "e8ed3b0c8bbf4fb6984c3de043bf7d2f4e5969ae"
MODEL_DIR = Path(__file__).resolve().parents[3] / "models" / "encoders" / "rubert_tiny2"
OUTPUT_DIR = Path(__file__).resolve().parents[3] / "models" / "classifiers" / "misha-intent-rubert-tiny2"
MAX_LENGTH = 128


class IntentDataset(Dataset):
    def __init__(self, rows: list[dict], tokenizer, max_length: int = MAX_LENGTH):
        self.rows = rows
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        row = self.rows[index]
        encoded = self.tokenizer(
            model_input(row),
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors="pt",
        )
        targets = torch.zeros(len(INTENTS), dtype=torch.float32)
        for label in row["labels"]:
            targets[INTENTS.index(label)] = 1.0
        return {
            "input_ids": encoded["input_ids"].squeeze(0),
            "attention_mask": encoded["attention_mask"].squeeze(0),
            "targets": targets,
        }


class MrtAiIntentModel(nn.Module):
    def __init__(self, encoder):
        super().__init__()
        self.encoder = encoder
        hidden_size = encoder.config.hidden_size
        self.dropout = nn.Dropout(0.1)
        self.classifier = nn.Linear(hidden_size, len(INTENTS))

    def forward(self, input_ids, attention_mask):
        output = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        pooled = output.last_hidden_state[:, 0]
        return self.classifier(self.dropout(pooled))


def compute_metrics(
    logits: torch.Tensor,
    targets: torch.Tensor,
    threshold: float | torch.Tensor = 0.5,
) -> dict:
    predictions = torch.sigmoid(logits) >= threshold
    targets = targets.bool()
    true_positive = (predictions & targets).sum(dim=0).float()
    false_positive = (predictions & ~targets).sum(dim=0).float()
    false_negative = (~predictions & targets).sum(dim=0).float()
    precision = true_positive / (true_positive + false_positive).clamp(min=1)
    recall = true_positive / (true_positive + false_negative).clamp(min=1)
    f1 = 2 * precision * recall / (precision + recall).clamp(min=1e-12)
    exact_match = (predictions == targets).all(dim=1).float().mean().item()
    return {
        "macro_f1": f1.mean().item(),
        "micro_f1": (2 * true_positive.sum() / (2 * true_positive.sum() + false_positive.sum() + false_negative.sum()).clamp(min=1)).item(),
        "exact_match": exact_match,
        "per_intent": {
            intent: {
                "precision": precision[index].item(),
                "recall": recall[index].item(),
                "f1": f1[index].item(),
                "support": int(targets[:, index].sum().item()),
            }
            for index, intent in enumerate(INTENTS)
        },
    }


def evaluate_model(
    model,
    dataloader,
    device: torch.device,
    threshold: float | torch.Tensor = 0.5,
) -> tuple[dict, torch.Tensor, torch.Tensor]:
    model.eval()
    logits_list, targets_list = [], []
    with torch.inference_mode():
        for batch in dataloader:
            logits_list.append(model(
                batch["input_ids"].to(device),
                batch["attention_mask"].to(device),
            ).cpu())
            targets_list.append(batch["targets"])
    logits = torch.cat(logits_list)
    targets = torch.cat(targets_list)
    return compute_metrics(logits, targets, threshold), logits, targets


def select_global_threshold(logits: torch.Tensor, targets: torch.Tensor) -> tuple[float, dict]:
    candidates = [round(value / 100, 2) for value in range(10, 91, 5)]
    scored = [
        (compute_metrics(logits, targets, threshold), threshold)
        for threshold in candidates
    ]
    metrics, threshold = max(
        scored,
        key=lambda item: (item[0]["macro_f1"], item[0]["exact_match"], -abs(item[1] - 0.5)),
    )
    return threshold, metrics


def train(
    epochs: int = 5,
    batch_size: int = 8,
    learning_rate: float = 2e-5,
    seed: int = 17,
    encoder_dir: Path = MODEL_DIR,
    dataset_path: Path = DATASET_PATH,
    output_dir: Path = OUTPUT_DIR,
) -> dict:
    random.seed(seed)
    torch.manual_seed(seed)
    torch.set_num_threads(max(1, min(4, torch.get_num_threads())))
    payload = load_dataset(dataset_path)
    if not (encoder_dir / "mrt-ai-encoder.json").is_file():
        raise FileNotFoundError(
            f"Verified local RuBERT-tiny2 encoder not found at {encoder_dir}; "
            "run `python -m scripts.download_intent_encoder` first."
        )
    manifest = json.loads((encoder_dir / "mrt-ai-encoder.json").read_text(encoding="utf-8"))
    if (
        manifest.get("model_id") != ENCODER_ID
        or manifest.get("revision") != ENCODER_REVISION
        or manifest.get("license") != "MIT"
        or manifest.get("role") != "pretrained_encoder"
    ):
        raise ValueError("The local RuBERT encoder manifest is not the pinned verified version.")
    tokenizer = AutoTokenizer.from_pretrained(encoder_dir, local_files_only=True)
    encoder = AutoModel.from_pretrained(
        encoder_dir,
        local_files_only=True,
        use_safetensors=True,
    )
    model = MrtAiIntentModel(encoder)
    device = torch.device("cpu")
    model.to(device)

    rows = payload["examples"]
    train_loader = DataLoader(
        IntentDataset([row for row in rows if row["split"] == "train"], tokenizer),
        batch_size=batch_size,
        shuffle=True,
    )
    validation_loader = DataLoader(
        IntentDataset([row for row in rows if row["split"] == "validation"], tokenizer),
        batch_size=batch_size,
    )
    test_loader = DataLoader(
        IntentDataset([row for row in rows if row["split"] == "test"], tokenizer),
        batch_size=batch_size,
    )
    if not len(train_loader.dataset) or not len(validation_loader.dataset) or not len(test_loader.dataset):
        raise ValueError("Train, validation and test splits must all contain examples.")

    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate)
    training_targets = torch.stack([IntentDataset([row], tokenizer)[0]["targets"] for row in train_loader.dataset.rows])
    positive_counts = training_targets.sum(dim=0)
    negative_counts = len(training_targets) - positive_counts
    positive_weights = (negative_counts / positive_counts.clamp(min=1)).clamp(min=1.0, max=10.0)
    criterion = nn.BCEWithLogitsLoss(pos_weight=positive_weights)
    best_validation_f1 = -1.0
    best_threshold = 0.5
    best_state = None
    history = []
    for epoch in range(epochs):
        model.train()
        losses = []
        for batch in train_loader:
            optimizer.zero_grad(set_to_none=True)
            logits = model(batch["input_ids"].to(device), batch["attention_mask"].to(device))
            loss = criterion(logits, batch["targets"].to(device))
            loss.backward()
            optimizer.step()
            losses.append(loss.item())
        _, validation_logits, validation_targets = evaluate_model(model, validation_loader, device)
        epoch_threshold, validation_metrics = select_global_threshold(
            validation_logits,
            validation_targets,
        )
        history.append({
            "epoch": epoch + 1,
            "mean_train_loss": sum(losses) / len(losses),
            "validation": validation_metrics,
        })
        if validation_metrics["macro_f1"] > best_validation_f1:
            best_validation_f1 = validation_metrics["macro_f1"]
            best_threshold = epoch_threshold
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}

    if best_state is None:
        raise RuntimeError("Training did not produce a checkpoint.")
    model.load_state_dict(best_state)
    test_metrics, _, _ = evaluate_model(model, test_loader, device, best_threshold)
    output_dir.mkdir(parents=True, exist_ok=True)
    model.encoder.save_pretrained(output_dir / "encoder", safe_serialization=True)
    tokenizer.save_pretrained(output_dir / "encoder")
    from safetensors.torch import save_file
    save_file(
        {key: value.contiguous() for key, value in model.classifier.state_dict().items()},
        output_dir / "classifier.safetensors",
    )
    report = {
        "model_name": "mrt-ai-misha-intent-rubert-tiny2",
        "model_role": "multilabel_intent_classifier",
        "encoder": {"id": ENCODER_ID, "revision": ENCODER_REVISION, "license": "MIT"},
        "dataset_version": payload["dataset_version"],
        "dataset_provenance": "synthetic_manual",
        "labels": list(INTENTS),
        "split_counts": {
            split: sum(row["split"] == split for row in rows)
            for split in ("train", "validation", "test")
        },
        "seed": seed,
        "epochs": epochs,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "classification_threshold": best_threshold,
        "best_validation_macro_f1": best_validation_f1,
        "test_metrics": test_metrics,
        "training_history": history,
        "quality_notice": (
            "Synthetic pilot only. This checkpoint must not be used as a production "
            "classifier or connected to Misha without a real held-out benchmark."
        ),
    }
    (output_dir / "mrt-ai-intent-model.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report
