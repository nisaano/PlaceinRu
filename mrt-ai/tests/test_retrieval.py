import unittest

from scripts.evaluate_retrieval import evaluate


class RetrievalEvaluationTests(unittest.TestCase):
    def test_bm25_baseline_is_reproducible_and_has_expected_quality_floor(self):
        first = evaluate(top_k=5)
        second = evaluate(top_k=5)
        self.assertEqual(first, second)
        self.assertEqual(first["ranking_version"], "bm25-lexical-v1")
        self.assertEqual(first["query_count"], 8)
        self.assertGreaterEqual(first["mean_ndcg_at_k"], 0.70)
        self.assertGreaterEqual(first["mean_recall_at_k"], 0.75)
        self.assertTrue(all(row["top_ids"] for row in first["per_query"]))


if __name__ == "__main__":
    unittest.main()
