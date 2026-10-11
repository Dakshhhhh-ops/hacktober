"""The latency CSV: one row per inference attempt, and failures never crash the app."""
import csv
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from drishti import config, latency_log, vlm

GOOD = '{"hazards": [], "objects": [], "text": [], "summary": "A desk."}'


class LatencyLogTests(unittest.TestCase):
    def test_each_attempt_gets_a_row(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "logs" / "latency.csv"
            replies = iter(["not json", GOOD])
            with mock.patch.object(config, "LATENCY_CSV", path):
                result = vlm.describe("aW1hZ2U=", "read", "hi", post=lambda payload: next(replies))
            rows = list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))

        self.assertEqual(list(rows[0]), latency_log.FIELDS)
        self.assertEqual([r["attempt"] for r in rows], ["1", "2"])
        self.assertEqual([r["parse_outcome"] for r in rows], ["invalid_json", "valid"])
        self.assertEqual({r["request_id"] for r in rows}, {result.request_id})
        self.assertEqual((rows[0]["mode"], rows[0]["lang"], rows[0]["retry_count"]), ("read", "hi", "1"))
        self.assertEqual(rows[1]["request_outcome"], "ok")

    def test_a_failed_request_is_logged_as_an_error(self):
        def down(payload):
            raise vlm.VLMError("Could not reach Ollama.")

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "latency.csv"
            with mock.patch.object(config, "LATENCY_CSV", path):
                with self.assertRaises(vlm.VLMError):
                    vlm.describe("aW1hZ2U=", post=down)
            rows = list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))
        self.assertEqual((rows[0]["parse_outcome"], rows[0]["request_outcome"]), ("error", "error"))

    def test_an_unwritable_log_does_not_stop_the_request(self):
        with tempfile.TemporaryDirectory() as folder:
            # A directory where the file should be makes open() fail.
            with mock.patch.object(config, "LATENCY_CSV", Path(folder)):
                result = vlm.describe("aW1hZ2U=", post=lambda payload: GOOD)
        self.assertEqual(result.status, "ok")


if __name__ == "__main__":
    unittest.main()
