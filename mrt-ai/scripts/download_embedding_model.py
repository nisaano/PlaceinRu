"""Download the pinned Russian SBERT snapshot into the local, ignored model cache."""
import hashlib
import json
from pathlib import Path

from huggingface_hub import snapshot_download

ROOT = Path(__file__).resolve().parent.parent
MODEL_ID = "ai-forever/sbert_large_nlu_ru"
MODEL_REVISION = "89deeaa197d9d146e5763ac1f5fe32bf66817126"
MODEL_SHA256 = "cea5e5ebffd98391d7c119f2d35a50e546aad6aea7c883bb584754874d27f622"
MODEL_SIZE = 1_707_679_808
MODEL_DIR = ROOT / "models" / "embeddings" / "sbert_large_nlu_ru"


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
            "1_Pooling/config.json",
            "config.json",
            "config_sentence_transformers.json",
            "model.safetensors",
            "modules.json",
            "special_tokens_map.json",
            "tokenizer.json",
            "tokenizer_config.json",
            "vocab.txt",
        ],
    )

    weights = MODEL_DIR / "model.safetensors"
    if not weights.is_file() or weights.stat().st_size != MODEL_SIZE:
        raise RuntimeError("Downloaded SBERT weights are missing or have an unexpected size.")
    actual_sha256 = sha256(weights)
    if actual_sha256 != MODEL_SHA256:
        raise RuntimeError("Downloaded SBERT weights failed the pinned SHA-256 check.")

    manifest = {
        "model_id": MODEL_ID,
        "revision": MODEL_REVISION,
        "license": "MIT",
        "role": "embedding_encoder",
        "weights_file": "model.safetensors",
        "weights_size_bytes": MODEL_SIZE,
        "weights_sha256": MODEL_SHA256,
    }
    (MODEL_DIR / "mrt-ai-model.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Verified {MODEL_ID}@{MODEL_REVISION} in {MODEL_DIR}")


if __name__ == "__main__":
    main()
