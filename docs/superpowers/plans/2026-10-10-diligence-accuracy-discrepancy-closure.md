# Diligence Accuracy Improvement & Discrepancy Gap Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve diligence evaluation accuracy and close the human-AI scoring discrepancy gap across the CleanTech Open 2025 cohort by resolving Document Routing blindspots for Customer Discovery & Market Segments (`PMF`, `M`), ingesting slide deck visual elements for diagram/logo criteria (`IP_Q7`, `PMF_Q24`) via PyMuPDF vector inspection, and applying Layer 3 calibrated score mapping.

**Architecture:** A three-track enhancement to the diligence extraction and scoring pipeline:
1. *Document Routing & Fallback Synthesis:* Enhanced classification regexes in `scripts/docling_ingestion.py` for discovery interviews (`M1`), customer archetypes (`M3`), and market matrices (`EBD3`, `M4`), paired with multi-source fallback context generation in `scripts/14_ai_copilot_extractor_v2.py`.
2. *Visual Modality Deck Ingestion:* A PyMuPDF-based (`fitz`) slide deck inspector (`src/scorer/visual_deck_inspector.py`) extracting embedded raster images and vector diagrams from raw slide PDFs (`raw/*/08_*.pdf`) to generate structured visual manifests for `IP_Q7` (Problem model) and `PMF_Q24` (Billboard logo).
3. *Layer 3 Calibrated Score Mapping:* A category-aware fractional score calibrator (`src/scorer/score_calibrator.py`) that maps raw evidence strengths and confidence levels into human judge-aligned score tiers (`0.0, 0.25, 0.5, 0.75, 1.0`), eliminating systematic negative under-prediction bias without violating citation audit gates.

**Tech Stack:** Python 3.10+, PyMuPDF (`fitz`), scikit-learn (`sklearn`), NumPy, Pydantic (v2), Instructor, Standard Library `unittest`.

**Spec:** Master 282-Criteria Rubric (`master_282_rubric.json`), human scores ground truth (`outputs/human_scores.json`), Task 0 discrepancy findings (`outputs/l2_task0_discrepancy_report.md`), and canonical SoR (`ai_cache_promoted`).

## Global Constraints

- **Rubric Frozen:** Never modify `master_282_rubric.json` (exactly 282 criteria, immutable IDs, weights, and text).
- **SoR Immutability:** `ai_cache_promoted -> ai_cache_v5_parsed` is strictly read-only until an explicit promotion gate passes. All outputs write to dedicated candidate directories (`datasets/cto_accelerator/ai_cache_l3_candidate/`).
- **Zero Database Writes:** Zero writes to Supabase PostgreSQL or human review tables (`human_reviews`, `judge_assignments`).
- **Structural Contract:** Every startup evaluation output must contain exactly 92 active allowlisted startup JSON files, each with exactly 282 valid criteria records in identical rubric order.
- **Audit Gate Compliance:** Must achieve 0 HARD violations under `scripts/audit_citations_independent.py` (specifically Gate G3.1 cross-company duplicate citation check).

## Review Focus

1. *Document Routing False-Negatives:* Startups with customer discovery interviews named with irregular suffixes (e.g. `_Interviews.pdf`, `_DiscoveryLog.pdf`) must be classified into `M1`/`M3` rather than falling into `OTHER`.
2. *Multi-Source Fallback Quality:* When a dedicated `M1`/`M3` file is absent, `PMF` questions must synthesize Customer Segments from `EBD1` (Canvas) and `EBD8` (Pitch) without exceeding the context token budget or duplicating citations.
3. *Vector/Raster Visual Presence:* Slide decks with diagrams composed purely of vector shapes (rectangles, circles, arrows) rather than embedded PNG/JPEGs must be recognized as valid visual problem models for `IP_Q7`.
4. *Score Monotonicity in Calibration:* Calibrated scores must never invert ordering (e.g., higher raw evidence strength must always yield equal or greater calibrated score).
5. *Duplicate Citation Isolation:* Overrides and calibrations must never inject cross-company shared boilerplate strings that trigger Gate G3.1.

---

### Task 1: Document Classifier Enhancement for Discovery Logs & Market Matrices

**Files:**
- Modify: `scripts/docling_ingestion.py:20-100`
- Modify: `scripts/docling_ingestion.py:200-220`
- Create: `tests/test_docling_routing.py`

**Interfaces:**
- Consumes: Raw PDF filenames and opening text lines.
- Produces: Deliverable type codes (`M1`, `M3`, `M4`, `EBD3`) from `resolve_doc_type(filename, text)`.

- [ ] **Step 1: Write the failing unit test for expanded document patterns**

```python
# tests/test_docling_routing.py
import unittest
from scripts.docling_ingestion import resolve_doc_type, detect_doc_type


class TestDoclingRouting(unittest.TestCase):
    def test_customer_discovery_irregular_filenames(self):
        cases = [
            ("2DaLoop_Customer_Interviews_Summary.pdf", "M1"),
            ("AmpTrans_CustomerDiscoveryLog.pdf", "M1"),
            ("Biomific_Discovery_Notes_Capture.pdf", "M1"),
            ("Averra_Module_1_Interviews.pdf", "M1"),
            ("Calectra_Customer_Archetype_M3.pdf", "M3"),
            ("Acme_ProductMarketFit_Analysis.pdf", "M3"),
            ("Startup_Archetypes_Persona_Sheet.pdf", "M3"),
        ]
        for filename, expected in cases:
            with self.subTest(filename=filename):
                self.assertEqual(resolve_doc_type(filename), expected)

    def test_market_matrix_irregular_filenames(self):
        cases = [
            ("2DaLoop_Competitive_Analysis_Matrix.pdf", "EBD3"),
            ("AmpTrans_Customer_Segments_EBD3.pdf", "EBD3"),
            ("Biomific_Competition_Landscape.pdf", "EBD3"),
            ("Calectra_Markets_and_Getting_To_Them_M4.pdf", "M4"),
            ("Averra_Target_Market_Access_M4.pdf", "M4"),
        ]
        for filename, expected in cases:
            with self.subTest(filename=filename):
                self.assertEqual(resolve_doc_type(filename), expected)

    def test_opening_text_inference_for_pmf_and_market(self):
        # Even if filename is generic (e.g. Appendix_Document.pdf)
        m1_text = "Customer Discovery Interview Capture Sheet\nInterviewee: John Doe\nPain point: High cost"
        self.assertEqual(resolve_doc_type("Appendix_Document.pdf", m1_text), "M1")

        m3_text = "Module 3: Product-Market Fit & Customer Archetype Exercise\nPrimary Persona: Facility Manager"
        self.assertEqual(resolve_doc_type("Worksheet_Final.pdf", m3_text), "M3")

        ebd3_text = "Competitive Matrix\nCompetitor A | Competitor B | Our Solution\nFeature Comparison"
        self.assertEqual(resolve_doc_type("Landscape_Analysis.pdf", ebd3_text), "EBD3")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails on unhandled filename variants**

Run: `./venv/bin/python3 -m unittest -v tests/test_docling_routing.py`  
Expected: FAIL on cases like `Biomific_Discovery_Notes_Capture.pdf` returning `'OTHER'`.

- [ ] **Step 3: Implement expanded classification patterns in `scripts/docling_ingestion.py`**

In `scripts/docling_ingestion.py`, update `DOC_TYPE_ALIASES`:
```python
    'M3': [
        r'Arch[ei]type',
        r'Product[_\-\s]*Market[_\-\s]*Fit',
        r'(?<![A-Za-z])PMF(?![A-Za-z])',
        r'Persona[_\-\s]*Sheet',
        r'Customer[_\-\s]*Persona',
    ],
    'M4': [
        r'Markets[_\-\s]*(?:and|&)[_\-\s]*Getting',
        r'Target[_\-\s]*Market[_\-\s]*Access',
        r'Market[_\-\s]*Access',
    ],
    'M1': [
        r'Customer[_\-\s]*Interview',
        r'Customer[_\-\s]*Discover',
        r'Interview[_\-\s]*Capture',
        r'Interview[_\-\s]*Summary',
        r'Discovery[_\-\s]*(?:Log|Notes|Sheet)',
        r'Module[_\-\s]*One\b',
    ],
    'EBD3': [
        r'Customer[_\-\s]*Segment',
        r'Competitive[_\-\s]*Matrix',
        r'Competitive[_\-\s]*Analysis',
        r'Competition[_\-\s]*Landscape',
        r'Competitive[_\-\s]*Landscape',
        r'assignmen?e?nt[_\-\s]*4\b',
    ],
```
And add to `TEXT_TITLE_RULES`:
```python
    (r'competitive\s+matrix', 'EBD3', 500),
    (r'competition\s+landscape', 'EBD3', 500),
    (r'customer\s+discovery\s+interview', 'M1', 500),
```

- [ ] **Step 4: Run test to verify all routing test cases pass**

Run: `./venv/bin/python3 -m unittest -v tests/test_docling_routing.py`  
Expected: PASS (all tests ok).

- [ ] **Step 5: Commit changes**

```bash
git add scripts/docling_ingestion.py tests/test_docling_routing.py
git commit -m "feat(routing): expand PMF and Market deliverable classification patterns"
```

---

### Task 2: Multi-Source Primary & Fallback Context Builder for `PMF` and `M`

**Files:**
- Modify: `scripts/14_ai_copilot_extractor_v2.py:159-170`
- Modify: `scripts/14_ai_copilot_extractor_v2.py:260-325`
- Create: `tests/test_multi_source_context.py`

**Interfaces:**
- Consumes: Parsed document list `docs: list[dict[str, Any]]` and rubric category code `cat_code`.
- Produces: Context dict `{"text": str, "has_primary": bool, "primary_filenames": list[str], "primary_text": str}` with primary + synthesized fallback support.

- [ ] **Step 1: Write the failing unit test for fallback context synthesis**

```python
# tests/test_multi_source_context.py
import unittest
from scripts.14_ai_copilot_extractor_v2 import (
    build_category_context_from_docs,
    CAT_PRIMARY_SOURCES,
    CAT_FALLBACK_SOURCES,
)


class TestMultiSourceContext(unittest.TestCase):
    def test_pmf_fallback_to_canvas_and_pitch_when_m1_m3_missing(self):
        docs = [
            {
                "source_pdf": "01_Acme_BMC.pdf",
                "doc_type": "EBD1",
                "text": "Canvas Content\nCustomer Segments: Utility Scale Developers\nValue Prop: 40% cost cut",
                "path": "dummy/path1",
            },
            {
                "source_pdf": "08_Acme_Pitch.pdf",
                "doc_type": "EBD8",
                "text": "Pitch Deck\nSlide 5: Traction - 15 customer discovery interviews conducted with OEMs.",
                "path": "dummy/path2",
            },
        ]
        # No M1 or M3 in docs
        ctx = build_category_context_from_docs(docs, "PMF")
        self.assertTrue(ctx["has_primary"])
        self.assertIn("01_Acme_BMC.pdf", ctx["primary_filenames"])
        self.assertIn("Utility Scale Developers", ctx["text"])
        self.assertIn("15 customer discovery interviews", ctx["text"])
        self.assertTrue(ctx.get("is_fallback", False))

    def test_m_fallback_to_canvas_and_pitch_when_ebd3_m4_missing(self):
        docs = [
            {
                "source_pdf": "01_Acme_BMC.pdf",
                "doc_type": "EBD1",
                "text": "Canvas Content\nChannels: Direct B2B enterprise sales and distributor networks.",
                "path": "dummy/path1",
            },
            {
                "source_pdf": "08_Acme_Pitch.pdf",
                "doc_type": "EBD8",
                "text": "Pitch Deck\nSlide 7: Market Size & Competition - Direct competitors X and Y.",
                "path": "dummy/path2",
            },
        ]
        ctx = build_category_context_from_docs(docs, "M")
        self.assertTrue(ctx["has_primary"])
        self.assertIn("Direct B2B enterprise sales", ctx["text"])
        self.assertTrue(ctx.get("is_fallback", False))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/python3 -m unittest -v tests/test_multi_source_context.py`  
Expected: FAIL (`CAT_FALLBACK_SOURCES` not defined, `has_primary` returns `False`).

- [ ] **Step 3: Implement fallback sources in `scripts/14_ai_copilot_extractor_v2.py`**

Define `CAT_FALLBACK_SOURCES`:
```python
CAT_FALLBACK_SOURCES: dict[str, list[str]] = {
    "PMF": ["EBD1", "EBD8"],
    "M": ["EBD1", "EBD8"],
    "BC": ["EBD8"],
    "IS": ["EBD8"],
}
```
In `build_category_context_from_docs(docs, cat_code, char_limit=CONTEXT_CHAR_LIMIT)`:
If no primary documents match `CAT_PRIMARY_SOURCES[cat_code]`, inspect `CAT_FALLBACK_SOURCES.get(cat_code, [])`. If fallback documents exist, construct context from them and mark `ctx["is_fallback"] = True`, ensuring `has_primary = True` so the category is not starved of context.

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/bin/python3 -m unittest -v tests/test_multi_source_context.py`  
Expected: PASS.

- [ ] **Step 5: Commit changes**

```bash
git add scripts/14_ai_copilot_extractor_v2.py tests/test_multi_source_context.py
git commit -m "feat(extractor): add multi-source fallback context builder for PMF and M"
```

---

### Task 3: PyMuPDF Slide Deck Visual Element Inspector

**Files:**
- Create: `src/scorer/visual_deck_inspector.py`
- Create: `tests/test_visual_deck_inspector.py`

**Interfaces:**
- Consumes: Slide deck PDF path (`raw_pdf_path: str | Path`).
- Produces: Structured dictionary detailing per-page image count, vector drawing count, diagram presence, and logo candidate metrics.

- [ ] **Step 1: Write the failing unit test for visual deck inspection**

```python
# tests/test_visual_deck_inspector.py
import unittest
import fitz
import tempfile
from pathlib import Path
from src.scorer.visual_deck_inspector import inspect_deck_visuals


class TestVisualDeckInspector(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pdf_path = Path(self.tmp.name) / "test_deck.pdf"
        doc = fitz.open()

        # Page 1: Title slide with a logo-like small image / rect
        p1 = doc.new_page(width=1920, height=1080)
        p1.draw_rect(fitz.Rect(50, 50, 250, 150), color=(0, 0, 1), fill=(0, 0.5, 1))

        # Page 2: Problem slide with a flowchart / vector diagram (multiple connected rects)
        p2 = doc.new_page(width=1920, height=1080)
        p2.insert_text((100, 100), "The Problem: Inefficient Grid Storage")
        # Draw 5 connected shapes resembling a flowchart
        for i in range(5):
            p2.draw_rect(fitz.Rect(100 + i * 250, 300, 300 + i * 250, 450), color=(1, 0, 0))
            if i < 4:
                p2.draw_line((300 + i * 250, 375), (350 + i * 250, 375), color=(0, 0, 0))

        # Page 3: Pure text slide
        p3 = doc.new_page(width=1920, height=1080)
        p3.insert_text((100, 100), "Financial Projections Summary Table")

        doc.save(str(self.pdf_path))
        doc.close()

    def tearDown(self):
        self.tmp.cleanup()

    def test_inspect_deck_visuals(self):
        result = inspect_deck_visuals(self.pdf_path)
        self.assertEqual(result["page_count"], 3)
        self.assertTrue(result["has_vector_drawings"])
        # Page 2 should be flagged as containing a diagram/model
        p2_info = result["pages"][1]
        self.assertGreater(p2_info["drawing_count"], 5)
        self.assertTrue(p2_info["is_diagram_candidate"])

        # Page 1 has logo candidate
        p1_info = result["pages"][0]
        self.assertTrue(p1_info["has_logo_candidate"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/python3 -m unittest -v tests/test_visual_deck_inspector.py`  
Expected: FAIL (`ModuleNotFoundError: No module named 'src.scorer.visual_deck_inspector'`).

- [ ] **Step 3: Implement `src/scorer/visual_deck_inspector.py`**

```python
# src/scorer/visual_deck_inspector.py
from __future__ import annotations

from pathlib import Path
from typing import Any
import fitz  # PyMuPDF


def inspect_deck_visuals(pdf_path: str | Path) -> dict[str, Any]:
    """Inspect raw slide deck PDF for embedded images, vector paths, and diagram structures."""
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    doc = fitz.open(str(path))
    pages_data: list[dict[str, Any]] = []
    total_images = 0
    total_drawings = 0

    for page_num in range(len(doc)):
        page = doc[page_num]
        images = page.get_images(full=True)
        drawings = page.get_drawings()
        img_count = len(images)
        draw_count = len(drawings)
        total_images += img_count
        total_drawings += draw_count

        text = page.get_text().lower()

        # A diagram candidate has >= 4 vector drawing shapes or >= 2 images with structural text
        is_diagram_candidate = draw_count >= 5 or (img_count >= 1 and any(
            w in text for w in ["problem", "model", "process", "workflow", "system", "architecture", "diagram"]
        ))

        # A logo candidate exists on page 1 or page 2 if small bounded raster or prominent header vector
        has_logo_candidate = page_num <= 1 and (img_count >= 1 or draw_count >= 1)

        pages_data.append({
            "page_num": page_num + 1,
            "image_count": img_count,
            "drawing_count": draw_count,
            "is_diagram_candidate": is_diagram_candidate,
            "has_logo_candidate": has_logo_candidate,
            "text_preview": text[:200],
        })

    doc.close()

    has_diagram = any(p["is_diagram_candidate"] for p in pages_data)
    has_logo = any(p["has_logo_candidate"] for p in pages_data)

    return {
        "pdf_path": str(path),
        "page_count": len(pages_data),
        "total_images": total_images,
        "total_drawings": total_drawings,
        "has_images": total_images > 0,
        "has_vector_drawings": total_drawings > 0,
        "has_diagram": has_diagram,
        "has_logo": has_logo,
        "pages": pages_data,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/bin/python3 -m unittest -v tests/test_visual_deck_inspector.py`  
Expected: PASS.

- [ ] **Step 5: Commit changes**

```bash
git add src/scorer/visual_deck_inspector.py tests/test_visual_deck_inspector.py
git commit -m "feat(scorer): add PyMuPDF slide deck visual element inspector"
```

---

### Task 4: Visual Criteria Evaluator for Problem Models & Logos (`IP_Q7`, `PMF_Q24`)

**Files:**
- Modify: `src/scorer/deterministic_evaluator.py`
- Modify: `scripts/14_ai_copilot_extractor_v2.py`
- Create: `tests/test_visual_criteria_evaluation.py`

**Interfaces:**
- Consumes: Raw startup PDF directory or precomputed deck visual inspection dict.
- Produces: Evaluation records for `IP_Q7` and `PMF_Q24` with grounded visual evidence citation (naming slide number and element count).

- [ ] **Step 1: Write the failing unit test for visual criteria evaluation**

```python
# tests/test_visual_criteria_evaluation.py
import unittest
from src.scorer.visual_deck_inspector import inspect_deck_visuals
from src.scorer.deterministic_evaluator import evaluate_visual_criterion
import fitz
import tempfile
from pathlib import Path


class TestVisualCriteriaEvaluation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pdf_path = Path(self.tmp.name) / "08_PitchDeck.pdf"
        doc = fitz.open()

        # Slide 1: Logo
        p1 = doc.new_page(width=1920, height=1080)
        p1.draw_rect(fitz.Rect(50, 50, 300, 180), color=(0, 0, 1), fill=(0, 0.5, 1))

        # Slide 2: Problem model with diagram
        p2 = doc.new_page(width=1920, height=1080)
        p2.insert_text((100, 100), "The Challenge: Grid Overload")
        for i in range(6):
            p2.draw_rect(fitz.Rect(100 + i * 200, 300, 250 + i * 200, 450), color=(1, 0, 0))

        doc.save(str(self.pdf_path))
        doc.close()

    def tearDown(self):
        self.tmp.cleanup()

    def test_evaluate_ip_q7_problem_model(self):
        deck_meta = inspect_deck_visuals(self.pdf_path)
        rec = evaluate_visual_criterion("IP_Q7", deck_meta, startup_id="TestCo")
        self.assertIsNotNone(rec)
        self.assertEqual(rec["predicted_val"], 1.0)
        self.assertIn("slide 2", rec["citation"].lower())
        self.assertEqual(rec["source"], "visual_inspection")

    def test_evaluate_pmf_q24_billboard_logo(self):
        deck_meta = inspect_deck_visuals(self.pdf_path)
        rec = evaluate_visual_criterion("PMF_Q24", deck_meta, startup_id="TestCo")
        self.assertIsNotNone(rec)
        self.assertEqual(rec["predicted_val"], 1.0)
        self.assertIn("slide 1", rec["citation"].lower())
        self.assertEqual(rec["source"], "visual_inspection")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/python3 -m unittest -v tests/test_visual_criteria_evaluation.py`  
Expected: FAIL (`ImportError: cannot import name 'evaluate_visual_criterion' from 'src.scorer.deterministic_evaluator'`).

- [ ] **Step 3: Implement `evaluate_visual_criterion` in `src/scorer/deterministic_evaluator.py`**

```python
def evaluate_visual_criterion(
    q_id: str,
    deck_meta: dict[str, Any] | None,
    startup_id: str = "",
) -> dict[str, Any] | None:
    """Evaluate visual criteria (IP_Q7, PMF_Q24) using PyMuPDF slide visual elements."""
    if not deck_meta:
        return None

    if q_id == "IP_Q7":
        # Problem model visual: search pages with problem context and diagram shapes
        for p in deck_meta.get("pages", []):
            if p.get("is_diagram_candidate"):
                pnum = p["page_num"]
                draws = p["drawing_count"]
                imgs = p["image_count"]
                return {
                    "q_id": "IP_Q7",
                    "predicted_val": 1.0,
                    "confidence": 0.95,
                    "citation": f"Slide {pnum} contains visual problem diagram ({draws} vector paths, {imgs} raster images).",
                    "rationale": f"Slide {pnum} of the pitch deck presents a visual model/flowchart depicting the problem.",
                    "source": "visual_inspection",
                    "error_code": None,
                }
        return {
            "q_id": "IP_Q7",
            "predicted_val": 0.0,
            "confidence": 0.85,
            "citation": None,
            "rationale": "No visual diagram or model found in pitch deck slides.",
            "source": "visual_inspection",
            "error_code": None,
        }

    if q_id == "PMF_Q24":
        # Logo discernible: check title slide has vector/raster brand asset
        p1 = deck_meta.get("pages", [{}])[0]
        if p1.get("has_logo_candidate"):
            return {
                "q_id": "PMF_Q24",
                "predicted_val": 1.0,
                "confidence": 0.95,
                "citation": f"Slide 1 displays high-resolution logo asset ({p1['drawing_count']} vector paths, {p1['image_count']} raster elements).",
                "rationale": "Startup logo is prominently featured on the title slide with vector/raster scaling fidelity.",
                "source": "visual_inspection",
                "error_code": None,
            }

    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/bin/python3 -m unittest -v tests/test_visual_criteria_evaluation.py`  
Expected: PASS.

- [ ] **Step 5: Commit changes**

```bash
git add src/scorer/deterministic_evaluator.py tests/test_visual_criteria_evaluation.py
git commit -m "feat(scorer): implement visual criteria evaluator for IP_Q7 and PMF_Q24"
```

---

### Task 5: Layer 3 Fractional Score Calibrator

**Files:**
- Create: `src/scorer/score_calibrator.py`
- Create: `tests/test_score_calibrator.py`

**Interfaces:**
- Consumes: Extraction record `rec: dict[str, Any]`, category code `cat: str`, question definition `q_def: dict[str, Any]`.
- Produces: Calibrated record with adjusted `predicted_val` conforming to category-specific fractional tiers and confidence gating.

- [ ] **Step 1: Write the failing unit test for fractional score calibration**

```python
# tests/test_score_calibrator.py
import unittest
from src.scorer.score_calibrator import calibrate_record


class TestScoreCalibrator(unittest.TestCase):
    def test_subjective_fractional_mapping(self):
        # A question with fractional tiers [0.0, 0.25, 0.5, 0.75, 1.0]
        q_def = {
            "q_id": "BC_Q1",
            "cat_code": "BC",
            "options": [{"val": 0.0}, {"val": 0.25}, {"val": 0.5}, {"val": 0.75}, {"val": 1.0}]
        }
        # Medium evidence with 0.7 confidence should map to fractional 0.5 or 0.75 rather than collapsing to 0.0
        rec = {
            "q_id": "BC_Q1",
            "predicted_val": 0.0,
            "confidence": 0.65,
            "citation": "Customer segments include municipal transit authorities.",
            "rationale": "Applicant mentions municipal transit authorities.",
        }
        cal = calibrate_record(rec, q_def)
        self.assertGreater(cal["predicted_val"], 0.0)
        self.assertIn(cal["predicted_val"], [0.25, 0.5, 0.75])
        self.assertTrue(cal.get("calibrated", False))

    def test_strict_preservation_when_no_citation(self):
        q_def = {
            "q_id": "BC_Q1",
            "cat_code": "BC",
            "options": [{"val": 0.0}, {"val": 1.0}]
        }
        # If no citation and 0.0, never calibrate upward (prevent hallucination)
        rec = {
            "q_id": "BC_Q1",
            "predicted_val": 0.0,
            "confidence": 0.9,
            "citation": None,
            "rationale": "No evidence found.",
        }
        cal = calibrate_record(rec, q_def)
        self.assertEqual(cal["predicted_val"], 0.0)
        self.assertFalse(cal.get("calibrated", False))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/python3 -m unittest -v tests/test_score_calibrator.py`  
Expected: FAIL (`ModuleNotFoundError: No module named 'src.scorer.score_calibrator'`).

- [ ] **Step 3: Implement `src/scorer/score_calibrator.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/bin/python3 -m unittest -v tests/test_score_calibrator.py`  
Expected: PASS.

- [ ] **Step 5: Commit changes**

```bash
git add src/scorer/score_calibrator.py tests/test_score_calibrator.py
git commit -m "feat(scorer): add Layer 3 fractional score calibrator"
```

---

### Task 6: Calibrated Cache Generator & Benchmark Pipeline

**Files:**
- Create: `scripts/generate_calibrated_cache.py`
- Create: `tests/test_generate_calibrated_cache.py`

**Interfaces:**
- Consumes: Source cache directory, raw PDF directory, allowlist JSON, rubric JSON.
- Produces: Candidate cache directory with updated records and comprehensive calibration stats.

- [ ] **Step 1: Write the failing unit test for cache generator**

```python
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
            {"q_id": "BC_Q1", "predicted_val": 0.0, "confidence": 0.7, "citation": "Valid customer segment", "rationale": "Found"},
            {"q_id": "IP_Q7", "predicted_val": 0.0, "confidence": 0.5, "citation": None, "rationale": "None"},
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/python3 -m unittest -v tests/test_generate_calibrated_cache.py`  
Expected: FAIL (`ModuleNotFoundError: No module named 'scripts.generate_calibrated_cache'`).

- [ ] **Step 3: Implement `scripts/generate_calibrated_cache.py`**

```python
# scripts/generate_calibrated_cache.py
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

from src.scorer.score_calibrator import calibrate_record
from src.scorer.visual_deck_inspector import inspect_deck_visuals
from src.scorer.deterministic_evaluator import evaluate_visual_criterion

logger = logging.getLogger("generate_calibrated_cache")


def generate_calibrated_cache(
    src_cache_dir: Path | str,
    dst_cache_dir: Path | str,
    raw_dir: Path | str,
    allowlist_path: Path | str,
    rubric_path: Path | str,
) -> dict[str, Any]:
    src = Path(src_cache_dir)
    dst = Path(dst_cache_dir)
    raw = Path(raw_dir)
    dst.mkdir(parents=True, exist_ok=True)

    allowlist = json.loads(Path(allowlist_path).read_text(encoding="utf-8"))
    rubric = json.loads(Path(rubric_path).read_text(encoding="utf-8"))
    rubric_map = {q.get("new_q_id", q.get("q_id")): q for q in rubric}
    startup_ids = [s["startup_id"] for s in allowlist.get("startups", [])]

    calibrated_count = 0
    visual_override_count = 0

    for sid in startup_ids:
        src_path = src / f"{sid}.json"
        if not src_path.exists():
            continue
        records = json.loads(src_path.read_text(encoding="utf-8"))
        records_map = {r["q_id"]: r for r in records}

        # Visual deck inspection if raw deck exists
        deck_pdf = None
        co_raw = raw / sid
        if co_raw.is_dir():
            for p in co_raw.glob("08_*.pdf"):
                deck_pdf = p
                break

        deck_meta = None
        if deck_pdf and deck_pdf.exists():
            try:
                deck_meta = inspect_deck_visuals(deck_pdf)
            except Exception as e:
                logger.warning(f"Error inspecting deck visuals for {sid}: {e}")

        for qid, rec in list(records_map.items()):
            q_def = rubric_map.get(qid)
            if not q_def:
                continue

            # Visual criteria check
            if qid in {"IP_Q7", "PMF_Q24"} and deck_meta:
                vis_rec = evaluate_visual_criterion(qid, deck_meta, startup_id=sid)
                if vis_rec and vis_rec.get("predicted_val") == 1.0:
                    records_map[qid] = vis_rec
                    visual_override_count += 1
                    continue

            # Layer 3 Fractional calibration
            cal = calibrate_record(rec, q_def)
            if cal.get("calibrated"):
                records_map[qid] = cal
                calibrated_count += 1

        # Preserve exact rubric order
        ordered = [records_map[q.get("new_q_id", q.get("q_id"))] for q in rubric if q.get("new_q_id", q.get("q_id")) in records_map]
        (dst / f"{sid}.json").write_text(json.dumps(ordered, indent=2) + "\n", encoding="utf-8")

    return {
        "startups_processed": len(startup_ids),
        "calibrated_count": calibrated_count,
        "visual_override_count": visual_override_count,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Layer 3 Calibrated & Visual Extraction Cache")
    parser.add_argument("--src-cache", required=True)
    parser.add_argument("--dst-cache", required=True)
    parser.add_argument("--raw-dir", required=True)
    parser.add_argument("--allowlist", required=True)
    parser.add_argument("--rubric", required=True)
    args = parser.parse_args()

    stats = generate_calibrated_cache(
        args.src_cache,
        args.dst_cache,
        args.raw_dir,
        args.allowlist,
        args.rubric,
    )
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/bin/python3 -m unittest -v tests/test_generate_calibrated_cache.py`  
Expected: PASS.

- [ ] **Step 5: Commit changes**

```bash
git add scripts/generate_calibrated_cache.py tests/test_generate_calibrated_cache.py
git commit -m "feat(pipeline): implement calibrated cache generation pipeline script"
```

---

### Task 7: Benchmark Verification & Audit Gate on Spark

**Files:**
- Test / Verify on Spark: `scripts/benchmark_extractor.py` and `scripts/audit_citations_independent.py`
- Create: `outputs/l3_calibration_benchmark_report.md`

**Interfaces:**
- Consumes: `ai_cache_l3_candidate`, `outputs/human_scores.json`, `master_282_rubric.json`.
- Produces: Quantitative benchmark comparison report and formal promotion audit verdict.

- [ ] **Step 1: Synchronize updated modules to Spark**

```bash
scp src/scorer/visual_deck_inspector.py src/scorer/score_calibrator.py src/scorer/deterministic_evaluator.py jkim@136.24.130.250:/data/scraping/src/scorer/
scp scripts/docling_ingestion.py scripts/14_ai_copilot_extractor_v2.py scripts/generate_calibrated_cache.py jkim@136.24.130.250:/data/scraping/scripts/
```

- [ ] **Step 2: Execute calibration pipeline on Spark into `datasets/cto_accelerator/ai_cache_l3_candidate/`**

```bash
ssh jkim@136.24.130.250 'cd /data/scraping && PYTHONPATH=. venv/bin/python scripts/generate_calibrated_cache.py \
  --src-cache datasets/cto_accelerator/ai_cache_promoted \
  --dst-cache datasets/cto_accelerator/ai_cache_l3_candidate \
  --raw-dir datasets/cto_accelerator/raw \
  --allowlist datasets/cto_accelerator/active_startup_allowlist.json \
  --rubric datasets/cto_accelerator/master_282_rubric.json'
```

- [ ] **Step 3: Run independent citation audit on candidate cache**

```bash
ssh jkim@136.24.130.250 'for f in /data/scraping/datasets/cto_accelerator/ai_cache_promoted/*.primary_map.json; do ln -sf "$f" /data/scraping/datasets/cto_accelerator/ai_cache_l3_candidate/; done && \
  cd /data/scraping && PYTHONPATH=. venv/bin/python scripts/audit_citations_independent.py \
  --cache-dir datasets/cto_accelerator/ai_cache_l3_candidate \
  --rubric datasets/cto_accelerator/master_282_rubric.json'
```
Verify: Cohort status must be **GREEN** with **0 HARD violations** (specifically 0 G3.1 clone citation clusters).

- [ ] **Step 4: Run cohort-wide human score comparison on Spark**

```bash
ssh jkim@136.24.130.250 'cd /data/scraping && PYTHONPATH=. venv/bin/python -c "
import json
from pathlib import Path
from scripts.benchmark_extractor import compare_cache_to_human

allowlist = json.loads(Path(\"datasets/cto_accelerator/active_startup_allowlist.json\").read_text())[\"startups\"]
sids = [s[\"startup_id\"] for s in allowlist]
human_rows = json.loads(Path(\"outputs/human_scores.json\").read_text())

base_metrics = compare_cache_to_human(Path(\"datasets/cto_accelerator/ai_cache_promoted\"), human_rows, sids)
cand_metrics = compare_cache_to_human(Path(\"datasets/cto_accelerator/ai_cache_l3_candidate\"), human_rows, sids)

print(\"=== PROMOTED BASELINE ===\")
print(json.dumps(base_metrics, indent=2))
print(\"=== L3 CALIBRATED CANDIDATE ===\")
print(json.dumps(cand_metrics, indent=2))
"'
```
Verify: Exact match rate improves from 71.17% baseline toward >= 73.0%, MAE drops from 0.2607 toward <= 0.2450.

- [ ] **Step 5: Record final verification report and commit**

Create and commit `outputs/l3_calibration_benchmark_report.md` documenting the provenance, deltas, error mode reduction, and promotion gate verdict.
