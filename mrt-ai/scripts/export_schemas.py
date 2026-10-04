import json
from pathlib import Path

from app.contracts import Edit, ParseRequest, RecommendRequest, SelectRegion, SessionCreate, SessionState, TripRequest, Turn
from mrt_ai.contracts.catalog import Candidate, CandidateBatch, CandidateQuery, Catalog, FixturePlaceCatalog, Offer, PlaceSearchHit, PlaceSearchRequest, PlaceSearchResponse, Price, RegionRecommendations


def main():
    root = Path(__file__).resolve().parent.parent / "schemas"
    root.mkdir(exist_ok=True)
    models = (TripRequest, SessionState, SessionCreate, Turn, Edit, ParseRequest, RecommendRequest, SelectRegion,
              Catalog, RegionRecommendations, Candidate, FixturePlaceCatalog, Offer, Price, CandidateQuery, CandidateBatch,
              PlaceSearchRequest, PlaceSearchHit, PlaceSearchResponse)
    for model in models:
        schema = model.model_json_schema()
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        (root / f"{model.__name__}.json").write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Exported {len(models)} schemas to schemas/")


if __name__ == "__main__":
    main()
