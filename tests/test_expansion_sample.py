"""Reproducible five-company expansion sample for phase 4."""
import json
import random
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST = ROOT / "data" / "active_startup_allowlist.json"
SAMPLE_SEED = 2026
EXPECTED_SAMPLE = [
    "CarbonDots",
    "Cero_Global_Holdings",
    "Hubbletek",
    "SOLARSYSTEMS",
    "SPCTA_Industrial",
]


def pick_expansion_sample(startup_ids: list[str], seed: int = SAMPLE_SEED) -> list[str]:
    """Keep CarbonDots and add four peers from a fixed seed."""
    ids = list(startup_ids)
    if "CarbonDots" not in ids:
        raise ValueError("CarbonDots must be on the allowlist for the expansion sample")
    others = [s for s in ids if s != "CarbonDots"]
    return ["CarbonDots"] + random.Random(seed).sample(others, 4)


class TestExpansionSample(unittest.TestCase):
    def test_sample_is_five_allowlisted_companies(self):
        payload = json.loads(ALLOWLIST.read_text())
        ids = [row["startup_id"] for row in payload["startups"]]
        self.assertEqual(len(ids), 92)
        sample = pick_expansion_sample(ids)
        self.assertEqual(sample, EXPECTED_SAMPLE)
        self.assertEqual(len(sample), 5)
        self.assertEqual(len(set(sample)), 5)
        for startup_id in sample:
            self.assertIn(startup_id, ids)


if __name__ == "__main__":
    unittest.main()
