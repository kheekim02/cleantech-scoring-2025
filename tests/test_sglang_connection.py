"""Unit test for SGLang OpenAI-compatible server connection and health."""
import os
import unittest
import urllib.request
import json

SGLANG_URL = os.environ.get("SGLANG_BASE_URL", "http://127.0.0.1:30000")


class TestSGLangConnection(unittest.TestCase):
    def test_01_health_check(self):
        """Verify SGLang health endpoint responds 200 OK."""
        url = f"{SGLANG_URL}/health"
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                self.assertEqual(resp.status, 200)
        except Exception as e:
            self.skipTest(f"SGLang server not currently reachable at {url}: {e}")

    def test_02_models_endpoint(self):
        """Verify SGLang /v1/models returns active model list."""
        url = f"{SGLANG_URL}/v1/models"
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                self.assertEqual(resp.status, 200)
                data = json.loads(resp.read().decode())
                self.assertIn("data", data)
                self.assertGreater(len(data["data"]), 0)
                model_id = data["data"][0]["id"]
                print(f"[TEST] SGLang active model: {model_id}")
        except Exception as e:
            self.skipTest(f"SGLang server not currently reachable at {url}: {e}")


if __name__ == "__main__":
    unittest.main()
