import unittest
from pathlib import Path

from mrt_ai.contracts.catalog import FixturePlaceCatalog
from mrt_ai.retrieval.pipeline import MrtAiRetrievalPipeline
from mrt_ai.retrieval.encoders.sbert import LocalSbertPlaceSearch

ROOT = Path(__file__).resolve().parent.parent


class MrtAiRetrievalPipelineTests(unittest.TestCase):
    def setUp(self):
        catalogue = FixturePlaceCatalog.model_validate_json(
            (ROOT / "data" / "fixtures" / "places.json").read_text(encoding="utf-8")
        )
        self.candidates = [
            candidate for candidate in catalogue.candidates
            if candidate.region_id == "ru:region:50"
        ]
        self.pipeline = MrtAiRetrievalPipeline(LocalSbertPlaceSearch(
            ROOT / "unused-model",
            encode_texts=lambda texts: [[1.0, 0.0] for _ in texts],
        ))

    def test_pipeline_uses_mrt_ai_bm25_baseline_by_default(self):
        result = self.pipeline.search(
            "прогулка по лесной тропе",
            self.candidates,
            3,
            "bm25",
        )
        self.assertEqual(result.ranking_version, "bm25-lexical-v1")
        self.assertTrue(result.results)
        self.assertIn("BM25", result.warning)

    def test_pipeline_exposes_external_encoder_as_embedding_strategy(self):
        result = self.pipeline.search(
            "спокойная поездка на природе",
            self.candidates,
            3,
            "embedding",
        )
        self.assertEqual(result.ranking_version, "sbert-large-nlu-ru-mean-v1")
        self.assertEqual(len(result.results), 3)
        self.assertIn("SBERT", result.warning)


if __name__ == "__main__":
    unittest.main()
