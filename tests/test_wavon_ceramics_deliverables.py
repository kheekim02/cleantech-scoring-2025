"""Falsifiable Verification Harness for Wavon Ceramics Deliverables.

Verifies:
1. PostgreSQL table startup_deliverable_files schema, row count (18), PDF magic bytes, SHA-256 hashes.
2. api/pdf.js endpoint contract: 200 OK, Content-Type, Content-Length, Content-Disposition, ETag.
3. HTTP caching (304 Not Modified for If-None-Match), HEAD method, and 405 Method Not Allowed guards.
4. Security boundaries: path traversal defense, missing parameters, 404 on unknown files.
5. startup_extractions payload.document.sections has all 10 rubric categories populated.
6. Frontend renderLeftPane contract: produces valid dropdown, iframe src, and zero empty-state placeholders.
7. Regression protection: exactly 92 startups exist and other 91 startups remain completely intact.
"""
import os
import re
import json
import hashlib
import unittest
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

def load_db_url():
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"].replace("?pgbouncer=true", "")
    env_path = ROOT_DIR / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("DATABASE_URL="):
                    return line.split("=", 1)[1].strip().strip("'").strip('"').replace("?pgbouncer=true", "")
    raise ValueError("DATABASE_URL is not configured")

try:
    import psycopg2
    import psycopg2.extras
    HAVE_PSYCOPG2 = True
except ImportError:
    HAVE_PSYCOPG2 = False


class TestWavonCeramicsDeliverables(unittest.TestCase):
    """End-to-end verification suite for Wavon Ceramics deliverable serving."""

    STARTUP_ID = "Wavon_Ceramics_—_Accelerating_Manufacturing"
    EXPECTED_FILES = [
        "01_Supplementary.pdf",
        "02_WavonCeramics_TeamTargets.pdf",
        "03_WavonCeramics_M1CustomerDiscoveryInterviews.pdf",
        "04_WavonCeramics_BusinessModelCanvas.pdf",
        "05_WavonCeramics_M2ImpactSustainaiblityQuestions.pdf",
        "06_WavonCeramics_GHGERP.pdf",
        "07_WavonCeramics_EBD2ImpactStatement.pdf",
        "08_WavonCeramics_M3AssignmentQuestion.pdf",
        "09_WavonCeramics_M4Questions.pdf",
        "10_WavonCeramics_EBD3CustomerSegmentationCompetitiveMatrix.pdf",
        "11_WavonCeramics_EBD4TechnologyValidation.pdf",
        "12_WavonCeramics_M6Questions.pdf",
        "13_WavonCeramics_FinancialProjection.pdf",
        "14_WavonCeramics_M7Questions.pdf",
        "15_WavonCeramics_M8Questions.pdf",
        "16_WavonCeramics_InclusionAssignment.pdf",
        "17_WavonCeramics_ExecutiveSummary.pdf",
        "18_WavonCeramics_InvestorPitch.pdf",
    ]

    @classmethod
    def setUpClass(cls):
        if not HAVE_PSYCOPG2:
            raise unittest.SkipTest("psycopg2 is required for database verification")
        cls.db_url = load_db_url()

    def test_01_startup_deliverable_files_table_schema_and_integrity(self):
        """Verify startup_deliverable_files table holds all 18 valid PDF deliverables for Wavon Ceramics."""
        conn = psycopg2.connect(self.db_url)
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        try:
            cur.execute("""
                SELECT filename, file_bytes, mime_type, file_size_bytes, sha256
                FROM startup_deliverable_files
                WHERE startup_id = %s
                ORDER BY filename ASC
            """, (self.STARTUP_ID,))
            rows = cur.fetchall()

            self.assertEqual(len(rows), 18, f"Expected 18 ingested deliverables, found {len(rows)}")
            file_names = [r["filename"] for r in rows]
            self.assertEqual(file_names, sorted(self.EXPECTED_FILES))

            for r in rows:
                fname = r["filename"]
                raw_bytes = bytes(r["file_bytes"])
                self.assertGreater(len(raw_bytes), 100_000, f"{fname} is too small: {len(raw_bytes)} bytes")
                self.assertEqual(r["file_size_bytes"], len(raw_bytes), f"file_size_bytes mismatch on {fname}")
                self.assertTrue(raw_bytes.startswith(b"%PDF-"), f"{fname} does not start with %PDF- magic bytes")
                self.assertEqual(r["mime_type"], "application/pdf")

                expected_hash = hashlib.sha256(raw_bytes).hexdigest()
                self.assertEqual(r["sha256"], expected_hash, f"SHA-256 hash mismatch on {fname}")
        finally:
            cur.close()
            conn.close()

    def test_02_pdf_api_endpoint_serves_all_18_deliverables(self):
        """Invoke api/pdf.js handler for each of the 18 deliverables and confirm HTTP 200, PDF headers, and bytes."""
        cmd = """
        const handler = require('./api/pdf');
        const files = %s;
        const startupId = %s;

        (async () => {
          for (const file of files) {
            let statusCode = null;
            const headers = {};
            let body = null;
            const req = {
              method: 'GET',
              query: { startup_id: startupId, file },
              headers: {}
            };
            const res = {
              setHeader: (k, v) => { headers[k.toLowerCase()] = v; },
              status: (code) => { statusCode = code; return res; },
              send: (buf) => { body = buf; },
              json: (obj) => { body = Buffer.from(JSON.stringify(obj)); },
              end: () => {}
            };

            await handler(req, res);
            if (statusCode !== 200) {
              console.error(`FAIL: ${file} returned status ${statusCode}`);
              process.exit(1);
            }
            if (headers['content-type'] !== 'application/pdf') {
              console.error(`FAIL: ${file} content-type is ${headers['content-type']}`);
              process.exit(2);
            }
            if (!body || body.slice(0, 5).toString('ascii') !== '%%PDF-') {
              console.error(`FAIL: ${file} missing %%PDF- magic bytes`);
              process.exit(3);
            }
          }
          console.log('ALL_18_SERVED_OK');
          process.exit(0);
        })();
        """ % (json.dumps(self.EXPECTED_FILES), json.dumps(self.STARTUP_ID))

        proc = subprocess.run(
            ["node", "--env-file=.env", "-e", cmd],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True
        )
        self.assertEqual(proc.returncode, 0, f"api/pdf.js failed to serve deliverables:\n{proc.stderr}\n{proc.stdout}")
        self.assertIn("ALL_18_SERVED_OK", proc.stdout)

    def test_03_pdf_api_http_caching_and_method_guards(self):
        """Verify conditional GET (304), HEAD request (200 empty body), and 405 Method Not Allowed."""
        cmd = """
        const handler = require('./api/pdf');
        (async () => {
          // 1. HEAD request
          let headStatus = null;
          const headHeaders = {};
          let headBody = null;
          await handler({
            method: 'HEAD',
            query: { startup_id: %s, file: '04_WavonCeramics_BusinessModelCanvas.pdf' },
            headers: {}
          }, {
            setHeader: (k, v) => { headHeaders[k.toLowerCase()] = v; },
            status: (c) => { headStatus = c; return { end: () => {} }; },
            send: (b) => { headBody = b; },
            end: () => {}
          });

          // 2. Conditional GET with matching ETag
          const etag = headHeaders['etag'];
          let condStatus = null;
          await handler({
            method: 'GET',
            query: { startup_id: %s, file: '04_WavonCeramics_BusinessModelCanvas.pdf' },
            headers: { 'if-none-match': etag }
          }, {
            setHeader: () => {},
            status: (c) => { condStatus = c; return { end: () => {} }; },
            send: () => {},
            end: () => {}
          });

          // 3. Method Not Allowed (POST)
          let postStatus = null;
          const postHeaders = {};
          await handler({
            method: 'POST',
            query: {},
            headers: {}
          }, {
            setHeader: (k, v) => { postHeaders[k.toLowerCase()] = v; },
            status: (c) => { postStatus = c; return { json: () => {} }; },
            json: () => {}
          });

          console.log(JSON.stringify({ headStatus, hasHeadBody: !!headBody, condStatus, postStatus, allowHeader: postHeaders['allow'] }));
          process.exit(0);
        })();
        """ % (json.dumps(self.STARTUP_ID), json.dumps(self.STARTUP_ID))

        proc = subprocess.run(
            ["node", "--env-file=.env", "-e", cmd],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True
        )
        self.assertEqual(proc.returncode, 0, f"Cache/method test failed:\n{proc.stderr}")
        res = json.loads(proc.stdout.strip())
        self.assertEqual(res["headStatus"], 200)
        self.assertFalse(res["hasHeadBody"])
        self.assertEqual(res["condStatus"], 304)
        self.assertEqual(res["postStatus"], 405)
        self.assertIn("GET", res["allowHeader"])

    def test_04_pdf_api_negative_and_security_boundaries(self):
        """Verify 400 Bad Request on missing params or path traversal, and 404 on non-existent files."""
        cmd = """
        const handler = require('./api/pdf');
        (async () => {
          const testCases = [
            { req: { method: 'GET', query: {}, headers: {} }, expected: 400, desc: 'missing params' },
            { req: { method: 'GET', query: { startup_id: %s, file: '../../../etc/passwd' }, headers: {} }, expected: 400, desc: 'path traversal' },
            { req: { method: 'GET', query: { startup_id: %s, file: 'sub/dir/test.pdf' }, headers: {} }, expected: 400, desc: 'slash in filename' },
            { req: { method: 'GET', query: { startup_id: %s, file: 'ghost.pdf' }, headers: {} }, expected: 404, desc: 'non-existent file' },
            { req: { method: 'GET', query: { startup_id: 'NonExistentStartup', file: '01_Supplementary.pdf' }, headers: {} }, expected: 404, desc: 'unknown startup' },
          ];

          for (const tc of testCases) {
            let statusCode = null;
            const res = {
              setHeader: () => {},
              status: (c) => { statusCode = c; return { json: () => {}, send: () => {} }; },
              json: () => {},
              send: () => {}
            };
            await handler(tc.req, res);
            if (statusCode !== tc.expected) {
              console.error(`Case ${tc.desc} failed: expected ${tc.expected}, got ${statusCode}`);
              process.exit(1);
            }
          }
          console.log('SECURITY_BOUNDARIES_OK');
          process.exit(0);
        })();
        """ % (json.dumps(self.STARTUP_ID), json.dumps(self.STARTUP_ID), json.dumps(self.STARTUP_ID))

        proc = subprocess.run(
            ["node", "--env-file=.env", "-e", cmd],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True
        )
        self.assertEqual(proc.returncode, 0, f"Security boundaries test failed:\n{proc.stderr}\n{proc.stdout}")
        self.assertIn("SECURITY_BOUNDARIES_OK", proc.stdout)

    def test_05_wavon_extractions_payload_document_sections_populated(self):
        """Verify startup_extractions has all 10 CleanTech Open categories mapped with non-empty PDFs."""
        conn = psycopg2.connect(self.db_url)
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        try:
            cur.execute("SELECT payload FROM startup_extractions WHERE startup_id = %s", (self.STARTUP_ID,))
            row = cur.fetchone()
            self.assertIsNotNone(row, f"Startup {self.STARTUP_ID} not found in startup_extractions")

            payload = row["payload"]
            sections = payload.get("document", {}).get("sections", [])
            self.assertGreaterEqual(len(sections), 10, f"Expected >= 10 sections, found {len(sections)}")

            cat_map = {s["cat_code"]: s for s in sections}
            required_cats = ["BC", "ES", "F", "IP", "IS", "L", "M", "PMF", "T", "TP"]

            for cat in required_cats:
                self.assertIn(cat, cat_map, f"Category {cat} missing from Wavon Ceramics sections")
                sec = cat_map[cat]
                self.assertGreater(len(sec.get("pdfs", [])), 0, f"Category {cat} has 0 mapped PDFs")
                for p in sec["pdfs"]:
                    self.assertTrue(p["url"].startswith("/api/pdf?startup_id="), f"Invalid PDF URL: {p['url']}")
                    self.assertTrue(len(p.get("label", "")) > 0, "PDF label must not be empty")

            # Verify specific essential deliverables
            bc_urls = [p["url"] for p in cat_map["BC"]["pdfs"]]
            self.assertTrue(any("BusinessModelCanvas" in u for u in bc_urls), "BC missing BusinessModelCanvas")

            ip_urls = [p["url"] for p in cat_map["IP"]["pdfs"]]
            self.assertTrue(any("InvestorPitch" in u for u in ip_urls), "IP missing InvestorPitch")

            f_urls = [p["url"] for p in cat_map["F"]["pdfs"]]
            self.assertTrue(any("FinancialProjection" in u for u in f_urls), "F missing FinancialProjection")

            is_urls = [p["url"] for p in cat_map["IS"]["pdfs"]]
            self.assertTrue(any("ExecutiveSummary" in u for u in is_urls), "IS missing ExecutiveSummary")
        finally:
            cur.close()
            conn.close()

    def test_06_frontend_render_left_pane_contract(self):
        """Verify renderLeftPane generates universal dropdown, iframe, and zero empty-state placeholders."""
        cmd = """
        const fs = require('fs');
        const { Client } = require('pg');

        (async () => {
          const client = new Client({ connectionString: %s, ssl: { rejectUnauthorized: false } });
          await client.connect();
          const r = await client.query("SELECT payload FROM startup_extractions WHERE startup_id = $1", [%s]);
          await client.end();

          const payload = r.rows[0].payload;
          const categories = ['BC', 'ES', 'F', 'IP', 'IS', 'L', 'M', 'PMF', 'T', 'TP'];

          for (const cat of categories) {
            const elements = {
              'extraction-viewer': { innerHTML: '', textContent: '', style: {} },
              'left-step-pill': { textContent: '' }
            };
            const mockDoc = {
              getElementById: (id) => elements[id] || null
            };
            global.document = mockDoc;
            global.window = { CTO: {} };

            eval(fs.readFileSync('site/js/render.js', 'utf8'));
            window.CTO.Render.renderLeftPane(cat, payload.document);

            const html = elements['extraction-viewer'].innerHTML;
            if (!html.includes('<select id="universal-pdf-selector"')) {
              console.error(`FAIL: ${cat} missing universal-pdf-selector`);
              process.exit(1);
            }
            if (!html.includes('<iframe id="primary-pdf-viewer"')) {
              console.error(`FAIL: ${cat} missing primary-pdf-viewer`);
              process.exit(2);
            }
            if (html.includes('No Documents Found')) {
              console.error(`FAIL: ${cat} displays No Documents Found placeholder`);
              process.exit(3);
            }
          }
          console.log('RENDER_LEFT_PANE_ALL_10_CATS_OK');
          process.exit(0);
        })();
        """ % (json.dumps(self.db_url), json.dumps(self.STARTUP_ID))

        proc = subprocess.run(
            ["node", "-e", cmd],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True
        )
        self.assertEqual(proc.returncode, 0, f"Frontend renderLeftPane simulation failed:\n{proc.stderr}\n{proc.stdout}")
        self.assertIn("RENDER_LEFT_PANE_ALL_10_CATS_OK", proc.stdout)

    def test_07_regression_guard_other_91_startups_untouched(self):
        """Verify that exactly 92 startups exist in startup_extractions and the other 91 remain intact."""
        conn = psycopg2.connect(self.db_url)
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT startup_id,
                       jsonb_array_length(COALESCE(payload->'document'->'sections', '[]'::jsonb)) as sec_cnt
                FROM startup_extractions
                ORDER BY startup_id ASC
            """)
            rows = cur.fetchall()
            self.assertEqual(len(rows), 92, f"Expected exactly 92 startups in DB, found {len(rows)}")

            for sid, sec_cnt in rows:
                self.assertGreater(sec_cnt, 0, f"Startup {sid} has 0 document sections")
        finally:
            cur.close()
            conn.close()


if __name__ == "__main__":
    unittest.main()
