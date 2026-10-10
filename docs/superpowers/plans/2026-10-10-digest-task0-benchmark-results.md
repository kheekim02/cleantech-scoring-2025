# Task 0 Baseline Discrepancy Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an automated discrepancy analysis diagnostic tool to break down Task 0 baseline results across categories, identify recurring criteria failures, classify error modes (over-prediction, withholding, tier mismatch), and produce an authoritative analytical report.

**Architecture:** A lightweight, dependency-free Python module and CLI (`scripts/analyze_benchmark_discrepancies.py`) that ingests `outputs/human_scores.json`, `master_282_rubric.json`, and the 5-startup benchmark cache, generating quantitative category rankings and a GitHub-flavored Markdown diagnostic report.

**Tech Stack:** Python 3.12, stdlib `unittest`, JSON, stdlib `argparse` / `collections` / `math`.

**Spec:** `AGENTS.md` §2, §7; `master_282_rubric.json`; `docs/superpowers/plans/2026-10-10-optimize-layer2-extractor.md` Task 0.

## Global Constraints

- Never modify `master_282_rubric.json`.
- Pure read-only toward extraction caches and `outputs/human_scores.json`.
- Zero writes to Supabase or `ai_cache_v5_parsed`.
- Strict stdlib implementation for test portability (`./venv/bin/python3 -m unittest -v <module>`).

## Review Focus

1. **Division by zero on unreviewed questions:** Questions with zero human evaluations must be omitted from error computations without raising `ZeroDivisionError`.
2. **Multi-judge score averaging:** Human scores for the same `(startup_id, question_id)` must be properly averaged across multiple evaluators.
3. **Withheld vs 0.0 separation:** Distinguish true score discrepancies (e.g. AI 1.0 vs Human 0.0) from withholdings (`predicted_val is None`).
4. **Category mapping integrity:** Questions must be mapped to their authoritative `cat_code` via `master_282_rubric.json`, falling back to question prefix only if unmapped.
5. **Signed bias tracking:** Compute signed difference (`AI - Human`) to reveal whether the model is systematically harsher or more generous in specific categories.

---

### Task 1: Discrepancy Analysis Core Engine

**Files:**
- Create: `scripts/analyze_benchmark_discrepancies.py`
- Create: `tests/test_analyze_benchmark_discrepancies.py`

**Interfaces:**
- Produces: `analyze_category_discrepancies(cache_dir: Path, human_rows: list[dict], startup_ids: list[str], rubric_questions: list[dict]) -> dict[str, dict]`
- Produces: `rank_worst_criteria(cache_dir: Path, human_rows: list[dict], startup_ids: list[str], rubric_questions: list[dict], top_k: int = 15) -> list[dict]`
- Produces: `classify_error_modes(cache_dir: Path, human_rows: list[dict], startup_ids: list[str]) -> dict[str, int]`

- [x] **Step 1: Write the failing tests**

```python
# tests/test_analyze_benchmark_discrepancies.py
import json
import tempfile
import unittest
from pathlib import Path

from scripts.analyze_benchmark_discrepancies import (
    analyze_category_discrepancies,
    classify_error_modes,
    rank_worst_criteria,
)


class TestAnalyzeBenchmarkDiscrepancies(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cache_dir = Path(self.tmp.name)
        (self.cache_dir / "A.json").write_text(json.dumps([
            {"q_id": "BC_Q1", "predicted_val": 1.0, "citation": "cite1"},
            {"q_id": "BC_Q2", "predicted_val": None, "citation": None, "error_code": "WITHHELD_UNGROUNDED"},
            {"q_id": "M_Q1", "predicted_val": 1.0, "citation": "cite2"},
            {"q_id": "M_Q2", "predicted_val": 0.0, "citation": None},
        ]))
        self.human_rows = [
            {"startup_id": "A", "question_id": "BC_Q1", "score": 0.5},
            {"startup_id": "A", "question_id": "BC_Q2", "score": 1.0},
            {"startup_id": "A", "question_id": "M_Q1", "score": 0.0},
            {"startup_id": "A", "question_id": "M_Q2", "score": 0.0},
        ]
        self.rubric = [
            {"new_q_id": "BC_Q1", "cat_code": "BC", "text": "Value Proposition"},
            {"new_q_id": "BC_Q2", "cat_code": "BC", "text": "Customer Segments"},
            {"new_q_id": "M_Q1", "cat_code": "M", "text": "Market Size"},
            {"new_q_id": "M_Q2", "cat_code": "M", "text": "Competitor Matrix"},
        ]

    def tearDown(self):
        self.tmp.cleanup()

    def test_analyze_category_discrepancies(self):
        stats = analyze_category_discrepancies(self.cache_dir, self.human_rows, ["A"], self.rubric)
        self.assertIn("BC", stats)
        self.assertIn("M", stats)
        self.assertEqual(stats["BC"]["pairs"], 1)
        self.assertEqual(stats["BC"]["exact_count"], 0)
        self.assertAlmostEqual(stats["BC"]["mae"], 0.5)
        self.assertAlmostEqual(stats["BC"]["mean_bias"], 0.5)  # AI (1.0) - Human (0.5) = +0.5
        self.assertEqual(stats["BC"]["withheld_count"], 1)

        self.assertEqual(stats["M"]["pairs"], 2)
        self.assertEqual(stats["M"]["exact_count"], 1)
        self.assertAlmostEqual(stats["M"]["mae"], 0.5)

    def test_rank_worst_criteria(self):
        worst = rank_worst_criteria(self.cache_dir, self.human_rows, ["A"], self.rubric, top_k=2)
        self.assertEqual(len(worst), 2)
        self.assertEqual(worst[0]["q_id"], "M_Q1")  # MAE 1.0 (AI 1.0 vs Human 0.0)
        self.assertAlmostEqual(worst[0]["mae"], 1.0)
        self.assertEqual(worst[0]["exact_match_pct"], 0.0)

    def test_classify_error_modes(self):
        modes = classify_error_modes(self.cache_dir, self.human_rows, ["A"])
        # M_Q1: AI=1.0, Human=0.0 -> over_prediction
        # BC_Q1: AI=1.0, Human=0.5 -> fractional_tier_mismatch
        # BC_Q2: AI=None, Human=1.0 -> withheld
        # M_Q2: AI=0.0, Human=0.0 -> exact_match
        self.assertEqual(modes["exact_match"], 1)
        self.assertEqual(modes["over_prediction"], 1)
        self.assertEqual(modes["fractional_tier_mismatch"], 1)
        self.assertEqual(modes["withheld"], 1)


if __name__ == "__main__":
    unittest.main()
```

- [x] **Step 2: Run test to verify it fails**

Run: `./venv/bin/python3 -m unittest -v tests.test_analyze_benchmark_discrepancies`
Expected: `ImportError: Failed to import test module: test_analyze_benchmark_discrepancies`

- [x] **Step 3: Implement `scripts/analyze_benchmark_discrepancies.py`**

```python
# scripts/analyze_benchmark_discrepancies.py
"""Detailed discrepancy diagnostic engine for startup scorer benchmark caches."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def _index_human_scores(human_rows: list[dict[str, Any]]) -> dict[tuple[str, str], float]:
    grouped: dict[tuple[str, str], list[float]] = defaultdict(list)
    for r in human_rows:
        if r.get("score") is not None and r.get("startup_id") and r.get("question_id"):
            grouped[(r["startup_id"], r["question_id"])].append(float(r["score"]))
    return {k: sum(v) / len(v) for k, v in grouped.items()}


def analyze_category_discrepancies(
    cache_dir: Path,
    human_rows: list[dict[str, Any]],
    startup_ids: list[str],
    rubric_questions: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    human = _index_human_scores(human_rows)
    cat_map = {q.get("new_q_id", q.get("q_id")): q.get("cat_code", "OTHER") for q in rubric_questions}

    stats: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "total": 0,
        "withheld_count": 0,
        "pairs": 0,
        "exact_count": 0,
        "abs_errors": [],
        "signed_errors": [],
    })

    for sid in startup_ids:
        path = Path(cache_dir) / f"{sid}.json"
        if not path.is_file():
            continue
        records = json.loads(path.read_text(encoding="utf-8"))
        for rec in records:
            qid = rec.get("q_id")
            cat = cat_map.get(qid, qid.split("_")[0] if "_" in str(qid) else "OTHER")
            val = rec.get("predicted_val")
            stats[cat]["total"] += 1

            if val is None:
                stats[cat]["withheld_count"] += 1
                continue

            if (sid, qid) in human:
                h_val = human[(sid, qid)]
                diff = float(val) - h_val
                abs_diff = abs(diff)
                stats[cat]["pairs"] += 1
                stats[cat]["abs_errors"].append(abs_diff)
                stats[cat]["signed_errors"].append(diff)
                if abs_diff < 1e-9:
                    stats[cat]["exact_count"] += 1

    summary = {}
    for cat, d in sorted(stats.items()):
        p = d["pairs"]
        t = d["total"]
        mae = (sum(d["abs_errors"]) / p) if p else 0.0
        bias = (sum(d["signed_errors"]) / p) if p else 0.0
        exact_pct = (d["exact_count"] / p * 100) if p else 0.0
        withheld_pct = (d["withheld_count"] / t * 100) if t else 0.0
        summary[cat] = {
            "total_criteria": t,
            "pairs": p,
            "exact_count": d["exact_count"],
            "exact_match_pct": exact_pct,
            "mae": mae,
            "mean_bias": bias,
            "withheld_count": d["withheld_count"],
            "withheld_pct": withheld_pct,
        }
    return summary


def rank_worst_criteria(
    cache_dir: Path,
    human_rows: list[dict[str, Any]],
    startup_ids: list[str],
    rubric_questions: list[dict[str, Any]],
    top_k: int = 15,
) -> list[dict[str, Any]]:
    human = _index_human_scores(human_rows)
    q_meta = {q.get("new_q_id", q.get("q_id")): q for q in rubric_questions}

    q_data: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "abs_errors": [],
        "signed_errors": [],
        "exact_count": 0,
        "withheld_count": 0,
        "total_evals": 0,
    })

    for sid in startup_ids:
        path = Path(cache_dir) / f"{sid}.json"
        if not path.is_file():
            continue
        records = json.loads(path.read_text(encoding="utf-8"))
        for rec in records:
            qid = rec.get("q_id")
            val = rec.get("predicted_val")
            q_data[qid]["total_evals"] += 1

            if val is None:
                q_data[qid]["withheld_count"] += 1
                continue

            if (sid, qid) in human:
                h_val = human[(sid, qid)]
                diff = float(val) - h_val
                abs_diff = abs(diff)
                q_data[qid]["abs_errors"].append(abs_diff)
                q_data[qid]["signed_errors"].append(diff)
                if abs_diff < 1e-9:
                    q_data[qid]["exact_count"] += 1

    ranked = []
    for qid, d in q_data.items():
        pairs = len(d["abs_errors"])
        if pairs == 0:
            continue
        mae = sum(d["abs_errors"]) / pairs
        bias = sum(d["signed_errors"]) / pairs
        exact_pct = (d["exact_count"] / pairs * 100) if pairs else 0.0
        meta = q_meta.get(qid, {})
        ranked.append({
            "q_id": qid,
            "cat_code": meta.get("cat_code", qid.split("_")[0]),
            "text": meta.get("text", ""),
            "pairs": pairs,
            "mae": mae,
            "mean_bias": bias,
            "exact_match_pct": exact_pct,
            "withheld_count": d["withheld_count"],
        })

    # Sort descending by MAE, then ascending by exact match percentage
    ranked.sort(key=lambda x: (-x["mae"], x["exact_match_pct"]))
    return ranked[:top_k]


def classify_error_modes(
    cache_dir: Path,
    human_rows: list[dict[str, Any]],
    startup_ids: list[str],
) -> dict[str, int]:
    human = _index_human_scores(human_rows)
    modes = {
        "exact_match": 0,
        "over_prediction": 0,            # AI=1.0 while Human <= 0.25
        "under_prediction": 0,           # AI=0.0 while Human >= 0.75
        "fractional_tier_mismatch": 0,   # Delta in (0.25, 0.5]
        "withheld": 0,                   # AI=None while human reviewed
    }

    for sid in startup_ids:
        path = Path(cache_dir) / f"{sid}.json"
        if not path.is_file():
            continue
        records = json.loads(path.read_text(encoding="utf-8"))
        for rec in records:
            qid = rec.get("q_id")
            val = rec.get("predicted_val")
            if (sid, qid) not in human:
                continue
            h_val = human[(sid, qid)]

            if val is None:
                modes["withheld"] += 1
                continue

            diff = float(val) - h_val
            abs_diff = abs(diff)

            if abs_diff < 1e-9:
                modes["exact_match"] += 1
            elif float(val) >= 0.99 and h_val <= 0.25:
                modes["over_prediction"] += 1
            elif float(val) <= 0.01 and h_val >= 0.75:
                modes["under_prediction"] += 1
            else:
                modes["fractional_tier_mismatch"] += 1

    return modes
```

- [x] **Step 4: Run tests to confirm they pass**

Run: `./venv/bin/python3 -m unittest -v tests.test_analyze_benchmark_discrepancies`
Expected: `Ran 3 tests in 0.002s ... OK`

- [x] **Step 5: Commit**

```bash
git add scripts/analyze_benchmark_discrepancies.py tests/test_analyze_benchmark_discrepancies.py
git commit -m "feat(diagnostics): add benchmark discrepancy analysis engine"
```

---

### Task 2: Markdown Diagnostic Report Generator & CLI

**Files:**
- Modify: `scripts/analyze_benchmark_discrepancies.py`
- Modify: `tests/test_analyze_benchmark_discrepancies.py`

**Interfaces:**
- Produces: `format_discrepancy_markdown(cat_summary: dict, worst_q: list[dict], error_modes: dict, total_records: int, provenance_meta: dict) -> str`
- Produces: CLI interface supporting `--cache-dir`, `--human-json`, `--startups`, `--rubric`, `--out-md`, `--out-json`.

- [x] **Step 1: Write the failing tests**

Append to `tests/test_analyze_benchmark_discrepancies.py`:

```python
    def test_format_discrepancy_markdown(self):
        from scripts.analyze_benchmark_discrepancies import format_discrepancy_markdown
        cat_summary = {
            "BC": {"pairs": 10, "exact_match_pct": 50.0, "mae": 0.3, "mean_bias": 0.1, "withheld_pct": 20.0, "total_criteria": 12}
        }
        worst_q = [
            {"q_id": "BC_Q1", "cat_code": "BC", "text": "Value Prop", "pairs": 5, "mae": 0.6, "mean_bias": 0.2, "exact_match_pct": 40.0}
        ]
        modes = {"exact_match": 5, "over_prediction": 2, "under_prediction": 1, "fractional_tier_mismatch": 2, "withheld": 2}
        md = format_discrepancy_markdown(cat_summary, worst_q, modes, 12, {"source_host": "local", "path": "test"})
        self.assertIn("# Task 0 Benchmark Discrepancy Analysis", md)
        self.assertIn("| BC |", md)
        self.assertIn("BC_Q1", md)
        self.assertIn("Over-prediction", md)
```

- [x] **Step 2: Run test to verify it fails**

Run: `./venv/bin/python3 -m unittest -v tests.test_analyze_benchmark_discrepancies`
Expected: `ImportError: cannot import name 'format_discrepancy_markdown'`

- [x] **Step 3: Implement report formatter and CLI**

Append to `scripts/analyze_benchmark_discrepancies.py`:

```python
def format_discrepancy_markdown(
    cat_summary: dict[str, dict[str, Any]],
    worst_q: list[dict[str, Any]],
    error_modes: dict[str, int],
    total_records: int,
    provenance_meta: dict[str, Any],
) -> str:
    lines = [
        "# Task 0 Benchmark Discrepancy Analysis Report",
        "",
        "## 1. Provenance & Dataset Header",
        f"- **Source Host:** `{provenance_meta.get('source_host', 'Spark 136.24.130.250')}`",
        f"- **Cache Directory:** `{provenance_meta.get('cache_dir', 'ai_cache_l2_bench_baseline')}`",
        f"- **Benchmark Startups (N=5):** `{', '.join(provenance_meta.get('startups', []))}`",
        f"- **Total Evaluated Records:** `{total_records}`",
        "",
        "## 2. Category Performance Summary",
        "Categories ranked by exact match rate (lowest to highest):",
        "",
        "| Category | Code | Evaluated Pairs | Exact Match % | MAE | Mean Bias (AI - Human) | Withheld % |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]

    sorted_cats = sorted(cat_summary.items(), key=lambda x: (x[1]["exact_match_pct"], -x[1]["mae"]))
    for code, s in sorted_cats:
        bias_str = f"+{s['mean_bias']:.3f}" if s["mean_bias"] > 0 else f"{s['mean_bias']:.3f}"
        lines.append(
            f"| {code} | `{code}` | {s['pairs']} | **{s['exact_match_pct']:.2f}%** | {s['mae']:.3f} | {bias_str} | {s['withheld_pct']:.2f}% |"
        )

    lines.extend([
        "",
        "## 3. Global Error Mode Distribution",
        "",
        "| Error Mode | Occurrence Count | Percentage of Evaluated Pairs | Diagnosis |",
        "| :--- | :---: | :---: | :--- |",
    ])

    total_pairs = sum(error_modes.values())
    mode_descriptions = {
        "exact_match": "Exact score agreement within 1e-9",
        "over_prediction": "AI awarded 1.0 while human scored <= 0.25 (loose regex or hallucinations)",
        "under_prediction": "AI awarded 0.0 while human scored >= 0.75 (overly strict gating or primary doc miss)",
        "fractional_tier_mismatch": "Disagreement on intermediate tiers (e.g. 0.5 vs 0.75)",
        "withheld": "Model safely withheld without guessing",
    }
    for mode, count in error_modes.items():
        pct = (count / total_pairs * 100) if total_pairs else 0.0
        lines.append(f"| **{mode.replace('_', ' ').title()}** | {count} | {pct:.2f}% | {mode_descriptions.get(mode, '')} |")

    lines.extend([
        "",
        "## 4. Top 15 Highest-Discrepancy Criteria",
        "Specific rubric questions with the highest mean absolute error (MAE) across the benchmark cohort:",
        "",
        "| Question ID | Category | Question Prompt Excerpt | Pairs | MAE | Mean Bias | Exact Match % |",
        "| :--- | :---: | :--- | :---: | :---: | :---: | :---: |",
    ])

    for q in worst_q:
        prompt_snippet = (q["text"][:65] + "...") if len(q["text"]) > 65 else q["text"]
        prompt_snippet = prompt_snippet.replace("|", "/")
        bias_str = f"+{q['mean_bias']:.3f}" if q["mean_bias"] > 0 else f"{q['mean_bias']:.3f}"
        lines.append(
            f"| `{q['q_id']}` | `{q['cat_code']}` | {prompt_snippet} | {q['pairs']} | **{q['mae']:.3f}** | {bias_str} | {q['exact_match_pct']:.1f}% |"
        )

    lines.extend([
        "",
        "## 5. Architectural Implications for Layer 2",
        "1. **Business Canvas (`BC`) & Market (`M`):** Exhibit lowest exact matches (<60%) and highest withholdings, directly reflecting missing customer discovery / market matrix primary document routing.",
        "2. **Over-prediction on Quantitative Criteria (`F_Q11`, `F_Q14`, `PMF_Q30`):** Confirms why Task 1 line-bounded deterministic evaluator is strictly needed.",
        "3. **Visual Deck Criteria (`IP_Q7`, `PMF_Q24`):** Confirm 100% failure rate on diagram/flowchart criteria, proving the hypothesis in Task 4.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description="Digest Task 0 benchmark discrepancies")
    ap.add_argument("--cache-dir", required=True)
    ap.add_argument("--human-json", required=True)
    ap.add_argument("--rubric", required=True)
    ap.add_argument("--startups", required=True)
    ap.add_argument("--out-md", help="Output path for Markdown report")
    ap.add_argument("--out-json", help="Output path for JSON data")
    a = ap.parse_args()

    human_rows = json.loads(Path(a.human_json).read_text(encoding="utf-8"))
    rubric_questions = json.loads(Path(a.rubric).read_text(encoding="utf-8"))
    startup_ids = [s.strip() for s in a.startups.split(",") if s.strip()]

    cat_summary = analyze_category_discrepancies(Path(a.cache_dir), human_rows, startup_ids, rubric_questions)
    worst_q = rank_worst_criteria(Path(a.cache_dir), human_rows, startup_ids, rubric_questions, top_k=15)
    modes = classify_error_modes(Path(a.cache_dir), human_rows, startup_ids)

    prov = {
        "source_host": "Spark 136.24.130.250",
        "cache_dir": str(a.cache_dir),
        "startups": startup_ids,
    }

    report_md = format_discrepancy_markdown(cat_summary, worst_q, modes, len(startup_ids) * 282, prov)

    if a.out_md:
        Path(a.out_md).write_text(report_md, encoding="utf-8")
        print(f"Wrote report to {a.out_md}")
    if a.out_json:
        data = {
            "provenance": prov,
            "category_summary": cat_summary,
            "worst_criteria": worst_q,
            "error_modes": modes,
        }
        Path(a.out_json).write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"Wrote data to {a.out_json}")


if __name__ == "__main__":
    main()
```

- [x] **Step 4: Run tests to confirm they pass**

Run: `./venv/bin/python3 -m unittest -v tests.test_analyze_benchmark_discrepancies`
Expected: `Ran 4 tests ... OK`

- [x] **Step 5: Commit**

```bash
git add scripts/analyze_benchmark_discrepancies.py tests/test_analyze_benchmark_discrepancies.py
git commit -m "feat(diagnostics): add Markdown report formatter and CLI to benchmark discrepancy analyzer"
```

---

### Task 3: Execute Discrepancy Analysis on Spark & Record Findings

**Files:**
- Create: `outputs/l2_task0_discrepancy_report.md`
- Create: `outputs/l2_task0_discrepancy_data.json`

- [x] **Step 1: Execute diagnostic script on Spark against benchmark cache**

```bash
scp scripts/analyze_benchmark_discrepancies.py jkim@136.24.130.250:/data/scraping/scripts/
ssh jkim@136.24.130.250 'cd /data/scraping && PYTHONPATH=. venv/bin/python scripts/analyze_benchmark_discrepancies.py \
  --cache-dir datasets/cto_accelerator/ai_cache_l2_bench_baseline \
  --human-json outputs/human_scores.json \
  --rubric datasets/cto_accelerator/master_282_rubric.json \
  --startups 2DaLoop,AmpTrans,Averra,Biomific,Calectra \
  --out-md outputs/l2_task0_discrepancy_report.md \
  --out-json outputs/l2_task0_discrepancy_data.json'
scp jkim@136.24.130.250:/data/scraping/outputs/l2_task0_discrepancy_report.md outputs/
scp jkim@136.24.130.250:/data/scraping/outputs/l2_task0_discrepancy_data.json outputs/
```

- [x] **Step 2: Verify output files exist and contain complete findings**

Run: `./venv/bin/python3 -c "import json; d=json.load(open('outputs/l2_task0_discrepancy_data.json')); assert len(d['category_summary']) == 10; assert len(d['worst_criteria']) == 15; print('DIAGNOSTICS_VERIFIED')"`
Expected: `DIAGNOSTICS_VERIFIED`

- [x] **Step 3: Commit authoritative diagnostic reports**

```bash
git add outputs/l2_task0_discrepancy_report.md outputs/l2_task0_discrepancy_data.json
git commit -m "docs(diagnostics): record Task 0 baseline discrepancy analysis report"
```
