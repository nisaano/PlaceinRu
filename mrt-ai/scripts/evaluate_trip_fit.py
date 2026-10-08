"""Evaluate trip-fit ranking on the versioned, synthetic fixture relevance set."""
import json
import math
import argparse
from pathlib import Path

from app.catalog import RegionCatalog
from app.catalog_import import ROOT
from app.contracts import TripRequest
from app.providers import LocalCandidateProvider
from mrt_ai.contracts.catalog import CandidateQuery
from mrt_ai.ranking import TripCandidateRanker


DATASET = ROOT / "data/fixtures/trip-fit-relevance-v1.json"


def dcg(grades):
    return sum((2**grade - 1) / math.log2(index + 2) for index, grade in enumerate(grades))


def evaluate_case(case, provider, ranker):
    trip = TripRequest.model_validate(case["trip"])
    query = CandidateQuery(
        region_id=case["region_id"], data_mode="fixture",
        start_date=trip.dates.start_date,
        end_date=trip.dates.end_date,
        adults=trip.party.adults,
        children_ages=trip.party.children_ages,
    )
    batch = provider.query(query)
    response = ranker.rank(trip, batch)
    if response.ranking_version != ranker.version:
        raise RuntimeError(f"{case['id']}: version mismatch: {response.ranking_version}")

    grades = case["relevant"]
    ordered = [row.candidate.object_id for row in response.results]
    top5 = ordered[:5]
    observed_grades = [grades.get(object_id, 0) for object_id in top5]
    ideal = sorted(grades.values(), reverse=True)[:5]
    idcg = dcg(ideal)
    ndcg = dcg(observed_grades) / idcg if idcg else 0.0
    relevant_ids = {object_id for object_id, grade in grades.items() if grade > 0}
    recall = len(relevant_ids.intersection(top5)) / len(relevant_ids) if relevant_ids else 1.0
    reciprocal_rank = next((1 / (i + 1) for i, object_id in enumerate(ordered) if object_id in relevant_ids), 0.0)
    expected_unscored = set(case.get("expected_unscored", []))
    actual_unscored = set(response.unscored_factors)
    if expected_unscored and actual_unscored != expected_unscored:
        raise RuntimeError(f"{case['id']}: expected unscored={sorted(expected_unscored)}, got={sorted(actual_unscored)}")
    if case["group"] == "exclusions" and any("museum" in object_id for object_id in ordered):
        raise RuntimeError(f"{case['id']}: excluded museum candidate remained in results")
    if case["group"] == "guide_no" and any(":guide:" in object_id for object_id in ordered):
        raise RuntimeError(f"{case['id']}: guide returned although guide.required=false")
    positions = {object_id: index for index, object_id in enumerate(ordered)}
    for better_id, worse_id in case.get("must_rank_above", []):
        if better_id not in positions or worse_id not in positions or positions[better_id] >= positions[worse_id]:
            raise RuntimeError(f"{case['id']}: expected {better_id} above {worse_id}")
    for object_id in case.get("must_remain_ids", []):
        if object_id not in positions:
            raise RuntimeError(f"{case['id']}: related candidate was unexpectedly filtered: {object_id}")
    expected_unmatched = set(case.get("expected_unmatched_interests", []))
    if expected_unmatched:
        for row in response.results:
            if not expected_unmatched.issubset(row.unmatched_interests):
                raise RuntimeError(f"{case['id']}: unknown interests were marked matched: {row.matched_interests}")
    if case.get("expect_zero_scores") and any(row.score != 0 for row in response.results):
        raise RuntimeError(f"{case['id']}: unsupported interest unexpectedly produced a non-zero score")
    if case.get("expect_neutral_order_warning") and not any(
        "порядок карточек нейтральный" in warning.lower() for warning in response.warnings
    ):
        raise RuntimeError(f"{case['id']}: neutral ranking warning is missing")
    relevant_ids = {object_id for object_id, grade in grades.items() if grade > 0}
    return {
        "id": case["id"], "group": case["group"], "ndcg_at_5": round(ndcg, 4),
        "recall_at_5": round(recall, 4), "mrr": round(reciprocal_rank, 4),
        "top5": [{"object_id": row.candidate.object_id, "score": row.score,
                  "grade": grades.get(row.candidate.object_id, 0)} for row in response.results[:5]],
        "unscored_factors": response.unscored_factors,
        "excluded_count": len(response.excluded_object_ids),
        "metric_case": case.get("metric_case", True),
        "relevant_found_in_full_ranking": len(relevant_ids.intersection(ordered)),
        "relevant_count": len(relevant_ids),
        "missed_relevant_ids": sorted(relevant_ids - set(ordered)),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DATASET,
                        help="JSON relevance dataset (defaults to trip-fit-relevance-v1)")
    args = parser.parse_args()
    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    provider = LocalCandidateProvider(
        RegionCatalog(ROOT / "data/normalized/catalog.json"),
        ROOT / "data/fixtures/places.json",
    )
    ranker = TripCandidateRanker()
    results = [evaluate_case(case, provider, ranker) for case in dataset["cases"]]
    metric_results = [row for row in results if row["metric_case"]]
    summary = {
        "dataset_id": dataset["dataset_id"], "ranking_version": ranker.version,
        "case_count": len(results),
        "metric_case_count": len(metric_results),
        "diagnostic_case_count": len(results) - len(metric_results),
        "mean_ndcg_at_5": round(sum(row["ndcg_at_5"] for row in metric_results) / len(metric_results), 4),
        "mean_recall_at_5": round(sum(row["recall_at_5"] for row in metric_results) / len(metric_results), 4),
        "mean_mrr": round(sum(row["mrr"] for row in metric_results) / len(metric_results), 4),
        "by_group": {}, "cases": results,
    }
    for group in sorted({row["group"] for row in metric_results}):
        members = [row for row in metric_results if row["group"] == group]
        summary["by_group"][group] = {
            "cases": len(members),
            "mean_ndcg_at_5": round(sum(row["ndcg_at_5"] for row in members) / len(members), 4),
            "mean_recall_at_5": round(sum(row["recall_at_5"] for row in members) / len(members), 4),
        }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
