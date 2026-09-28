"""The cleaned tree must fail closed, and template lines must come out."""
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

from scripts.clean_parsed_documents_v2 import clean_markdown_text
from scripts.docling_ingestion import UNIVERSAL_SCAFFOLDING_PATTERNS
from scripts.verify_data_integrity import DEFAULT_PARSED_DIR, audit

ROOT = Path(__file__).resolve().parents[1]


def load_numbered(name):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestScaffoldClean(unittest.TestCase):
    def test_template_deliverable_line_is_removed(self):
        source = "\n".join([
            "## Essential Business Deliverable #2: Impact Statement",
            "2. Key Deliverable: Write your Impact Statement as part of your Essential Business Deliverable #2.",
            "The plant cuts water use by 40 percent.",
        ])
        cleaned, _, _ = clean_markdown_text(source, "OTHER", {})
        self.assertNotIn("Essential Business Deliverable", cleaned)
        self.assertIn("water use by 40 percent", cleaned)


class TestIntegrityGate(unittest.TestCase):
    def write_tree(self, root, name, text):
        path = os.path.join(root, "Some_Startup", "converted", name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def foregger(self, root, text):
        path = os.path.join(
            root,
            "Foregger_Energy_Solutions",
            "converted",
            "11_FES_CTO_Slide_Deck.pdf.md",
        )
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def test_pass_requires_text_and_no_template_lines(self):
        with tempfile.TemporaryDirectory() as root:
            self.foregger(root, "slide " * 800)
            self.write_tree(root, "02_EBD1_Canvas.pdf.md", "Key partners and revenue streams are listed here in full.")
            self.assertEqual(audit(root), [])

    def test_empty_primary_fails(self):
        with tempfile.TemporaryDirectory() as root:
            self.foregger(root, "slide " * 800)
            self.write_tree(root, "14_EBD5_Three-Year_Financial_Projection.pdf.md", "<!-- Page 1 -->")
            failures = audit(root)
            self.assertEqual(len(failures), 1)
            self.assertIn("primary deliverables", failures[0])

    def test_template_phrase_fails(self):
        with tempfile.TemporaryDirectory() as root:
            self.foregger(root, "slide " * 800)
            self.write_tree(
                root,
                "notes.pdf.md",
                "Key Deliverable: see your Essential Business Deliverable #2.",
            )
            failures = audit(root)
            self.assertEqual(len(failures), 1)
            self.assertIn("template scaffolding", failures[0])

    def test_missing_directory_fails(self):
        failures = audit(os.path.join(tempfile.gettempdir(), "cto-missing-parsed-clean"))
        self.assertEqual(len(failures), 1)
        self.assertIn("missing", failures[0])


class TestV4Paths(unittest.TestCase):
    def test_readers_use_the_v4_trees(self):
        self.assertTrue(DEFAULT_PARSED_DIR.rstrip("/").endswith("parsed_clean_v4"))
        ground = load_numbered("13_ground_citations.py")
        self.assertTrue(ground.DEFAULT_CACHE_DIR.endswith("ai_cache_v4_shadow"))
        self.assertTrue(ground.DEFAULT_PARSED_DIR.endswith("parsed_clean_v4"))
        with self.assertRaises(SystemExit):
            ground.refuse_production_path("/data/scraping/datasets/cto_accelerator/ai_cache_v3_strict", ground.PRODUCTION_CACHE)
        with self.assertRaises(SystemExit):
            ground.refuse_production_path("/data/scraping/datasets/cto_accelerator/parsed_clean", ground.PREVIOUS_PARSED)
        ground.refuse_production_path("/data/scraping/datasets/cto_accelerator/parsed_clean_v4", ground.PREVIOUS_PARSED)
        extractor = load_numbered("14_ai_copilot_extractor_v2.py")
        self.assertTrue(extractor.REMOTE_DOCLING_DIR.endswith("docling_clean_v4"))
        self.assertTrue(extractor.default_docling_dir().endswith("docling_clean_v4"))
        verifier = load_numbered("11_independent_verifier.py")
        self.assertTrue(verifier.IndependentVerifier.__init__.__defaults__[0].endswith("parsed_clean_v4"))
        joined = "\n".join(UNIVERSAL_SCAFFOLDING_PATTERNS)
        self.assertIn("essential\\s+business\\s+deliverable", joined)
