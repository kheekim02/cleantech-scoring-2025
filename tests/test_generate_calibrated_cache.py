# tests/test_generate_calibrated_cache.py
import unittest
import json
import tempfile
from pathlib import Path
from scripts.generate_calibrated_cache import generate_calibrated_cache


class TestGenerateCalibratedCache(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.src_cache = self.root / "src_cache"
        self.dst_cache = self.root / "dst_cache"
        self.raw_dir = self.root / "raw"
        self.src_cache.mkdir()
        self.dst_cache.mkdir()
        self.raw_dir.mkdir()

        self.allowlist_path = self.root / "allowlist.json"
        self.allowlist_path.write_text(json.dumps({
            "count": 1,
            "startups": [{"startup_id": "TestCo"}]
        }))

        self.rubric_path = self.root / "rubric.json"
        self.rubric_path.write_text(json.dumps([
            {"q_id": "BC_Q1", "cat_code": "BC", "options": [{"val": 0.0}, {"val": 0.5}, {"val": 1.0}]},
            {"q_id": "IP_Q7", "cat_code": "IP", "options": [{"val": 0.0}, {"val": 1.0}]},
        ]))

        (self.src_cache / "TestCo.json").write_text(json.dumps([
            {"q_id": "BC_Q1", "predicted_val": 0.0, "confidence": 0.7, "citation": "Customer segments include municipal transit authorities.", "rationale": "Applicant explicitly mentions municipal transit authorities as primary target customer segment."},
            {"q_id": "IP_Q7", "predicted_val": 0.0, "confidence": 0.5, "citation": None, "rationale": "No visual problem diagram found in pitch deck slides."},
        ]))

    def tearDown(self):
        self.tmp.cleanup()

    def test_generate_calibrated_cache(self):
        stats = generate_calibrated_cache(
            src_cache_dir=self.src_cache,
            dst_cache_dir=self.dst_cache,
            raw_dir=self.raw_dir,
            allowlist_path=self.allowlist_path,
            rubric_path=self.rubric_path,
            calibrate_fractional=True,
        )
        self.assertEqual(stats["startups_processed"], 1)
        self.assertGreater(stats["calibrated_count"], 0)

        out_file = self.dst_cache / "TestCo.json"
        self.assertTrue(out_file.exists())
        records = json.loads(out_file.read_text())
        by_qid = {r["q_id"]: r for r in records}
        self.assertEqual(by_qid["BC_Q1"]["predicted_val"], 0.5)


if __name__ == "__main__":
    unittest.main()
