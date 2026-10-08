# Blind review trip-fit

This review flow collects relevance judgments without exposing the ranker's scores or order. It currently uses synthetic fixtures, so it can review the scoring logic but cannot validate real-world place quality.

Generate a randomized review sheet from the holdout query set:

```powershell
.\venv\Scripts\python.exe -B -m scripts.create_trip_fit_review --seed 20261006
```

The worksheet is written to `artifacts/trip-fit-review-v1.json`; a separate `artifacts/trip-fit-review-v1.answer-key.json` maps opaque candidate keys to fixture IDs. Give reviewers only the worksheet. Ask them to fill every `rating_0_to_3`: 0 means not relevant, 1 weak, 2 good, 3 very good. Leave the candidate order intact and do not show model scores or existing relevance labels.

After collecting a completed sheet, import it with:

```powershell
.\venv\Scripts\python.exe -B -m scripts.import_trip_fit_review artifacts/trip-fit-review-v1.json artifacts/trip-fit-review-v1.answer-key.json --output artifacts/trip-fit-human-review-v1.json
.\venv\Scripts\python.exe -B -m scripts.evaluate_trip_fit --dataset artifacts/trip-fit-human-review-v1.json
```

Keep the answer key separate from the reviewer. The importer rejects missing, duplicate, out-of-range, or mismatched grades. Do not tune weights from a single rater; compare independent reviewers first. Human judgments on these fictional cards remain engineering feedback, not evidence about real travel recommendations.
