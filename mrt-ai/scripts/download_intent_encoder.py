"""Download the pinned RuBERT-tiny2 encoder into the local ignored model cache."""
import hashlib
import json
from pathlib import Path

from huggingface_hub import snapshot_download

ROOT = Path(__file__).resolve().parent.parent
MODEL_ID = "cointegrated/rubert-tiny2"
MODEL_REVISION = "e8ed3b0c8bbf4fb6984c3de043bf7d2f4e5969ae"
MODEL_SHA256 = "26ebb6db2a68593c54c74902d7a74f332da66297693f965cc9f1b0af4abf3894"
MODEL_SIZE = 117_529_600
MODEL_DIR = ROOT / "models" / "encoders" / "rubert_tiny2"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=MODEL_ID,
        revision=MODEL_REVISION,
        local_dir=MODEL_DIR,
        allow_patterns=[
            "config.json",
            "model.safetensors",
            "special_tokens_map.json",
            "tokenizer.json",
            "tokenizer_config.json",
            "vocab.txt",
        ],
    )

    weights = MODEL_DIR / "model.safetensors"
    if not weights.is_file() or weights.stat().st_size != MODEL_SIZE:
        raise RuntimeError("Downloaded RuBERT-tiny2 weights are missing or have an unexpected size.")
    if sha256(weights) != MODEL_SHA256:
        raise RuntimeError("Downloaded RuBERT-tiny2 weights failed the pinned SHA-256 check.")

    manifest = {
        "model_id": MODEL_ID,
        "revision": MODEL_REVISION,
        "license": "MIT",
        "role": "pretrained_encoder",
        "weights_file": "model.safetensors",
        "weights_size_bytes": MODEL_SIZE,
        "weights_sha256": MODEL_SHA256,
    }
    (MODEL_DIR / "mrt-ai-encoder.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Verified {MODEL_ID}@{MODEL_REVISION} in {MODEL_DIR}")


if __name__ == "__main__":
    main()
