import json
import tempfile
import unittest
from pathlib import Path

from stockclient import datasource


class DataSourceConfigTest(unittest.TestCase):
    def test_load_default_source(self):
        src = datasource.load_source("eastmoney")
        self.assertEqual(src["name"], "eastmoney")
        for key in ("snapshot", "list", "kline", "trends", "suggest"):
            self.assertIn(key, src["endpoints"])
        self.assertIn("price", src["field_map"]["snapshot"])
        self.assertEqual(src["periods"]["day"], 101)

    def test_user_override_deep_merge(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data_sources.json"
            # override one endpoint + one rate limit, leave the rest intact
            path.write_text(json.dumps({
                "sources": {"eastmoney": {
                    "endpoints": {"snapshot": "https://example.test/snap"},
                    "request": {"retries": 9},
                }}
            }), encoding="utf-8")
            data = datasource.load_data_sources(path)
            east = data["sources"]["eastmoney"]
            self.assertEqual(east["endpoints"]["snapshot"], "https://example.test/snap")
            self.assertEqual(east["request"]["retries"], 9)
            self.assertEqual(east["request"]["timeout"], 8.0)          # untouched
            self.assertIn("kline", east["endpoints"])                  # untouched

    def test_export_user_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "sub" / "data_sources.json"
            written = datasource.export_user_config(target)
            self.assertTrue(written.is_file())
            self.assertIn("eastmoney", written.read_text(encoding="utf-8"))

    def test_unknown_source(self):
        with self.assertRaises(KeyError):
            datasource.load_source("does-not-exist")


class EastMoneyConfigWiringTest(unittest.TestCase):
    def test_module_constants_from_config(self):
        from stockclient import eastmoney
        src = datasource.load_source("eastmoney")
        self.assertEqual(eastmoney.SNAPSHOT_URL, src["endpoints"]["snapshot"])
        self.assertEqual(eastmoney.KLINE_URL, src["endpoints"]["kline"])
        self.assertEqual(eastmoney.PERIODS, src["periods"])
        self.assertEqual(eastmoney.DEFAULT_HEADERS["Referer"], src["headers"]["Referer"])


if __name__ == "__main__":
    unittest.main()
