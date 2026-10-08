"""Convert a completed blinded review sheet to evaluator relevance grades."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("review_sheet", type=Path)
    parser.add_argument("answer_key", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    sheet = json.loads(args.review_sheet.read_text(encoding="utf-8"))
    key = json.loads(args.answer_key.read_text(encoding="utf-8"))
    if sheet["review_id"] != key["review_id"] or sheet["source_dataset"] != key["source_dataset"]:
        raise ValueError("Review sheet and answer key do not match")

    cases = []
    if set(case["case_id"] for case in sheet["cases"]) != set(key["cases"]):
        raise ValueError("Review case IDs differ from answer key")
    for reviewed in sheet["cases"]:
        case_id = reviewed["case_id"]
        key_map = key["cases"][case_id]
        relevant = {}
        seen_keys = set()
        for candidate in reviewed["candidates"]:
            candidate_key = candidate["candidate_key"]
            if candidate_key not in key_map or candidate_key in seen_keys:
                raise ValueError(f"Unknown or duplicate candidate key in {case_id}: {candidate_key}")
            seen_keys.add(candidate_key)
            grade = candidate.get("rating_0_to_3")
            if type(grade) is not int or grade < 0 or grade > 3:
                raise ValueError(f"Complete rating_0_to_3 for {case_id}/{candidate_key} with an integer 0..3")
            if grade:
                relevant[key_map[candidate_key]] = grade
        if seen_keys != set(key_map):
            raise ValueError(f"Candidate list is incomplete in case {case_id}")
        cases.append({
            "id": case_id,
            "group": "human_review",
            "region_id": reviewed["region_id"],
            "trip": reviewed["trip_request"],
            "relevant": relevant,
        })

    output = {
        "dataset_id": sheet["review_id"],
        "split": "human_review",
        "data_mode": sheet["data_mode"],
        "purpose": "Human relevance judgments collected without model scores or ranking order.",
        "limitations": [
            "Candidates are synthetic fixtures, not real places or services.",
            "This file reflects one completed review sheet; combine independent raters before tuning weights.",
        ],
        "cases": cases,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Imported {len(cases)} reviewed cases to {args.output}")


if __name__ == "__main__":
    main()
