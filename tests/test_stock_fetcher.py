from __future__ import annotations

import json
import os
import sys
import unittest
from unittest import mock

from lib.stock_fetcher import FetchError, _request_json, fetch_full_payload, fetch_single_payload


class RequestJsonTests(unittest.TestCase):
    @mock.patch("urllib.request.urlopen")
    def test_returns_parsed_json(self, mocked_urlopen):
        fake_response = mock.Mock()
        fake_response.read.return_value = json.dumps({"hello": True}).encode("utf-8")
        fake_response.__enter__ = mock.Mock(return_value=fake_response)
        fake_response.__exit__ = mock.Mock(return_value=False)
        mocked_urlopen.return_value = fake_response
        self.assertEqual(_request_json("http://example.invalid"), {"hello": True})

    @mock.patch("urllib.request.urlopen", side_effect=OSError("boom"))
    def test_raises_fetch_error_after_retries(self, mocked_urlopen):
        with self.assertRaises(FetchError):
            _request_json("http://example.invalid")


class LiveFetchTests(unittest.TestCase):
    def test_fetch_single_payload_live(self):
        payload = fetch_single_payload()
        self.assertEqual(payload["symbol"], "2308.TW")
        self.assertEqual(payload["currency"], "TWD")
        self.assertEqual(payload["exchange"], "TAI")
        self.assertIsNotNone(payload["history"]["1mo"])
        self.assertIsNone(payload["history"]["1y"])
        for field in ("previousClose", "price", "change", "changePercent",
                      "fiftyTwoWeekHigh", "fiftyTwoWeekLow"):
            self.assertIsInstance(payload[field], (int, float), field)
        self.assertIsInstance(payload["volume"], int)
        self.assertIsInstance(payload["updatedAt"], int)
        self.assertGreaterEqual(payload["updatedAt"], 0)

    def test_fetch_full_payload_live(self):
        payload = fetch_full_payload()
        self.assertEqual(payload["symbol"], "2308.TW")
        self.assertEqual(payload["currency"], "TWD")
        self.assertEqual(payload["exchange"], "TAI")
        self.assertIsNotNone(payload["history"]["1mo"])
        self.assertIsNotNone(payload["history"]["1y"])
        self.assertGreaterEqual(len(payload["history"]["1mo"]), 10)
        self.assertGreaterEqual(len(payload["history"]["1y"]), 10)
        for field in ("previousClose", "price", "change", "changePercent",
                      "fiftyTwoWeekHigh", "fiftyTwoWeekLow"):
            self.assertIsInstance(payload[field], (int, float), field)
        self.assertIsInstance(payload["volume"], int)
        self.assertIsInstance(payload["updatedAt"], int)
        self.assertGreaterEqual(payload["updatedAt"], 0)


def live_only_suite():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(RequestJsonTests))
    if os.environ.get("RUN_NETWORK_TESTS"):
        suite.addTests(loader.loadTestsFromTestCase(LiveFetchTests))
    return suite


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(live_only_suite())
