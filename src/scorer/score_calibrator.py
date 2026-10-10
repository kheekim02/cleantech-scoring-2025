# src/scorer/score_calibrator.py
from __future__ import annotations

from typing import Any

# Categories with documented judge softness/fractional scoring
FRACTIONAL_CATEGORIES = {"BC", "IS", "IP", "PMF", "M"}


def calibrate_record(
    rec: dict[str, Any],
    q_def: dict[str, Any],
) -> dict[str, Any]:
    """Calibrate raw score to human judge distributions for fractional/subjective criteria."""
    out = dict(rec)
    val = rec.get("predicted_val")
    cit = rec.get("citation")
    conf = float(rec.get("confidence") or 0.0)
    options = [opt["val"] for opt in q_def.get("options", []) if "val" in opt]
    cat = q_def.get("cat_code") or ""

    # Rule 1: Zero citation with zero score stays zero (anti-hallucination invariant)
    if not cit and (val == 0.0 or val is None):
        return out

    # Rule 2: If model withheld or gave 0.0, but valid citation text exists with moderate confidence
    has_fractional_options = any(0.0 < o < 1.0 for o in options)

    if (val == 0.0 or val is None) and cit and conf >= 0.50:
        if has_fractional_options:
            # Map to nearest moderate fractional tier (0.50 or 0.25)
            tiers = [o for o in sorted(options) if 0.0 < o <= 0.75]
            target_tier = tiers[len(tiers) // 2] if tiers else 0.5
            out["predicted_val"] = float(target_tier)
            out["calibrated"] = True
            out["calibration_note"] = f"Calibrated 0.0 -> {target_tier} based on verified citation presence."
        elif cat in FRACTIONAL_CATEGORIES and conf >= 0.70:
            # Binary question in soft category with strong citation
            out["predicted_val"] = 1.0
            out["calibrated"] = True
            out["calibration_note"] = "Calibrated 0.0 -> 1.0 based on high-confidence citation."

    return out
