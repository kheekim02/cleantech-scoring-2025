# tests/test_layer2_policies.py
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_extractor():
    path = ROOT / "scripts" / "14_ai_copilot_extractor_v2.py"
    spec = importlib.util.spec_from_file_location("extractor_l2p", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def capture_system_prompt(ext, question):
    seen = {}

    def fake_chat(endpoint, model_id, messages, timeout, temperature=0.0):
        seen["system"] = messages[0]["content"]
        return {"q_id": question["q_id"], "predicted_val": 0.0, "confidence": 0.5,
                "citation": None, "rationale": "x"}

    ext._ollama_chat = fake_chat
    ext.query_sglang_question(None, "m", "ctx", question, 5, {"EBD2": ["impact.pdf.md"]},
                              True, "http://h:11434", startup_id="AcmeCo")
    return seen["system"]


ES_Q1 = {"q_id": "ES_Q1", "new_q_id": "ES_Q1", "cat_code": "ES", "text": "SDG alignment?",
         "options": [{"val": 0.0}, {"val": 0.5}, {"val": 1.0}]}
BC_Q1 = {"q_id": "BC_Q1", "new_q_id": "BC_Q1", "cat_code": "BC", "text": "Value prop?",
         "options": [{"val": 0.0}, {"val": 1.0}]}
GOLDEN = ROOT / "tests" / "fixtures" / "l2_system_prompts.json"


class TestPromptCharacterization(unittest.TestCase):
    def test_system_prompts_unchanged(self):
        import json
        ext = load_extractor()
        current = {q["q_id"]: capture_system_prompt(ext, q) for q in (ES_Q1, BC_Q1)}
        if not GOLDEN.exists():
            GOLDEN.parent.mkdir(parents=True, exist_ok=True)
            GOLDEN.write_text(json.dumps(current, indent=2), encoding="utf-8")
        self.assertEqual(current, json.loads(GOLDEN.read_text(encoding="utf-8")))


class TestPolicies(unittest.TestCase):
    def test_build_system_prompt_uses_policy_file(self):
        ext = load_extractor()
        policies = ext.load_policies()
        self.assertIn("ES_Q1", policies["question"])
        prompt = ext.build_system_prompt(ES_Q1, {"EBD2": ["impact.pdf.md"]}, policies)
        self.assertIn("For ES_Q1 specifically", prompt)
        self.assertNotIn("For ES_Q1 specifically", ext.build_system_prompt(BC_Q1, {}, policies))


if __name__ == "__main__":
    unittest.main()
