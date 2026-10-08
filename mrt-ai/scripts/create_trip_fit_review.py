"""Create an anonymized relevance-review sheet from a TripRequest dataset."""
import argparse
import json
import random
from pathlib import Path

from app.catalog_import import ROOT
from mrt_ai.contracts.catalog import FixturePlaceCatalog


DEFAULT_DATASET = ROOT / "data/fixtures/trip-fit-holdout-v1.json"
DEFAULT_OUTPUT = ROOT / "artifacts/trip-fit-review-v1.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--seed", type=int, default=None,
                        help="Optional seed for reproducible candidate shuffling")
    args = parser.parse_args()

    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    catalog = FixturePlaceCatalog.model_validate_json(
        (ROOT / "data/fixtures/places.json").read_text(encoding="utf-8")
    )
    rng = random.Random(args.seed)
    review_cases = []
    answer_cases = {}
    for case in dataset["cases"]:
        candidates = [candidate for candidate in catalog.candidates if candidate.region_id == case["region_id"]]
        rng.shuffle(candidates)
        answer_map = {}
        review_candidates = []
        for index, candidate in enumerate(candidates):
            key = f"C{index + 1:02d}"
            answer_map[key] = candidate.object_id
            review_candidates.append({
                "candidate_key": key,
                "kind": candidate.kind,
                "name": candidate.name,
                "description": candidate.description,
                "tags": candidate.tags,
                "rating_0_to_3": None,
                "notes": "",
            })
        answer_cases[case["id"]] = answer_map
        review_cases.append({
            "case_id": case["id"],
            "region_id": case["region_id"],
            "trip_request": case["trip"],
            "candidates": review_candidates,
        })

    sheet = {
        "review_id": "trip-fit-human-review-v1",
        "source_dataset": dataset["dataset_id"],
        "data_mode": "fixture",
        "instructions": (
            "Оценивайте соответствие карточки запросу, не сравнивая её с другими карточками. "
            "0 — не подходит; 1 — слабо подходит; 2 — хорошо подходит; 3 — очень хорошо подходит. "
            "Неизвестные из карточки факты (цена, наличие, реальность места) не предполагайте. "
            "Все места синтетические и вымышленные. Заполняйте rating_0_to_3 и при необходимости notes."
        ),
        "cases": review_cases,
    }
    answer_key = {
        "review_id": sheet["review_id"],
        "source_dataset": dataset["dataset_id"],
        "cases": answer_cases,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(sheet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    key_path = args.output.with_name(args.output.stem + ".answer-key.json")
    key_path.write_text(json.dumps(answer_key, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Review sheet: {args.output}")
    print(f"Keep this answer key private from reviewers: {key_path}")
    print(f"Cases: {len(review_cases)}; cards per case: "
          + ", ".join(str(len(case["candidates"])) for case in review_cases))


if __name__ == "__main__":
    main()
