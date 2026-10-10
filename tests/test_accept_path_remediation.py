"""Unit tests for remediated accept path (no engineered clone rationales)."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

from src.scorer.schemas import QuestionEvaluation, is_engineered_rationale, is_scaffolding_citation


class TestAcceptPathRemediation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1] / "scripts" / "14_ai_copilot_extractor_v2.py"
        spec = importlib.util.spec_from_file_location("extractor_v2", path)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        cls.ext = mod

    def test_error_code_survives_schema_dump(self):
        rec = QuestionEvaluation(
            q_id="ES_Q1",
            predicted_val=None,
            confidence=0.0,
            citation=None,
            rationale=None,
            error_code="TIMEOUT",
        )
        dumped = rec.model_dump()
        self.assertEqual(dumped["error_code"], "TIMEOUT")
        self.assertIsNone(dumped["rationale"])

    def test_withhold_has_null_rationale_and_error_code(self):
        out = self.ext._withhold(
            "ES_Q1",
            [{"check": "citation_ungrounded", "detail": "x"}],
        )
        self.assertIsNone(out["predicted_val"])
        self.assertIsNone(out["rationale"])
        self.assertIsNone(out["citation"])
        self.assertEqual(out["error_code"], "WITHHELD_UNGROUNDED")
        self.assertFalse(is_engineered_rationale(out["rationale"]))

    def test_timeout_and_no_primary_passthrough(self):
        q = {"new_q_id": "ES_Q1", "cat_code": "ES", "text": "Impact?"}
        timeout = self.ext.accept_model_answer(
            {"q_id": "ES_Q1", "error_code": "TIMEOUT"},
            "primary text here",
            q,
        )
        self.assertEqual(timeout["error_code"], "TIMEOUT")
        self.assertIsNone(timeout["rationale"])

        missing = self.ext.accept_model_answer(
            {"q_id": "ES_Q1", "error_code": "NO_PRIMARY"},
            "",
            q,
        )
        self.assertEqual(missing["error_code"], "NO_PRIMARY")
        self.assertIsNone(missing["rationale"])

    def test_absence_high_score_rejected(self):
        primary = "Our team built a modular ammonia reactor for remote farms."
        q = {
            "new_q_id": "ES_Q1",
            "cat_code": "ES",
            "text": "Impact evidence?",
            "options": [{"val": 0.0}, {"val": 0.5}, {"val": 1.0}],
        }
        raw = {
            "q_id": "ES_Q1",
            "predicted_val": 0.75,
            "confidence": 0.8,
            "citation": "Our team built a modular ammonia reactor for remote farms.",
            "rationale": "The documents do not mention any impact metrics.",
        }
        out = self.ext.accept_model_answer(raw, primary, q, company="AcmeCo")
        self.assertIsNone(out["predicted_val"])
        self.assertEqual(out["error_code"], "WITHHELD_SCORE_ABSENCE_MISMATCH")

    def test_invented_figure_withholds_not_sanitize_clone(self):
        primary = "AcmeCo sells recycled graphite anodes to battery makers in Ohio."
        q = {
            "new_q_id": "ES_Q2",
            "cat_code": "ES",
            "text": "Describe impact",
            "options": [{"val": 0.0}, {"val": 0.25}, {"val": 0.5}, {"val": 0.75}, {"val": 1.0}],
        }
        raw = {
            "q_id": "ES_Q2",
            "predicted_val": 0.75,
            "confidence": 0.9,
            "citation": "AcmeCo sells recycled graphite anodes to battery makers in Ohio.",
            "rationale": "AcmeCo reduces emissions by 40% toward SDG 13.",
        }
        out = self.ext.accept_model_answer(raw, primary, q, company="AcmeCo")
        self.assertIsNone(out["predicted_val"])
        self.assertIsNone(out["rationale"])
        self.assertEqual(out["error_code"], "WITHHELD_UNSUPPORTED_CLAIM")
        self.assertNotIn("Score based on the cited primary text only", str(out))

    def test_generic_rationale_without_citation_token_rejected(self):
        primary = "ZetaPower ships solid-state cells to municipal buses."
        q = {
            "new_q_id": "PMF_Q1",
            "cat_code": "PMF",
            "text": "Customer evidence?",
            "options": [{"val": 0.0}, {"val": 0.5}, {"val": 1.0}],
        }
        raw = {
            "q_id": "PMF_Q1",
            "predicted_val": 0.5,
            "confidence": 0.7,
            "citation": "ZetaPower ships solid-state cells to municipal buses.",
            "rationale": "The startup demonstrates a strong approach overall.",
        }
        out = self.ext.accept_model_answer(raw, primary, q, company="OtherName")
        self.assertIsNone(out["predicted_val"])
        self.assertEqual(out["error_code"], "WITHHELD_UNSUPPORTED_CLAIM")

    def test_less_taxation_is_scaffolding(self):
        self.assertTrue(is_scaffolding_citation("less taxation 0 0 0"))

    def test_es_q1_narrative_impact_allowed_without_sdg_label(self):
        """Wave 2: grounded climate/impact narrative may score without literal SDG."""
        from scripts.audit_v5_parsed import audit_parsed_records

        primary = (
            "H2O Now builds modular water purification for drought-hit farms, "
            "cutting freshwater waste and improving community access to clean water."
        )
        cite = (
            "H2O Now builds modular water purification for drought-hit farms, "
            "cutting freshwater waste and improving community access to clean water."
        )
        record = {
            "q_id": "ES_Q1",
            "predicted_val": 1.0,
            "confidence": 0.8,
            "citation": cite,
            "rationale": (
                "H2O Now cites water purification for drought-hit farms and community "
                "access to clean water — two grounded impact themes without naming SDG numbers."
            ),
        }
        q = {
            "new_q_id": "ES_Q1",
            "cat_code": "ES",
            "text": (
                "Company purpose directly addresses two or more United Nations "
                "Sustainable Development Goals (SDGs)."
            ),
            "options": [{"val": 0.0}, {"val": 0.5}, {"val": 1.0}],
        }
        findings = audit_parsed_records([record], {"ES": primary}, [q])
        self.assertEqual(findings, [])

        out = self.ext.accept_model_answer(
            {
                "q_id": "ES_Q1",
                "predicted_val": 1.0,
                "confidence": 0.8,
                "citation": cite,
                "rationale": record["rationale"],
            },
            primary,
            q,
            company="H2O_Now",
        )
        self.assertEqual(out.get("predicted_val"), 1.0)
        self.assertIsNone(out.get("error_code"))

    def test_es_q1_invented_sdg_number_still_withheld(self):
        primary = "AcmeCo sells recycled graphite anodes to battery makers in Ohio."
        q = {
            "new_q_id": "ES_Q1",
            "cat_code": "ES",
            "text": (
                "Company purpose directly addresses two or more United Nations "
                "Sustainable Development Goals (SDGs)."
            ),
            "options": [{"val": 0.0}, {"val": 0.5}, {"val": 1.0}],
        }
        raw = {
            "q_id": "ES_Q1",
            "predicted_val": 1.0,
            "confidence": 0.9,
            "citation": "AcmeCo sells recycled graphite anodes to battery makers in Ohio.",
            "rationale": "AcmeCo advances SDG 7 and SDG 13 via recycled anodes.",
        }
        out = self.ext.accept_model_answer(raw, primary, q, company="AcmeCo")
        self.assertIsNone(out["predicted_val"])
        self.assertEqual(out["error_code"], "WITHHELD_UNSUPPORTED_CLAIM")


if __name__ == "__main__":
    unittest.main()
