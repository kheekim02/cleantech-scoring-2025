# Layer 2 Extractor Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `scripts/14_ai_copilot_extractor_v2.py` cheaper and more accurate for future cohort runs. Every change has to pass a measured before/after benchmark on Spark before it is adopted.

**Architecture:** Four changes to the per-question scoring path. (1) A deterministic short-circuit that answers a small set of structured criteria from primary markdown with an exact-span citation, before any LLM call. (2) A refactor that moves prompt construction and per-question scoring out of closures so they can be tested. (3) A policy file that replaces hardcoded per-question prompt patches. (4) Optional small-group batching, off by default and adopted only if the benchmark shows a gain. Every output still goes through the existing `accept_model_answer` grounding gate.

**Tech Stack:** Python 3.12, stdlib `unittest` (pytest is not installed in `venv`), SGLang (RadixAttention) / Ollama on Spark, existing `src/scorer/schemas.py` grounding helpers.

**Spec:** `AGENTS.md` (repo root) §3–§5. `docs/CITATION_RATIONALE_AUDIT_GATES.md`. `docs/superpowers/plans/2026-10-09-recalibrate-282-criteria-scores.md` (Layer 3, whose deterministic rules are adapted and tightened here directly on clean `main`).

## Global Constraints

- Rubric is frozen: `master_282_rubric.json` question IDs, text, and options are never edited.
- No Supabase writes. Reading `human_reviews` through `scripts/export_scored_data.py` is allowed for benchmarking.
- Never write to the promoted SoR `/data/scraping/datasets/cto_accelerator/ai_cache_v5_parsed`. All Spark benchmark runs use `--cache-dir /data/scraping/datasets/cto_accelerator/ai_cache_l2_bench_<variant>`.
- Every record still passes `accept_model_answer` and `scripts/audit_v5_parsed.py`. A non-zero score with no exact-span citation must never be written.
- Default CLI behavior after this plan should match today's behavior except for the deterministic short-circuit (Task 2). Batching stays opt-in.
- Spark host: `jkim@136.24.130.250`. Python: `/data/scraping/venv/bin/python` run from `/data/scraping`.
- Test runner: `./venv/bin/python3 -m unittest -v <module>`.

## Review Focus

1. Deterministic false positives: a regex that matches scattered words across a long document (e.g. "Year 1 … Year 3" spread over pages) must not award 1.0.
2. Regex absence is not evidence absence. The short-circuit may only award a positive score. When the regex finds nothing, the question must fall through to the LLM and must not be scored 0.0.
3. Batching cross-contamination: one batched response must never put question A's citation or rationale on question B. This failure mode is a relative of the cross-company clone rationales fixed in Waves 0–3.
4. Prompt drift: moving the ES_Q1 patch into the policy file must leave the system prompt for every question byte-identical.
5. Writing to the promoted cache by accident: a benchmark run that omits `--cache-dir` falls back to `default_cache_dir()`, which is the promoted SoR on Spark.

## Corrected assumptions (read before Task 1)

- **Prefix caching already exists.** `scripts/sglang_service.sh` serves with SGLang RadixAttention, so the shared category context is already prefix-cached across the 282 per-question calls. Earlier advice claimed batching would fix "KV-cache thrashing". That claim is unverified. Batching can still save HTTP round-trips and decode overhead, so Task 5 measures it before anyone adopts it.
- **A per-category cascade already exists.** `query_sglang_question` returns `NO_PRIMARY` without calling the model when a category has no primary document. A startup-level "screen-out" would delete ops data that humans compare against, so it is **out of scope**.
- **There are no visual markers in the local markdown.** `grep` found zero `<!-- image -->` / `![...]()` tokens in `data/parsed_clean`. Task 4 measures whether `parsed_clean_v4` on Spark has any before relying on prompt-level visual guidance.

---

### Task 0: Baseline Snapshot and Benchmark Harness

**Files:**
- Create: `scripts/benchmark_extractor.py`
- Create: `tests/test_benchmark_extractor.py`

**Interfaces:**
- Produces: `compare_cache_to_human(cache_dir: Path, human_rows: list[dict], startup_ids: list[str]) -> dict` returning `{"n_pairs", "exact_match", "mae", "withheld_rate", "scored_rate", "cited_rate"}`.
- Produces: CLI `python scripts/benchmark_extractor.py --cache-dir DIR --human-json FILE --startups A,B,C --out FILE`.

- [x] **Step 1: Baseline settled.** Uncommitted Waves 0–3 citation remediation baseline diffed against Spark production (`136.24.130.250:/data/scraping/`), verified, and committed on clean `main` as `29a1be6` (`feat(extractor): record Waves 0-3 citation remediation baseline`). Layer 3 draft commits preserved on `layer3-draft` (`5fabe60`). Ledger `L2_BASE = 29a1be6`.

- [x] **Step 2: Write the failing test** (created `tests/test_benchmark_extractor.py`)

- [x] **Step 3: Run it to confirm it fails** (`ModuleNotFoundError: No module named 'scripts.benchmark_extractor'`)

- [x] **Step 4: Implement `scripts/benchmark_extractor.py`** (implemented `compare_cache_to_human` and CLI)

- [x] **Step 5: Run the test to confirm it passes** (`Ran 1 test in 0.001s ... OK`)

- [x] **Step 6: Freeze the benchmark set and capture the baseline (Spark, read-only toward the SoR)**
Frozen `BENCH_SET = ["2DaLoop", "AmpTrans", "Averra", "Biomific", "Calectra"]`.
Exported 11,920 records to `outputs/human_scores.json`.
Baseline metrics captured into `outputs/l2_bench_baseline.json`:
- `n_records`: 1410
- `n_pairs`: 1266
- `exact_match`: 0.6927 (69.27%)
- `mae`: 0.2882
- `withheld_rate`: 0.1021 (10.21%)
- `scored_rate`: 0.8979 (89.79%)
- `cited_rate`: 0.6532 (65.32%)
- `audit_v5_parsed.py`: 5/5 PASS.

- [x] **Step 7: Commit**

```bash
git add scripts/benchmark_extractor.py tests/test_benchmark_extractor.py outputs/l2_bench_baseline.json
git commit -m "test(extractor): add read-only cache-vs-human benchmark harness and freeze baseline"
```

---

### Task 1: Create the Tightened Deterministic Evaluator and Return an Exact Evidence Span

**Files:**
- Create: `src/scorer/deterministic_evaluator.py`
- Create: `tests/test_deterministic_evaluator.py`

**Interfaces:**
- Produces: `DETERMINISTIC_RULES` (dict of regex patterns and labels for `F_Q1`, `F_Q7`, `L_Q1`, `L_Q14`)
- Produces: `find_deterministic_evidence(q_id: str, primary_text: str | None) -> str | None`. Returns the full source line containing the match, copied verbatim from `primary_text`, or `None`.
- Produces: `evaluate_deterministic_criterion(q_id: str, raw_text: str | None, current_val: float | None) -> tuple[float | None, bool, str]`

- [x] **Step 1: Write the failing tests**

```python
# tests/test_deterministic_evaluator.py
import unittest
from src.scorer.deterministic_evaluator import (
    DETERMINISTIC_RULES,
    evaluate_deterministic_criterion,
    find_deterministic_evidence,
)


class TestDeterministicEvaluator(unittest.TestCase):
    def test_f_q1_line_bounded_match(self):
        text = "Year 1 revenue: $100K | Year 2 revenue: $500K | Year 3 revenue: $2M\nRisks"
        val, overridden, reason = evaluate_deterministic_criterion("F_Q1", text, 0.0)
        self.assertTrue(overridden)
        self.assertEqual(val, 1.0)
        self.assertIn("3-Year financial projection model detected", reason)

    def test_f_q1_ignores_year_mentions_scattered_across_document(self):
        text = "Year 1 we hired an engineer.\n" + ("filler line\n" * 200) + "Year 2 pilot.\nYear 3 plan."
        val, overridden, _ = evaluate_deterministic_criterion("F_Q1", text, 0.0)
        self.assertFalse(overridden)
        self.assertEqual(val, 0.0)

    def test_f_q7_breakeven(self):
        text = "Financial Summary\nWe reach breakeven in Year 3 with $150K net profit.\nAppendix"
        val, overridden, _ = evaluate_deterministic_criterion("F_Q7", text, 0.0)
        self.assertTrue(overridden)
        self.assertEqual(val, 1.0)

    def test_l_q1_corp_entity(self):
        text = "Legal Formation\nCompany was incorporated in Delaware as a Delaware C-Corp in 2024."
        val, overridden, _ = evaluate_deterministic_criterion("L_Q1", text, 0.0)
        self.assertTrue(overridden)
        self.assertEqual(val, 1.0)

    def test_l_q14_patent(self):
        text = "Intellectual Property\nPatent No. US 11456789 was granted on clean hydrogen synthesis."
        val, overridden, _ = evaluate_deterministic_criterion("L_Q14", text, 0.0)
        self.assertTrue(overridden)
        self.assertEqual(val, 1.0)

    def test_find_evidence_returns_verbatim_source_line(self):
        text = "Overview\nWe reach breakeven in Year 3 with $150K net profit.\nRisks"
        span = find_deterministic_evidence("F_Q7", text)
        self.assertEqual(span, "We reach breakeven in Year 3 with $150K net profit.")
        self.assertIn(span, text)

    def test_find_evidence_none_for_unruled_question(self):
        self.assertIsNone(find_deterministic_evidence("BC_Q1", "anything"))

    def test_find_evidence_none_when_no_match(self):
        self.assertIsNone(find_deterministic_evidence("F_Q7", "No breakeven mentioned."))

    def test_unruled_question_not_overridden(self):
        val, overridden, _ = evaluate_deterministic_criterion("BC_Q1", "some text", 0.5)
        self.assertFalse(overridden)
        self.assertEqual(val, 0.5)


if __name__ == "__main__":
    unittest.main()
```

- [x] **Step 2: Run them to confirm they fail**

Run: `./venv/bin/python3 -m unittest -v tests.test_deterministic_evaluator`
Expected: `ModuleNotFoundError: No module named 'src.scorer.deterministic_evaluator'`

- [x] **Step 3: Implement `src/scorer/deterministic_evaluator.py`**

```python
# src/scorer/deterministic_evaluator.py
from __future__ import annotations
import re

PATENT_RE = re.compile(
    r"\b(?:US|EP|WO)\s?\d{7,8}[A-Z\d]?\b|\bpatent(?:\s+(?:number|no\.?|#|issued|application))?\s*(?:US|EP|WO)?\s*\d{6,8}\b|\bissued\s+patents?\b",
    re.IGNORECASE,
)

BREAKEVEN_RE = re.compile(
    r"\b(?:break[\s-]?even\s+(?:in|by|reached|achieved|at)\s+(?:year|month|\d{4})|cash\s+flow\s+positive\s+(?:in|by)\s+year\s*\d|breakeven\s+in\s+year\s*\d)\b",
    re.IGNORECASE,
)

CORP_ENTITY_RE = re.compile(
    r"\b(?:delaware\s+c[\s-]?corp|c[\s-]?corporation|incorporated\s+in\s+delaware|delaware\s+llc|limited\s+liability\s+company)\b",
    re.IGNORECASE,
)

PROJECTIONS_3YR_RE = re.compile(
    r"\b(?:3[\s-]year\s+(?:financial\s+)?projections?"
    r"|year\s*1\b[^\n]{0,200}?year\s*2\b[^\n]{0,200}?year\s*3\b"
    r"|\by1\b[^\n]{0,120}?\by2\b[^\n]{0,120}?\by3\b)",
    re.IGNORECASE,
)

DETERMINISTIC_RULES = {
    "F_Q1": {"pattern": PROJECTIONS_3YR_RE, "label": "3-Year financial projection model detected"},
    "F_Q7": {"pattern": BREAKEVEN_RE, "label": "Breakeven detected in financial projections"},
    "L_Q1": {"pattern": CORP_ENTITY_RE, "label": "Corporate legal entity structure verified"},
    "L_Q14": {"pattern": PATENT_RE, "label": "Issued patent detected in legal deliverables"},
}


def find_deterministic_evidence(q_id: str, primary_text: str | None) -> str | None:
    """Return the verbatim source line that satisfies a deterministic rule, else None."""
    if not primary_text or q_id not in DETERMINISTIC_RULES:
        return None
    match = DETERMINISTIC_RULES[q_id]["pattern"].search(primary_text)
    if not match:
        return None
    line_start = primary_text.rfind("\n", 0, match.start()) + 1
    line_end = primary_text.find("\n", match.end())
    if line_end == -1:
        line_end = len(primary_text)
    line = primary_text[line_start:line_end].strip()
    return line or None


def evaluate_deterministic_criterion(
    q_id: str,
    raw_text: str | None,
    current_val: float | None,
) -> tuple[float | None, bool, str]:
    """Overrides subjective/flawed LLM evaluation with deterministic regex checks on primary markdown."""
    if not raw_text or q_id not in DETERMINISTIC_RULES:
        return current_val, False, ""

    rule = DETERMINISTIC_RULES[q_id]
    match = rule["pattern"].search(raw_text)
    if match:
        snippet = match.group(0).replace("\n", " ").strip()
        if len(snippet) > 60:
            snippet = snippet[:57] + "..."
        return 1.0, True, f"Deterministic Override: {rule['label']} ('{snippet}')."

    return current_val, False, ""
```

- [x] **Step 4: Run tests to confirm they pass**

Run: `./venv/bin/python3 -m unittest -v tests.test_deterministic_evaluator`
Expected: All 9 tests OK.

- [x] **Step 5: Commit**

```bash
git add src/scorer/deterministic_evaluator.py tests/test_deterministic_evaluator.py
git commit -m "feat(scorer): create line-bounded deterministic evaluator with evidence span extraction"
```

---

### Task 2: Extract `score_question` and Add the Deterministic Short-Circuit

**Files:**
- Modify: `scripts/14_ai_copilot_extractor_v2.py` (the nested `_score_one` inside `evaluate_startup`, ~L899–930; add module-level functions above `evaluate_startup`)
- Create: `tests/test_layer2_short_circuit.py`

**Interfaces:**
- Consumes: `find_deterministic_evidence`, `DETERMINISTIC_RULES` (Task 1); `accept_model_answer` (existing).
- Produces: `deterministic_answer(question: dict, primary_text: str, company: str) -> dict | None`
- Produces: `score_question(question: dict, ctx: dict, *, query_fn, client, model_id, timeout, doc_manifest, endpoint, startup_id) -> dict`

- [ ] **Step 1: Write the failing tests**

```python
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
```

- [ ] **Step 2: Run them to confirm they fail**

Run: `./venv/bin/python3 -m unittest -v tests.test_layer2_short_circuit`
Expected: `AttributeError: module 'extractor_l2' has no attribute 'score_question'`

- [ ] **Step 3: Implement**

Add the import near the other `src.scorer` imports:

```python
from src.scorer.deterministic_evaluator import DETERMINISTIC_RULES, find_deterministic_evidence
```

Add above `evaluate_startup`:

```python
def deterministic_answer(question: dict[str, Any], primary_text: str, company: str) -> dict[str, Any] | None:
    """Positive-only structured answer. Regex absence never produces a score."""
    qid = question.get("new_q_id") or question.get("q_id")
    allowed = {round(float(o.get("val")), 2) for o in question.get("options") or [] if o.get("val") is not None}
    if allowed and 1.0 not in allowed:
        return None
    span = find_deterministic_evidence(qid, primary_text)
    if not span:
        return None
    raw = {
        "q_id": qid,
        "predicted_val": 1.0,
        "confidence": 0.95,
        "citation": span,
        "rationale": f"{company} primary text states: {span} {DETERMINISTIC_RULES[qid]['label']}.",
    }
    rec = accept_model_answer(raw, primary_text, question, company=company)
    if rec.get("error_code") or rec.get("predicted_val") != 1.0:
        return None
    rec["source"] = "deterministic"
    return rec


def score_question(
    question: dict[str, Any],
    ctx: dict[str, Any],
    *,
    query_fn: Any,
    client: Any,
    model_id: str,
    timeout: int,
    doc_manifest: dict[str, list[str]],
    endpoint: str,
    startup_id: str,
) -> dict[str, Any]:
    primary_text = ctx.get("primary_text", "")
    has_primary = ctx.get("has_primary", False)
    if has_primary:
        det = deterministic_answer(question, primary_text, startup_id)
        if det is not None:
            return det

    def _ask(temperature: float) -> dict[str, Any]:
        raw = query_fn(client, model_id, ctx.get("text", ""), question, timeout, doc_manifest,
                       has_primary, endpoint, startup_id=startup_id, temperature=temperature)
        return accept_model_answer(raw, primary_text, question, company=startup_id)

    rec = _ask(0.0)
    if rec.get("error_code") in RETRYABLE_ERROR_CODES:
        rec = _ask(0.2)
    return rec
```

Replace the body of the nested `_score_one` in `evaluate_startup` with:

```python
    def _score_one(q: dict[str, Any]) -> dict[str, Any]:
        return score_question(
            q,
            category_contexts.get(q.get("cat_code") or "") or {},
            query_fn=query_sglang_question,
            client=inst_client,
            model_id=model_id,
            timeout=timeout,
            doc_manifest=doc_manifest,
            endpoint=sglang_url,
            startup_id=startup_id,
        )
```

- [ ] **Step 4: Run new and existing extractor tests**

Run: `./venv/bin/python3 -m unittest -v tests.test_layer2_short_circuit tests.test_parsed_markdown_scoring tests.test_accept_path_remediation tests.test_category_context tests.test_extraction_audit`
Expected: all OK. If an existing test fails, use superpowers:systematic-debugging. Do not edit the existing tests.

- [ ] **Step 5: Small-batch Spark check (1 startup, F and L questions only)**

```bash
scp scripts/14_ai_copilot_extractor_v2.py src/scorer/deterministic_evaluator.py jkim@136.24.130.250:/tmp/l2/
ssh jkim@136.24.130.250 'cd /data/scraping && PYTHONPATH=/tmp/l2:/data/scraping venv/bin/python /tmp/l2/14_ai_copilot_extractor_v2.py \
  --startup <BENCH_SET[0]> --question-ids F_Q1,F_Q7,L_Q1,L_Q14 \
  --cache-dir datasets/cto_accelerator/ai_cache_l2_bench_task2'
```

Expected: records with `"source": "deterministic"` carry a citation that `audit_v5_parsed.py` accepts. Inspect every deterministic hit by hand. Any false positive sends you back to Task 1.

- [ ] **Step 6: Commit**

```bash
git add scripts/14_ai_copilot_extractor_v2.py tests/test_layer2_short_circuit.py
git commit -m "feat(extractor): short-circuit structured criteria with grounded deterministic answers"
```

---

### Task 3: Move Prompt Construction into `build_system_prompt` and a Policy File

**Files:**
- Create: `data/category_policies.json`
- Modify: `scripts/14_ai_copilot_extractor_v2.py` (`query_sglang_question` ~L642–672)
- Create: `tests/test_layer2_policies.py`

**Interfaces:**
- Produces: `load_policies(path: str | None = None) -> dict` with shape `{"category": {cat: str}, "question": {qid: str}}`
- Produces: `build_system_prompt(question: dict, doc_manifest: dict | None, policies: dict) -> str`

- [ ] **Step 1: Write a characterization test against the CURRENT code (it should pass now)**

```python
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
```

- [ ] **Step 2: Run it. The golden file gets written; characterization passes and the policy test fails.**

Run: `./venv/bin/python3 -m unittest -v tests.test_layer2_policies`
Expected: `test_system_prompts_unchanged` OK (golden file created from current code). `test_build_system_prompt_uses_policy_file` ERRORS with `AttributeError: … 'load_policies'`. Commit the golden fixture now so the refactor is checked against it:

```bash
git add tests/fixtures/l2_system_prompts.json tests/test_layer2_policies.py
git commit -m "test(extractor): freeze current system prompts as characterization golden"
```

- [ ] **Step 3: Implement**

Create `data/category_policies.json`. Copy the ES_Q1 string **verbatim** from the current `sourcing_instruction +=` block (L657–665), including its leading space:

```json
{
  "category": {},
  "question": {
    "ES_Q1": " For ES_Q1 specifically: score 1.0 only when the citation shows the company purpose addressing two or more distinct UN SDG themes (e.g. climate/energy, water, waste/circularity, equity/community) with founder-specific facts; score 0.5 for one theme; score 0.0 when no impact-purpose evidence exists. You may award 0.5/1.0 from grounded narrative impact language without a literal 'SDG N' label. Never invent an SDG number. Prefer predicted_val 0.0 with a company-named absence rationale over withholding when evidence is truly absent."
  }
}
```

In the extractor, add:

```python
POLICY_PATH = Path(__file__).resolve().parent.parent / "data" / "category_policies.json"


def load_policies(path: str | None = None) -> dict[str, dict[str, str]]:
    p = Path(path) if path else POLICY_PATH
    data = json.loads(p.read_text(encoding="utf-8"))
    return {"category": data.get("category", {}), "question": data.get("question", {})}


def build_system_prompt(
    question: dict[str, Any], doc_manifest: dict[str, list[str]] | None, policies: dict[str, dict[str, str]]
) -> str:
    qid = question.get("new_q_id", question.get("q_id"))
    cat_code = question.get("cat_code", "GENERAL")
    primary_filenames: list[str] = []
    if doc_manifest and cat_code in CAT_PRIMARY_SOURCES:
        for tc in CAT_PRIMARY_SOURCES[cat_code]:
            primary_filenames.extend(doc_manifest.get(tc, []))
    file_list = ", ".join(f'"{f}"' for f in primary_filenames) if primary_filenames else "the documents marked [Role: PRIMARY]"
    sourcing_instruction = (
        f"For this {cat_code} criterion, quote only from these PRIMARY documents: {file_list}. "
        "Copy one unbroken contiguous region of founder text exactly as it appears. "
        "Do not paraphrase, splice distant sentences, or join table cells with pipes. "
        "If evidence is on separate short lines, copy those lines in document order with spaces only. "
        "The rationale may only repeat facts that appear in that span. "
        "Do not name an SDG number, dollar amount, or percentage unless those characters appear in the quote."
    )
    sourcing_instruction += policies["category"].get(cat_code, "")
    sourcing_instruction += policies["question"].get(str(qid), "")
    return (
        "You are an objective due diligence evaluator scoring cleantech startup applications. "
        "Strictly adhere to the provided rubric and only quote verbatim text written by founders. "
        "Do NOT quote instructions or template boilerplate. "
        f"{sourcing_instruction}"
    )
```

In `query_sglang_question`, delete the `primary_filenames` / `file_list` / `sourcing_instruction` / ES_Q1 / `system_prompt` block. Replace it with:

```python
    system_prompt = build_system_prompt(question, doc_manifest, _POLICIES)
```

Add `_POLICIES = load_policies()` at module level, after `load_policies` is defined.

- [ ] **Step 4: Run tests**

Run: `./venv/bin/python3 -m unittest -v tests.test_layer2_policies tests.test_layer2_short_circuit tests.test_parsed_markdown_scoring`
Expected: all OK. `test_system_prompts_unchanged` is the proof that the prompts are byte-identical after the refactor.

- [ ] **Step 5: Commit**

```bash
git add data/category_policies.json scripts/14_ai_copilot_extractor_v2.py
git commit -m "refactor(extractor): move per-question prompt patches into category_policies.json"
```

> Authoring new category policy text (Paper 6 policy induction from the 32 human-reviewed startups) is **not** in this plan. New policy text changes scores, needs a held-out split so the human labels don't leak into evaluation, and needs sign-off from the CleanTech Open track leads. This task only builds the mechanism.

---

### Task 4: Measure Visual Markers, Then Decide on Visual Guidance

**Files:**
- Create: `scripts/measure_visual_markers.py`
- Create: `tests/test_measure_visual_markers.py`
- Modify (conditional, Step 6): `data/category_policies.json`

**Interfaces:**
- Produces: `count_visual_markers(text: str) -> dict[str, int]` keyed by marker family (`image_comment`, `md_image`, `diagram_heading`, `figure_caption`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_measure_visual_markers.py
import unittest
from scripts.measure_visual_markers import count_visual_markers


class TestVisualMarkers(unittest.TestCase):
    def test_counts_marker_families(self):
        text = "<!-- image -->\n![fig](a.png)\n## Diagram\nFigure 2: Process flow\nplain text"
        c = count_visual_markers(text)
        self.assertEqual(c["image_comment"], 1)
        self.assertEqual(c["md_image"], 1)
        self.assertEqual(c["diagram_heading"], 1)
        self.assertEqual(c["figure_caption"], 1)

    def test_plain_prose_has_no_markers(self):
        self.assertEqual(sum(count_visual_markers("We use a schematic approach.").values()), 0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `./venv/bin/python3 -m unittest -v tests.test_measure_visual_markers`
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement**

```python
# scripts/measure_visual_markers.py
"""Count structural visual markers in parsed markdown (EBD8 pitch decks)."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

PATTERNS = {
    "image_comment": re.compile(r"<!--\s*image\b[^>]*-->", re.IGNORECASE),
    "md_image": re.compile(r"!\[[^\]]*\]\([^)]*\)"),
    "diagram_heading": re.compile(r"^#{1,6}\s*diagram\b", re.IGNORECASE | re.MULTILINE),
    "figure_caption": re.compile(r"^\s*(?:figure|fig\.)\s*\d+\s*[:.]", re.IGNORECASE | re.MULTILINE),
}


def count_visual_markers(text: str) -> dict[str, int]:
    return {name: len(p.findall(text or "")) for name, p in PATTERNS.items()}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parsed-dir", required=True)
    ap.add_argument("--glob", default="**/*EBD8*.md")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    per_file = {}
    for p in sorted(Path(a.parsed_dir).glob(a.glob)):
        per_file[str(p.relative_to(a.parsed_dir))] = count_visual_markers(p.read_text(encoding="utf-8", errors="ignore"))
    files_with_any = sum(1 for c in per_file.values() if sum(c.values()) > 0)
    summary = {"files": len(per_file), "files_with_any_marker": files_with_any, "per_file": per_file}
    Path(a.out).write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"{files_with_any}/{len(per_file)} files contain visual markers")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the test to confirm it passes**

Run: `./venv/bin/python3 -m unittest -v tests.test_measure_visual_markers`
Expected: OK

- [ ] **Step 5: Measure on Spark**

```bash
scp scripts/measure_visual_markers.py jkim@136.24.130.250:/tmp/l2/
ssh jkim@136.24.130.250 'cd /data/scraping && venv/bin/python /tmp/l2/measure_visual_markers.py \
  --parsed-dir datasets/cto_accelerator/parsed_clean_v4 --out outputs/visual_markers_v4.json'
```

If the EBD8 filename glob matches 0 files, check how `resolve_doc_type` names pitch decks and rerun with the right `--glob`. Do not guess.

- [ ] **Step 6: Decide (ruling, recorded in the ledger)**

- **If ≥50% of EBD8 files contain markers:** add an `"IP"` category policy and a `"PMF_Q24"` question policy to `data/category_policies.json`. The text should tell the model that the listed marker families are evidence of a visual, and that the citation must quote the caption or the marker line itself. Re-run `tests.test_layer2_policies`. The golden fixture will now differ for IP questions only, so regenerate it and review the diff line by line. Then run the Task 0 benchmark on IP_Q3, IP_Q7, IP_Q12, and PMF_Q24.
- **If <50%:** do not add the policy. Text prompting cannot see images that the parser dropped. Ledger `Task 4: Ruling: visual criteria need page-image (multimodal) scoring; out of scope`. Also flag that the Layer 3 diagram proxy (`src/scorer/diagram_proxy_rescorer.py`) matches prose words like "flowchart" and "schematic", so its AmpTrans upgrades need human review.

- [ ] **Step 7: Commit**

```bash
git add scripts/measure_visual_markers.py tests/test_measure_visual_markers.py
git commit -m "feat(extractor): add visual-marker census for pitch-deck markdown"
```

---

### Task 5: Opt-In Same-Category Small-Group Batching (Benchmark-Gated)

**Files:**
- Modify: `scripts/14_ai_copilot_extractor_v2.py`
- Create: `tests/test_layer2_batching.py`

**Interfaces:**
- Produces: `group_questions(questions: list[dict], batch_size: int) -> list[list[dict]]`. Groups only within the same `cat_code`, preserves rubric order, and gives each group ≤ `batch_size` questions.
- Produces: `split_batched_response(raw_items: list[dict], group: list[dict]) -> list[dict]`. Maps items to questions by exact `q_id`. A missing, duplicated, or unknown `q_id` yields a `TIMEOUT`-coded withhold for that question. Nothing is ever matched by position.
- Produces: CLI flag `--batch-size` (default `1`, which keeps current behavior).

- [ ] **Step 1: Write the failing tests**

```python
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
```

- [ ] **Step 2: Run them to confirm they fail**

Run: `./venv/bin/python3 -m unittest -v tests.test_layer2_batching`
Expected: `AttributeError: … 'group_questions'`

- [ ] **Step 3: Implement the grouping and splitting helpers**

```python
def group_questions(questions: list[dict[str, Any]], batch_size: int) -> list[list[dict[str, Any]]]:
    if batch_size <= 1:
        return [[x] for x in questions]
    by_cat: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for x in questions:
        cat = x.get("cat_code") or ""
        if cat not in by_cat:
            by_cat[cat] = []
            order.append(cat)
        by_cat[cat].append(x)
    groups: list[list[dict[str, Any]]] = []
    for cat in order:
        items = by_cat[cat]
        groups.extend(items[i:i + batch_size] for i in range(0, len(items), batch_size))
    return groups


def split_batched_response(raw_items: list[dict[str, Any]], group: list[dict[str, Any]]) -> list[dict[str, Any]]:
    wanted = [x.get("new_q_id") or x.get("q_id") for x in group]
    seen: dict[str, list[dict[str, Any]]] = {}
    for item in raw_items or []:
        if isinstance(item, dict) and item.get("q_id") in wanted:
            seen.setdefault(item["q_id"], []).append(item)
    out: list[dict[str, Any]] = []
    for qid in wanted:
        hits = seen.get(qid, [])
        if len(hits) == 1:
            out.append(dict(hits[0]))
        else:
            out.append({"q_id": qid, "predicted_val": None, "confidence": 0.0, "citation": None,
                        "rationale": None, "error_code": "TIMEOUT"})
    return out
```

- [ ] **Step 4: Run tests to confirm they pass**

Run: `./venv/bin/python3 -m unittest -v tests.test_layer2_batching`
Expected: 4 tests OK

- [ ] **Step 5: Wire up `--batch-size` (default 1) and the batched query path**

Add `query_batch(client, model_id, prefix_context, group, timeout, doc_manifest, has_primary, endpoint, startup_id, temperature) -> list[dict]`. It reuses `build_system_prompt(group[0], …)`. Its user prompt lists each criterion in its own `<rubric_criterion>` block and asks for a JSON object `{"answers": [ {q_id, predicted_val, confidence, citation, rationale}, … ]}`. Set `max_tokens=350 * len(group)`, pass the `answers` list through `split_batched_response`, then run every item through `accept_model_answer` on its own. Questions that the deterministic short-circuit (Task 2) answers are removed before grouping. Any question that comes back `TIMEOUT` or retryable from a batch gets retried through the existing single-question `score_question`. When `--batch-size 1` is set, `evaluate_startup` must take the unchanged single-question path. Add `batch_size: int = 1` to the `evaluate_startup` signature and to `common` in `__main__`.

Run: `./venv/bin/python3 -m unittest -v tests.test_layer2_batching tests.test_layer2_short_circuit tests.test_layer2_policies tests.test_parsed_markdown_scoring`
Expected: all OK

- [ ] **Step 6: Benchmark gate on Spark (BENCH_SET, batch sizes 1, 4, 8)**

Run the Task 0 benchmark commands three times with `--batch-size {1,4,8}`, each into `ai_cache_l2_bench_bs{N}`. Adopt a batch size >1 only if **all** of the following hold against `bs1`:
- `audit_v5_parsed.py` PASS count is unchanged
- `withheld_rate` rises by no more than 2 percentage points
- `exact_match` against humans drops by no more than 1 percentage point
- wall time per startup falls by ≥30%
- a manual check of 20 random batched non-zero records finds 0 cases where the citation answers a different question in the same group

If any criterion fails, keep the default at 1 and ledger `Task 5: Ruling: batching not adopted — <metric>`.

- [ ] **Step 7: Commit**

```bash
git add scripts/14_ai_copilot_extractor_v2.py tests/test_layer2_batching.py
git commit -m "feat(extractor): add opt-in same-category batching gated by benchmark"
```

---

### Task 6: End-to-End Benchmark and Go/No-Go Report

**Files:**
- Create: `outputs/l2_benchmark_report.md` (generated, committed)

- [ ] **Step 1: Run the final configuration on BENCH_SET into `ai_cache_l2_bench_final` and benchmark it against `l2_bench_baseline.json`.**

- [ ] **Step 2: Write the report.** Include a table of baseline vs final for wall time per startup, LLM request count (count records with no `source` field plus retries from the logs), `exact_match`, `mae`, `withheld_rate`, `cited_rate`, and the audit PASS count. Then list every ledger `Ruling:` line.

- [ ] **Step 3: Go/no-go.** A full 92-startup re-run into a new cache directory is the user's decision. It is not part of this plan. Promoting a new cache over `ai_cache_v5_parsed` must go through `scripts/promote_cache_gate.py` with the user's explicit approval.

- [ ] **Step 4: Commit**

```bash
git add outputs/l2_benchmark_report.md
git commit -m "docs(extractor): Layer 2 optimization benchmark report"
```

---

## Out of Scope (with reasons)

| Item | Reason |
| :--- | :--- |
| Startup-level two-stage screen-out | Per-category `NO_PRIMARY` already skips the LLM. Screening out whole startups would delete ops comparison data. |
| New category policy text (policy induction) | It changes scores. It needs a held-out split of the human-reviewed startups and track-lead sign-off. |
| Multimodal page-image scoring for IP_Q3/IP_Q7/IP_Q12/PMF_Q24 | Only relevant if Task 4 finds the markdown has dropped visuals. It needs a vision model and page rasters. |
| Any change to `site/` or Supabase | This is a judge-UI and AI-decoupling constraint. |
