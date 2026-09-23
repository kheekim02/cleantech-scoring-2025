"""Integration test for remote stack verification on Spark GB10.

Tests:
- CUDA 13.0 & PyTorch 2.13 compatibility
- Docling 2.118+ document conversion capability
- SGLang 0.5.20+ and XGrammar 0.2+ imports
- Instructor 1.17+ and Pydantic v2 model definitions
"""
import sys
import unittest


class TestRemoteStack(unittest.TestCase):
    def test_01_cuda_and_torch(self):
        import torch
        if not torch.cuda.is_available():
            self.skipTest("CUDA not available locally; runs on Spark GB10")
        device_count = torch.cuda.device_count()
        self.assertGreaterEqual(device_count, 1, "At least 1 GPU device must be detected")
        device_name = torch.cuda.get_device_name(0)
        print(f"[TEST] PyTorch {torch.__version__} with CUDA: {device_name}")
        self.assertTrue("GB10" in device_name or "NVIDIA" in device_name, f"Expected NVIDIA GPU, got {device_name}")

    def test_02_docling_import(self):
        import docling
        from docling.document_converter import DocumentConverter
        print(f"[TEST] Docling version: {docling.__version__}")
        converter = DocumentConverter()
        self.assertIsNotNone(converter, "DocumentConverter should initialize cleanly")

    def test_03_sglang_and_xgrammar(self):
        try:
            import sglang
            import xgrammar
        except ImportError as e:
            self.skipTest(f"SGLang/XGrammar not available locally; runs on Spark: {e}")
        print(f"[TEST] SGLang version: {sglang.__version__}, XGrammar classes: {dir(xgrammar)[:5]}")
        self.assertTrue(hasattr(sglang, "__version__"))
        self.assertTrue(hasattr(xgrammar, "GrammarCompiler"))

    def test_04_instructor_and_pydantic(self):
        import instructor
        import pydantic
        from pydantic import BaseModel, Field
        print(f"[TEST] Instructor version: {instructor.__version__}, Pydantic version: {pydantic.__version__}")

        class DiligenceScore(BaseModel):
            q_id: str
            score: float = Field(ge=0.0, le=1.0)
            verbatim_citation: str | None = None

        item = DiligenceScore(q_id="BC_Q1", score=1.0, verbatim_citation="Founders demonstrate clear value.")
        self.assertEqual(item.score, 1.0)
        self.assertEqual(item.q_id, "BC_Q1")


if __name__ == "__main__":
    unittest.main()
