import unittest

from stockclient.eastmoney import parse_kline, parse_orderbook, parse_snapshot, secid


class SecidTest(unittest.TestCase):
    def test_markets(self):
        self.assertEqual(secid("600519"), "1.600519")
        self.assertEqual(secid("510300"), "1.510300")
        self.assertEqual(secid("000001"), "0.000001")
        self.assertEqual(secid("300750"), "0.300750")
        self.assertEqual(secid("830799"), "0.830799")   # 北交所


class SnapshotTest(unittest.TestCase):
    # integers (no fltt) requiring the f59 decimal scale
    RAW = {"f43": 123700, "f44": 125000, "f45": 122000, "f46": 124000,
           "f47": 123456, "f48": 1500000000, "f57": "600519", "f58": "贵州茅台",
           "f59": 2, "f60": 125114, "f168": 98, "f170": -114, "f86": 1730000000}

    def test_unscaled_ints(self):
        q = parse_snapshot(self.RAW, pre_scaled=False)
        self.assertEqual(q.code, "600519")
        self.assertEqual(q.name, "贵州茅台")
        self.assertAlmostEqual(q.price, 1237.00)
        self.assertAlmostEqual(q.prev_close, 1251.14)
        self.assertAlmostEqual(q.change, -14.14, places=2)
        self.assertAlmostEqual(q.pct, -1.130, places=2)
        self.assertAlmostEqual(q.volume, 12345600.0)     # 手 -> 股

    def test_scaled_floats(self):
        q = parse_snapshot({"f43": 1237.0, "f60": 1251.14, "f57": "600519",
                            "f58": "贵州茅台", "f59": 2})
        self.assertAlmostEqual(q.price, 1237.0)
        self.assertAlmostEqual(q.prev_close, 1251.14)

    def test_empty(self):
        self.assertEqual(parse_snapshot({}).price, 0.0)


class OrderBookTest(unittest.TestCase):
    RAW = {
        "f57": "600519", "f59": 2,
        "f31": 170500, "f32": 120, "f33": 170400, "f34": 80,
        "f35": 170300, "f36": 210, "f37": 170200, "f38": 150,
        "f39": 170100, "f40": 300,             # 卖5..卖1
        "f11": 169600, "f12": 220, "f13": 169700, "f14": 140,
        "f15": 169800, "f16": 90, "f17": 169900, "f18": 180,
        "f19": 170000, "f20": 260,             # 买5..买1
    }

    def test_levels(self):
        ob = parse_orderbook(self.RAW, pre_scaled=False)
        self.assertEqual(len(ob.asks), 5)
        self.assertEqual(len(ob.bids), 5)
        self.assertAlmostEqual(ob.asks[0].price, 1701.0)   # index 0 == 卖1
        self.assertAlmostEqual(ob.asks[4].price, 1705.0)   # index 4 == 卖5
        self.assertAlmostEqual(ob.bids[0].price, 1700.0)   # index 0 == 买1
        self.assertAlmostEqual(ob.bids[4].price, 1696.0)   # index 4 == 买5
        self.assertAlmostEqual(ob.asks[0].volume, 30000.0)


class KlineTest(unittest.TestCase):
    PAYLOAD = {"data": {"code": "600519", "klines": [
        "2024-01-02,1685.00,1700.00,1712.00,1680.00,12345,2100000000,1.9,1.2,20.0,0.9",
        "2024-01-03,1700.00,1690.00,1705.00,1688.00,11000,1800000000,1.0,-0.6,-10.0,0.8",
    ]}}

    def test_parse(self):
        bars = parse_kline(self.PAYLOAD)
        self.assertEqual(len(bars), 2)
        b = bars[0]
        self.assertEqual(b.open, 1685.0)
        self.assertEqual(b.close, 1700.0)      # note: open, close, high, low
        self.assertEqual(b.high, 1712.0)
        self.assertEqual(b.low, 1680.0)
        self.assertAlmostEqual(b.volume, 1234500.0)


if __name__ == "__main__":
    unittest.main()
