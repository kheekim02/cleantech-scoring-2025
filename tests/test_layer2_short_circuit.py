# tests/test_layer2_short_circuit.py
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_extractor():
    path = ROOT / "scripts" / "14_ai_copilot_extractor_v2.py"
    spec = importlib.util.spec_from_file_location("extractor_l2", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


F_Q7 = {"q_id": "F_Q7", "new_q_id": "F_Q7", "cat_code": "F",
        "text": "Does the model show a breakeven point?",
        "options": [{"val": 0.0}, {"val": 1.0}]}
PRIMARY = "Financial Summary\nWe reach breakeven in Year 3 with $150K net profit.\nAppendix"


class FakeQuery:
    def __init__(self, response):
        self.calls = 0
        self.response = response

    def __call__(self, *args, **kwargs):
        self.calls += 1
        return dict(self.response)


class TestShortCircuit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ext = load_extractor()

    def _score(self, q, primary, fake):
        ctx = {"text": primary, "primary_text": primary, "has_primary": True}
        return self.ext.score_question(
            q, ctx, query_fn=fake, client=None, model_id="m", timeout=5,
            doc_manifest={}, endpoint="http://x:30000", startup_id="AcmeCo",
        )

    def test_deterministic_hit_skips_llm_and_is_grounded(self):
        fake = FakeQuery({"q_id": "F_Q7", "predicted_val": 0.0, "confidence": 0.5,
                          "citation": None, "rationale": "x"})
        rec = self._score(F_Q7, PRIMARY, fake)
        self.assertEqual(fake.calls, 0)
        self.assertEqual(rec["predicted_val"], 1.0)
        self.assertEqual(rec["source"], "deterministic")
        self.assertIn(rec["citation"], PRIMARY)
        self.assertIsNone(rec["error_code"])

    def test_regex_miss_falls_through_to_llm_not_zero(self):
        fake = FakeQuery({"q_id": "F_Q7", "predicted_val": 0.0, "confidence": 0.6,
                          "citation": None, "rationale": "AcmeCo provides no breakeven analysis."})
        rec = self._score(F_Q7, "Financial Summary\nRevenue grows.\n", fake)
        self.assertEqual(fake.calls, 1)
        self.assertNotEqual(rec.get("source"), "deterministic")

    def test_unruled_question_always_calls_llm(self):
        q = {"q_id": "BC_Q1", "new_q_id": "BC_Q1", "cat_code": "BC", "text": "Value prop?",
             "options": [{"val": 0.0}, {"val": 1.0}]}
        fake = FakeQuery({"q_id": "BC_Q1", "predicted_val": 0.0, "confidence": 0.5,
                          "citation": None, "rationale": "AcmeCo lists no value proposition."})
        self._score(q, PRIMARY, fake)
        self.assertEqual(fake.calls, 1)


if __name__ == "__main__":
    unittest.main()
