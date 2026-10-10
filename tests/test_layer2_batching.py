# tests/test_layer2_batching.py
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_extractor():
    path = ROOT / "scripts" / "14_ai_copilot_extractor_v2.py"
    spec = importlib.util.spec_from_file_location("extractor_l2b", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def q(qid, cat):
    return {"q_id": qid, "new_q_id": qid, "cat_code": cat, "text": qid, "options": [{"val": 0.0}, {"val": 1.0}]}


class TestBatching(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ext = load_extractor()

    def test_groups_never_mix_categories(self):
        qs = [q("BC_Q1", "BC"), q("BC_Q2", "BC"), q("ES_Q1", "ES"), q("BC_Q3", "BC")]
        groups = self.ext.group_questions(qs, 2)
        for g in groups:
            self.assertEqual(len({x["cat_code"] for x in g}), 1)
            self.assertLessEqual(len(g), 2)
        self.assertEqual(sorted(x["q_id"] for g in groups for x in g), sorted(x["q_id"] for x in qs))

    def test_batch_size_one_is_identity(self):
        qs = [q("BC_Q1", "BC"), q("ES_Q1", "ES")]
        self.assertEqual(self.ext.group_questions(qs, 1), [[qs[0]], [qs[1]]])

    def test_split_maps_by_qid_not_position(self):
        group = [q("BC_Q1", "BC"), q("BC_Q2", "BC")]
        raw = [{"q_id": "BC_Q2", "predicted_val": 1.0, "citation": "b"},
               {"q_id": "BC_Q1", "predicted_val": 0.0, "citation": None}]
        out = self.ext.split_batched_response(raw, group)
        self.assertEqual([r["q_id"] for r in out], ["BC_Q1", "BC_Q2"])
        self.assertEqual(out[1]["citation"], "b")

    def test_split_withholds_missing_and_duplicate(self):
        group = [q("BC_Q1", "BC"), q("BC_Q2", "BC")]
        raw = [{"q_id": "BC_Q1", "predicted_val": 1.0, "citation": "a"},
               {"q_id": "BC_Q1", "predicted_val": 0.0, "citation": None},
               {"q_id": "ZZ_Q9", "predicted_val": 1.0, "citation": "z"}]
        out = self.ext.split_batched_response(raw, group)
        self.assertEqual(out[0]["error_code"], "TIMEOUT")
        self.assertEqual(out[1]["error_code"], "TIMEOUT")


if __name__ == "__main__":
    unittest.main()
