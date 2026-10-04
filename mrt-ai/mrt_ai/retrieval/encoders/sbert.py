"""Local CPU sentence-embedding retrieval for explicitly synthetic candidates."""
import json
import math
import threading
from pathlib import Path
from typing import Callable

from mrt_ai.contracts.catalog import Candidate, PlaceSearchHit

MODEL_ID = "ai-forever/sbert_large_nlu_ru"
MODEL_REVISION = "89deeaa197d9d146e5763ac1f5fe32bf66817126"
MODEL_SHA256 = "cea5e5ebffd98391d7c119f2d35a50e546aad6aea7c883bb584754874d27f622"
RANKING_VERSION = "sbert-large-nlu-ru-mean-v1"
MAX_CACHED_CANDIDATE_SETS = 8


class EmbeddingModelUnavailable(RuntimeError):
    """Raised when the verified local model or its runtime dependencies are absent."""


class LocalSbertPlaceSearch:
    def __init__(
        self,
        model_dir: Path,
        encode_texts: Callable[[list[str]], list[list[float]]] | None = None,
    ):
        self.model_dir = model_dir
        self._test_encoder = encode_texts
        self._tokenizer = None
        self._model = None
        self._torch = None
        self._lock = threading.RLock()
        self._candidate_vectors: dict[tuple[str, ...], list[list[float]]] = {}

    def _cache_candidate_vectors(
        self,
        key: tuple[str, ...],
        vectors: list[list[float]],
    ) -> None:
        if key not in self._candidate_vectors and len(self._candidate_vectors) >= MAX_CACHED_CANDIDATE_SETS:
            self._candidate_vectors.pop(next(iter(self._candidate_vectors)))
        self._candidate_vectors[key] = vectors

    @staticmethod
    def _candidate_text(candidate: Candidate) -> str:
        return " ".join((candidate.name, " ".join(candidate.tags), candidate.description))

    @classmethod
    def _candidate_key(cls, candidates: list[Candidate]) -> tuple[str, ...]:
        return tuple(
            candidate.object_id + "\0" + cls._candidate_text(candidate)
            for candidate in candidates
        )

    @staticmethod
    def _normalize(vectors: list[list[float]]) -> list[list[float]]:
        dimensions = {len(vector) for vector in vectors}
        if len(dimensions) > 1 or (dimensions and next(iter(dimensions)) == 0):
            raise ValueError("Embedding model returned inconsistent vector dimensions.")
        normalized = []
        for vector in vectors:
            norm = math.sqrt(sum(value * value for value in vector))
            if norm == 0:
                raise ValueError("Embedding model produced a zero-length vector.")
            normalized.append([value / norm for value in vector])
        return normalized

    def _load_model(self) -> None:
        if self._model is not None:
            return
        manifest_path = self.model_dir / "mrt-ai-model.json"
        weights_path = self.model_dir / "model.safetensors"
        if not manifest_path.is_file() or not weights_path.is_file():
            raise EmbeddingModelUnavailable(
                "Локальный SBERT encoder не загружен. Выполните "
                "`python -m scripts.download_embedding_model`."
            )
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise EmbeddingModelUnavailable("Manifest локальной embedding-модели повреждён.") from error
        if (
            manifest.get("model_id") != MODEL_ID
            or manifest.get("revision") != MODEL_REVISION
            or manifest.get("license") != "MIT"
            or manifest.get("role") != "embedding_encoder"
            or manifest.get("weights_sha256") != MODEL_SHA256
            or manifest.get("weights_file") != "model.safetensors"
        ):
            raise EmbeddingModelUnavailable(
                f"В {self.model_dir} находится не закреплённая версия encoder {MODEL_ID}."
            )
        try:
            import torch
            from transformers import AutoModel, AutoTokenizer
        except ImportError as error:
            raise EmbeddingModelUnavailable(
                "Для semantic search установите зависимости из requirements-ml.txt."
            ) from error
        try:
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_dir,
                local_files_only=True,
            )
            self._model = AutoModel.from_pretrained(
                self.model_dir,
                local_files_only=True,
                use_safetensors=True,
            ).to("cpu")
        except OSError as error:
            raise EmbeddingModelUnavailable(
                "Не удалось открыть локальные файлы embedding-модели."
            ) from error
        self._model.eval()
        self._torch = torch

    def _encode(self, texts: list[str]) -> list[list[float]]:
        if self._test_encoder is not None:
            return self._normalize(self._test_encoder(texts))

        self._load_model()
        vectors = []
        for start in range(0, len(texts), 4):
            encoded = self._tokenizer(
                texts[start:start + 4],
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt",
            )
            with self._torch.inference_mode():
                output = self._model(**encoded)
                token_vectors = output.last_hidden_state
                mask = encoded["attention_mask"].unsqueeze(-1).to(token_vectors.dtype)
                sentence_vectors = (token_vectors * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)
                sentence_vectors = self._torch.nn.functional.normalize(sentence_vectors, p=2, dim=1)
            vectors.extend(sentence_vectors.cpu().tolist())
        return vectors

    def warmup(self, query: str, candidates: list[Candidate]) -> None:
        if not candidates:
            return
        key = self._candidate_key(candidates)
        with self._lock:
            if self._test_encoder is None:
                self._load_model()
            if key not in self._candidate_vectors:
                self._cache_candidate_vectors(
                    key,
                    self._encode([self._candidate_text(candidate) for candidate in candidates]),
                )
            self._encode([query])

    def search(self, query: str, candidates: list[Candidate], top_k: int = 5) -> list[PlaceSearchHit]:
        if not candidates:
            return []
        key = self._candidate_key(candidates)
        with self._lock:
            candidate_vectors = self._candidate_vectors.get(key)
            if candidate_vectors is None:
                candidate_vectors = self._encode(
                    [self._candidate_text(candidate) for candidate in candidates]
                )
                self._cache_candidate_vectors(key, candidate_vectors)
            query_vector = self._encode([query])[0]

        if any(len(query_vector) != len(vector) for vector in candidate_vectors):
            raise ValueError("Query and candidate embedding dimensions do not match.")
        hits = []
        for candidate, vector in zip(candidates, candidate_vectors):
            cosine = sum(left * right for left, right in zip(query_vector, vector))
            hits.append(PlaceSearchHit(
                candidate=candidate,
                score=round((cosine + 1.0) / 2.0, 6),
                matched_terms=[],
            ))
        hits.sort(key=lambda hit: (-hit.score, hit.candidate.object_id))
        return hits[:top_k]
