"""Unit tests for Wave 3 promote gate (no network, temp dirs)."""
from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path


def load_mod():
    path = Path(__file__).resolve().parents[1] / "scripts" / "promote_cache_gate.py"
    spec = importlib.util.spec_from_file_location("promote_cache_gate", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class TestPromoteCacheGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_mod()

    def test_count_symlink_maps(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real = root / "A.primary_map.json"
            real.write_text(json.dumps({"ES": "text"}))
            link = root / "B.primary_map.json"
            os.symlink(real.name, link)
            bad = self.mod.count_symlink_maps(root)
            self.assertEqual(bad, ["B.primary_map.json"])

    def test_gates_green_requires_all(self):
        ok_i = {"status": "GREEN", "symlink_primary_maps": []}
        ok_n = {"cohort_status": "GREEN", "hard_count": 0}
        ok_g = {"status": "PASS"}
        self.assertTrue(self.mod.gates_green(ok_i, ok_n, ok_g))
        self.assertFalse(
            self.mod.gates_green({**ok_i, "symlink_primary_maps": ["x"]}, ok_n, ok_g)
        )
        self.assertFalse(self.mod.gates_green(ok_i, {**ok_n, "hard_count": 1}, ok_g))
        self.assertFalse(self.mod.gates_green(ok_i, ok_n, {"status": "FAIL"}))

    def test_atomic_promote_refuses_symlink_maps(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cand = root / "candidate"
            live = root / "live"
            cand.mkdir()
            live.mkdir()
            (cand / "A.json").write_text("[]")
            link = cand / "A.primary_map.json"
            target = root / "real_map.json"
            target.write_text(json.dumps({"ES": "x"}))
            os.symlink(target, link)
            with self.assertRaises(RuntimeError):
                self.mod.atomic_promote(cand, live, root)

    def test_allow_supabase_flag_exits_refused(self):
        import subprocess
        import sys

        script = Path(__file__).resolve().parents[1] / "scripts" / "promote_cache_gate.py"
        proc = subprocess.run(
            [sys.executable, str(script), "--allow-supabase", "--check-only"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("Supabase push refused", proc.stdout)


if __name__ == "__main__":
    unittest.main()
