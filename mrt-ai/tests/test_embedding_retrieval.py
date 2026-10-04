import unittest
from pathlib import Path

from mrt_ai.contracts.catalog import FixturePlaceCatalog
from mrt_ai.retrieval.encoders.sbert import LocalSbertPlaceSearch
from scripts.evaluate_retrieval import evaluate

ROOT = Path(__file__).resolve().parent.parent


class EmbeddingRetrievalTests(unittest.TestCase):
    def setUp(self):
        catalogue = FixturePlaceCatalog.model_validate_json(
            (ROOT / "data" / "fixtures" / "places.json").read_text(encoding="utf-8")
        )
        self.target = catalogue.candidates[0].model_copy(update={"name": "target"})
        self.other = catalogue.candidates[1].model_copy(update={"name": "other"})
        self.encoded_texts = []

        def encoder(texts):
            self.encoded_texts.extend(texts)
            return [[1.0, 0.0] if "target" in text else [0.0, 1.0] for text in texts]

        self.searcher = LocalSbertPlaceSearch(ROOT / "missing-model", encode_texts=encoder)

    def test_embedding_ranking_is_deterministic_and_caches_candidate_vectors(self):
        first = self.searcher.search("target", [self.other, self.target], top_k=2)
        second = self.searcher.search("target", [self.other, self.target], top_k=2)
        self.assertEqual(
            [hit.candidate.object_id for hit in first],
            [self.target.object_id, self.other.object_id],
        )
        self.assertEqual(first, second)
        self.assertEqual(first[0].score, 1.0)
        self.assertEqual(first[0].matched_terms, [])
        self.assertEqual(len(self.encoded_texts), 4)

    def test_evaluator_reports_embedding_metrics_and_model_identity(self):
        result = evaluate(
            top_k=5,
            ranking_method="embedding",
            embedding_searcher=LocalSbertPlaceSearch(
                ROOT / "missing-model",
                encode_texts=lambda texts: [[1.0, 0.0] for _ in texts],
            ),
        )
        self.assertEqual(result["ranking_version"], "sbert-large-nlu-ru-mean-v1")
        self.assertEqual(result["query_count"], 8)
        self.assertIn("query_latency_ms", result)
        self.assertEqual(result["model"]["id"], "ai-forever/sbert_large_nlu_ru")

    def test_embedding_search_rejects_inconsistent_vector_dimensions(self):
        searcher = LocalSbertPlaceSearch(
            ROOT / "missing-model",
            encode_texts=lambda texts: [[1.0] if "target" in text else [1.0, 0.0] for text in texts],
        )
        with self.assertRaisesRegex(ValueError, "inconsistent vector dimensions"):
            searcher.search("target", [self.target, self.other], top_k=2)

    def test_candidate_vector_cache_has_a_fixed_limit(self):
        for index in range(9):
            candidate = self.target.model_copy(update={"object_id": f"test:{index}"})
            self.searcher.search("target", [candidate], top_k=1)
        self.assertEqual(len(self.searcher._candidate_vectors), 8)


if __name__ == "__main__":
    unittest.main()
