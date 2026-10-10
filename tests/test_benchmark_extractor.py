# tests/test_benchmark_extractor.py
import json
import tempfile
import unittest
from pathlib import Path

from scripts.benchmark_extractor import compare_cache_to_human


class TestBenchmarkExtractor(unittest.TestCase):
    def test_compare_counts_pairs_and_withholds(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            (cache / "A.json").write_text(json.dumps([
                {"q_id": "BC_Q1", "predicted_val": 1.0, "citation": "x"},
                {"q_id": "BC_Q2", "predicted_val": None, "citation": None, "error_code": "WITHHELD_UNGROUNDED"},
                {"q_id": "BC_Q3", "predicted_val": 0.0, "citation": None},
            ]))
            human = [
                {"startup_id": "A", "question_id": "BC_Q1", "score": 1.0},
                {"startup_id": "A", "question_id": "BC_Q2", "score": 1.0},
                {"startup_id": "A", "question_id": "BC_Q3", "score": 0.5},
            ]
            m = compare_cache_to_human(cache, human, ["A"])
        self.assertEqual(m["n_pairs"], 2)
        self.assertAlmostEqual(m["exact_match"], 0.5)
        self.assertAlmostEqual(m["mae"], 0.25)
        self.assertAlmostEqual(m["withheld_rate"], 1 / 3)
        self.assertAlmostEqual(m["cited_rate"], 1 / 3)


if __name__ == "__main__":
    unittest.main()
