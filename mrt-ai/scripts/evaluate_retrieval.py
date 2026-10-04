"""Evaluate BM25 or local SBERT search on the synthetic fixture set."""
import argparse
import json
import math
import time
from pathlib import Path

from mrt_ai.contracts.catalog import FixturePlaceCatalog
from mrt_ai.retrieval.bm25 import BM25PlaceSearch
from mrt_ai.retrieval.encoders.sbert import MODEL_ID, MODEL_REVISION, LocalSbertPlaceSearch

ROOT = Path(__file__).resolve().parent.parent
PLACES = ROOT / "data" / "fixtures" / "places.json"
RELEVANCE = ROOT / "data" / "fixtures" / "search-relevance.json"


def dcg(grades: list[int]) -> float:
    return sum((2**grade - 1) / math.log2(index + 2) for index, grade in enumerate(grades))


def evaluate(
    top_k: int = 5,
    ranking_method: str = "bm25",
    embedding_searcher: LocalSbertPlaceSearch | None = None,
) -> dict:
    catalogue = FixturePlaceCatalog.model_validate_json(PLACES.read_text(encoding="utf-8"))
    dataset = json.loads(RELEVANCE.read_text(encoding="utf-8"))
    if ranking_method not in {"bm25", "embedding"}:
        raise ValueError("ranking_method must be 'bm25' or 'embedding'")
    searcher = embedding_searcher
    if ranking_method == "embedding" and searcher is None:
        searcher = LocalSbertPlaceSearch(
            ROOT / "models" / "embeddings" / "sbert_large_nlu_ru"
        )
    warmup_seconds = 0.0
    if ranking_method == "embedding":
        if searcher is None:
            raise RuntimeError("Embedding searcher was not initialized.")
        warmup_started = time.perf_counter()
        warmed_regions = set()
        for query_case in dataset["queries"]:
            if query_case["region_id"] in warmed_regions:
                continue
            candidates = [
                candidate for candidate in catalogue.candidates
                if candidate.region_id == query_case["region_id"]
            ]
            searcher.warmup(query_case["query"], candidates)
            warmed_regions.add(query_case["region_id"])
        warmup_seconds = time.perf_counter() - warmup_started
    per_query = []
    latencies_ms = []
    for query_case in dataset["queries"]:
        candidates = [
            candidate for candidate in catalogue.candidates
            if candidate.region_id == query_case["region_id"]
        ]
        started = time.perf_counter()
        if ranking_method == "embedding":
            if searcher is None:
                raise RuntimeError("Embedding searcher was not initialized.")
            hits = searcher.search(query_case["query"], candidates, top_k)
            latencies_ms.append((time.perf_counter() - started) * 1000)
        else:
            hits = BM25PlaceSearch(candidates).search(query_case["query"], top_k)
        relevant = query_case["relevant"]
        ranked_ids = [hit.candidate.object_id for hit in hits]
        ranked_grades = [relevant.get(object_id, 0) for object_id in ranked_ids]
        ideal_grades = sorted(relevant.values(), reverse=True)[:top_k]
        ideal_dcg = dcg(ideal_grades)
        reciprocal_rank = next(
            (1 / rank for rank, object_id in enumerate(ranked_ids, start=1) if object_id in relevant),
            0.0,
        )
        recall = len(set(ranked_ids) & set(relevant)) / len(relevant) if relevant else 1.0
        per_query.append({
            "id": query_case["id"],
            "ndcg_at_k": dcg(ranked_grades) / ideal_dcg if ideal_dcg else 0.0,
            "recall_at_k": recall,
            "reciprocal_rank": reciprocal_rank,
            "top_ids": ranked_ids,
        })
    count = len(per_query)
    result = {
        "data_mode": "fixture",
        "ranking_version": (
            "bm25-lexical-v1" if ranking_method == "bm25"
            else "sbert-large-nlu-ru-mean-v1"
        ),
        "dataset_version": dataset["dataset_version"],
        "query_count": count,
        "k": top_k,
        "mean_ndcg_at_k": sum(row["ndcg_at_k"] for row in per_query) / count if count else 0.0,
        "mean_recall_at_k": sum(row["recall_at_k"] for row in per_query) / count if count else 0.0,
        "mean_reciprocal_rank": sum(row["reciprocal_rank"] for row in per_query) / count if count else 0.0,
        "per_query": per_query,
        "notice": "Синтетическая smoke-метрика; не является оценкой качества на реальном пользовательском трафике.",
    }
    if ranking_method == "embedding":
        sorted_latencies = sorted(latencies_ms)
        result["model"] = {"id": MODEL_ID, "revision": MODEL_REVISION}
        result["query_latency_ms"] = {
            "mean": sum(latencies_ms) / len(latencies_ms) if latencies_ms else 0.0,
            "p50": sorted_latencies[math.ceil(0.50 * len(sorted_latencies)) - 1] if sorted_latencies else 0.0,
            "p95": sorted_latencies[math.ceil(0.95 * len(sorted_latencies)) - 1] if sorted_latencies else 0.0,
            "note": "CPU wall time after all model/candidate warmup; query only.",
        }
        result["warmup_seconds"] = round(warmup_seconds, 3)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ranking-method", choices=("bm25", "embedding"), default="bm25")
    args = parser.parse_args()
    print(json.dumps(evaluate(ranking_method=args.ranking_method), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
