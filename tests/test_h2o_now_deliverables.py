"""Unit tests verifying full deliverable representation for H2O Now and the cohort."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_PATH = ROOT / "scripts" / "archive" / "analysis_and_audits" / "db_snapshot_pre_ai.json"


class TestH2ONowDeliverables(unittest.TestCase):
    """Verify H2O Now and cohort deliverable representation on the interface."""

    def setUp(self):
        self.assertTrue(SNAPSHOT_PATH.is_file(), "db_snapshot_pre_ai.json must exist")
        self.snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))

    def test_01_h2o_now_has_all_14_files_in_snapshot(self):
        """Verify H2O Now has exactly 14 unique deliverable files in the master snapshot."""
        h2o_data = self.snapshot.get("H2O_Now")
        self.assertIsNotNone(h2o_data, "H2O_Now must be present in snapshot")
        
        all_pdfs = []
        if isinstance(h2o_data, list):
            for sec in h2o_data:
                all_pdfs.extend(sec.get("pdfs", []))
        elif isinstance(h2o_data, dict):
            for sec in h2o_data.get("document", {}).get("sections", []):
                all_pdfs.extend(sec.get("pdfs", []))
                
        unique_urls = {p["url"] for p in all_pdfs}
        self.assertEqual(len(unique_urls), 14, f"H2O Now must have 14 unique files, found {len(unique_urls)}")

    def test_02_h2o_now_specific_files_exist(self):
        """Verify the 5 previously unrepresented files exist for H2O Now."""
        expected_files = [
            "03_Assignment_2.pdf",
            "04_assignment_2_1.pdf",
            "05_cleantech_assignment_3.pdf",
            "06_Adobe_20Scan_20Jun_2027_2C_202025.pdf",
            "07_cleantech_assignmenent_4.pdf",
        ]
        h2o_data = self.snapshot.get("H2O_Now")
        all_urls = [p["url"] for sec in h2o_data for p in sec.get("pdfs", [])]
        for expected in expected_files:
            found = any(expected in u for u in all_urls)
            self.assertTrue(found, f"Expected deliverable {expected} not found in H2O Now snapshot")

    def test_03_database_h2o_now_has_all_14_files(self):
        """Verify H2O Now in startup_extractions table has all 14 unique files."""
        import os, psycopg2
        from dotenv import load_dotenv
        load_dotenv()
        dsn = os.environ.get("DATABASE_URL", "").split("?")[0]
        if not dsn:
            raise unittest.SkipTest("DATABASE_URL not set")
        conn = psycopg2.connect(dsn)
        cur = conn.cursor()
        cur.execute("SELECT payload FROM startup_extractions WHERE startup_id = 'H2O_Now'")
        row = cur.fetchone()
        conn.close()
        self.assertIsNotNone(row, "H2O_Now must exist in startup_extractions")
        payload = row[0]
        sections = payload.get("document", {}).get("sections", [])
        all_urls = {p["url"] for sec in sections for p in sec.get("pdfs", [])}
        self.assertEqual(len(all_urls), 14, f"H2O Now in database must have all 14 files, currently has {len(all_urls)}")

    def test_04_database_h2o_now_category_coverage(self):
        """Verify H2O Now has deliverables mapped to all 10 categories including ES and M."""
        import os, psycopg2
        from dotenv import load_dotenv
        load_dotenv()
        dsn = os.environ.get("DATABASE_URL", "").split("?")[0]
        if not dsn:
            raise unittest.SkipTest("DATABASE_URL not set")
        conn = psycopg2.connect(dsn)
        cur = conn.cursor()
        cur.execute("SELECT payload FROM startup_extractions WHERE startup_id = 'H2O_Now'")
        row = cur.fetchone()
        conn.close()
        payload = row[0]
        sections = payload.get("document", {}).get("sections", [])
        cat_map = {sec.get("cat_code"): [p["url"] for p in sec.get("pdfs", [])] for sec in sections}
        
        # Check all 10 categories
        for cat in ['BC', 'ES', 'F', 'IP', 'IS', 'L', 'M', 'PMF', 'T', 'TP']:
            self.assertIn(cat, cat_map, f"Category {cat} must be present in H2O Now sections")
            self.assertGreater(len(cat_map[cat]), 0, f"Category {cat} must have at least one deliverable")
            
        # Verify specific assignments
        es_urls = " ".join(cat_map.get("ES", []))
        self.assertIn("03_Assignment_2.pdf", es_urls)
        self.assertIn("04_assignment_2_1.pdf", es_urls)
        
        m_urls = " ".join(cat_map.get("M", []))
        self.assertIn("06_Adobe_20Scan", m_urls)
        self.assertIn("07_cleantech_assignmenent_4.pdf", m_urls)

    def test_05_cohort_zero_dropped_files(self):
        """Verify across all 92 startups in the database, zero snapshot deliverable files are missing."""
        import os, psycopg2
        from dotenv import load_dotenv
        load_dotenv()
        dsn = os.environ.get("DATABASE_URL", "").split("?")[0]
        if not dsn:
            raise unittest.SkipTest("DATABASE_URL not set")
        conn = psycopg2.connect(dsn)
        cur = conn.cursor()
        cur.execute("SELECT startup_id, payload FROM startup_extractions")
        rows = cur.fetchall()
        conn.close()
        
        missing_by_startup = {}
        for sid, payload in rows:
            if sid not in self.snapshot:
                continue
            sections = payload.get("document", {}).get("sections", [])
            db_urls = {p["url"] for sec in sections for p in sec.get("pdfs", [])}
            
            sdata = self.snapshot[sid]
            snap_pdfs = []
            if isinstance(sdata, list):
                for sec in sdata:
                    snap_pdfs.extend(sec.get("pdfs", []))
            elif isinstance(sdata, dict):
                for sec in sdata.get("document", {}).get("sections", []):
                    snap_pdfs.extend(sec.get("pdfs", []))
            snap_urls = {p["url"] for p in snap_pdfs}
            
            dropped = snap_urls - db_urls
            if dropped:
                missing_by_startup[sid] = len(dropped)
                
        self.assertEqual(len(missing_by_startup), 0, f"{len(missing_by_startup)} startups have missing deliverable files: {missing_by_startup}")


if __name__ == "__main__":
    unittest.main()
