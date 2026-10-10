# tests/test_apply_deterministic_overrides.py
import json
import tempfile
import unittest
from pathlib import Path

from scripts.apply_deterministic_overrides import apply_deterministic_updates


class TestApplyDeterministicOverrides(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.src_cache = self.root / "src_cache"
        self.dst_cache = self.root / "dst_cache"
        self.parsed_dir = self.root / "parsed"
        self.src_cache.mkdir()
        self.parsed_dir.mkdir()

        # Mock startup allowlist
        self.allowlist_path = self.root / "allowlist.json"
        self.allowlist_path.write_text(json.dumps({
            "count": 1,
            "startups": [{"startup_id": "AcmeCo"}]
        }))

        # Mock rubric
        self.rubric_path = self.root / "rubric.json"
        self.rubric_path.write_text(json.dumps([
            {"q_id": "F_Q1", "cat_code": "F", "text": "3 year projections", "options": [{"val": 0.0}, {"val": 1.0}]},
            {"q_id": "F_Q2", "cat_code": "F", "text": "Unit economics", "options": [{"val": 0.0}, {"val": 1.0}]},
            {"q_id": "L_Q1", "cat_code": "L", "text": "Corporate entity", "options": [{"val": 0.0}, {"val": 1.0}]},
        ]))

        # Mock source cache
        (self.src_cache / "AcmeCo.json").write_text(json.dumps([
            {"q_id": "F_Q1", "predicted_val": 0.0, "confidence": 0.5, "citation": None, "rationale": "Old model"},
            {"q_id": "F_Q2", "predicted_val": 1.0, "confidence": 0.8, "citation": "unit cite", "rationale": "Kept"},
            {"q_id": "L_Q1", "predicted_val": 0.0, "confidence": 0.5, "citation": None, "rationale": "Old model"},
        ]))

        # Mock parsed directory for AcmeCo
        co_dir = self.parsed_dir / "AcmeCo"
        co_dir.mkdir()
        # EBD5 file with 3-year projection
        (co_dir / "01_Financial_Projections.pdf.md").write_text(
            "Financial Projections\nYear 1 revenue $100K | Year 2 revenue $300K | Year 3 revenue $900K\nAppendix"
        )
        # Legal file with Delaware C-corp
        (co_dir / "02_Legal_M7.pdf.md").write_text(
            "Formation\nAcmeCo is incorporated in Delaware as a Delaware C-Corp in 2024.\nStockholders"
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_apply_deterministic_updates(self):
        stats = apply_deterministic_updates(
            src_cache_dir=self.src_cache,
            dst_cache_dir=self.dst_cache,
            parsed_dir=self.parsed_dir,
            allowlist_path=self.allowlist_path,
            rubric_path=self.rubric_path,
        )

        self.assertEqual(stats["startups_processed"], 1)
        self.assertEqual(stats["total_overrides"], 2)
        self.assertEqual(stats["overrides_by_qid"]["F_Q1"], 1)
        self.assertEqual(stats["overrides_by_qid"]["L_Q1"], 1)

        # Check destination cache
        dst_file = self.dst_cache / "AcmeCo.json"
        self.assertTrue(dst_file.exists())
        records = json.loads(dst_file.read_text())
        by_qid = {r["q_id"]: r for r in records}

        # F_Q1 should be overridden to 1.0 with deterministic source
        self.assertEqual(by_qid["F_Q1"]["predicted_val"], 1.0)
        self.assertEqual(by_qid["F_Q1"]["source"], "deterministic")
        self.assertIn("Year 1 revenue", by_qid["F_Q1"]["citation"])

        # F_Q2 should be unchanged
        self.assertEqual(by_qid["F_Q2"]["predicted_val"], 1.0)
        self.assertEqual(by_qid["F_Q2"]["rationale"], "Kept")
        self.assertNotIn("source", by_qid["F_Q2"])

        # L_Q1 should be overridden to 1.0 with deterministic source
        self.assertEqual(by_qid["L_Q1"]["predicted_val"], 1.0)
        self.assertEqual(by_qid["L_Q1"]["source"], "deterministic")
        self.assertIn("Delaware C-Corp", by_qid["L_Q1"]["citation"])


if __name__ == "__main__":
    unittest.main()
