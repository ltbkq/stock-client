import unittest
from datetime import datetime

from stockclient.eastmoney import (
    LIST_URL, SUGGEST_URL, EastMoneyClient,
    parse_clist, parse_kline, parse_orderbook, parse_snapshot, parse_trends, secid,
)


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


class ClistTest(unittest.TestCase):
    # canned clist/get payload: 2 normal rows + 1 suspended (f2 == "-")
    PAYLOAD = {"data": {"total": 3, "diff": [
        {"f12": "600519", "f14": "贵州茅台", "f2": 1700.0, "f3": 2.3, "f4": 38.2,
         "f5": 123456, "f6": 2100000000.0, "f15": 1712.0, "f16": 1685.0,
         "f17": 1690.0, "f18": 1661.8, "f168": 0.98},
        {"f12": "000001", "f14": "平安银行", "f2": 12.5, "f3": -0.8, "f4": -0.1,
         "f5": 50000, "f6": 625000000.0, "f15": 12.6, "f16": 12.3,
         "f17": 12.45, "f18": 12.6, "f168": 0.5},
        {"f12": "300750", "f14": "宁德时代", "f2": "-", "f3": "-", "f4": "-",
         "f5": 0, "f6": 0, "f15": "-", "f16": "-", "f17": "-",
         "f18": 200.0, "f168": 0},
    ]}}

    def test_parse(self):
        qs = parse_clist(self.PAYLOAD)
        self.assertEqual(len(qs), 3)
        q = qs[0]
        self.assertEqual(q.code, "600519")
        self.assertEqual(q.name, "贵州茅台")
        self.assertAlmostEqual(q.price, 1700.0)
        self.assertAlmostEqual(q.prev_close, 1661.8)
        self.assertAlmostEqual(q.change, 38.2, places=1)
        self.assertAlmostEqual(q.pct, 2.30, places=1)
        self.assertAlmostEqual(q.open, 1690.0)
        self.assertAlmostEqual(q.high, 1712.0)
        self.assertAlmostEqual(q.low, 1685.0)
        self.assertAlmostEqual(q.volume, 12345600.0)    # 手 -> 股
        self.assertAlmostEqual(q.amount, 2100000000.0)
        self.assertAlmostEqual(q.turnover, 0.98)

    def test_suspended(self):
        q = parse_clist(self.PAYLOAD)[2]
        self.assertEqual(q.code, "300750")
        self.assertEqual(q.price, 0.0)                 # f2 == "-" -> 停牌
        self.assertEqual(q.high, 0.0)
        self.assertAlmostEqual(q.prev_close, 200.0)

    def test_empty(self):
        self.assertEqual(parse_clist({}), [])
        self.assertEqual(parse_clist({"data": None}), [])
        self.assertEqual(parse_clist({"data": {"diff": None}}), [])


class TrendsTest(unittest.TestCase):
    # canned trends2/get payload: time, open, close, high, low, 手, amount, avg
    PAYLOAD = {"data": {"code": "600519", "klines": [
        "2024-01-02 09:31,1685.00,1686.00,1687.00,1684.00,1234,2100000.0,1685.50",
        "2024-01-02 09:32,1686.00,1685.50,1686.50,1685.00,900,1500000.0,1685.80",
    ]}}

    def test_parse(self):
        bars = parse_trends(self.PAYLOAD)
        self.assertEqual(len(bars), 2)
        b = bars[0]
        self.assertEqual(b.dt, datetime(2024, 1, 2, 9, 31))
        self.assertEqual(b.open, 1685.0)
        self.assertEqual(b.close, 1686.0)      # note: open, close, high, low
        self.assertEqual(b.high, 1687.0)
        self.assertEqual(b.low, 1684.0)
        self.assertAlmostEqual(b.volume, 123400.0)    # 手 -> 股
        self.assertAlmostEqual(b.amount, 2100000.0)

    def test_empty(self):
        self.assertEqual(parse_trends({}), [])
        self.assertEqual(parse_trends({"data": {"klines": None}}), [])


class ClientTest(unittest.TestCase):
    """Client methods with a stubbed _get (no network)."""

    def test_clist_single_request_filters(self):
        client = EastMoneyClient()
        calls = []

        def fake_get(url, params):
            calls.append((url, params))
            return ClistTest.PAYLOAD

        client._get = fake_get
        qs = client.clist(["600519", "000001", "300750", "999999"])
        self.assertEqual(len(calls), 1)                # 一次请求拉全自选股
        url, params = calls[0]
        self.assertEqual(url, LIST_URL)
        self.assertEqual(params["fs"], "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:3")
        self.assertEqual(params["fields"],
                         "f12,f14,f2,f3,f4,f5,f6,f15,f16,f17,f18,f168")
        self.assertEqual([q.code for q in qs],
                         ["600519", "000001", "300750"])   # 999999 被过滤

    def test_trends_uses_parse_trends(self):
        client = EastMoneyClient()
        client._get = lambda url, params: TrendsTest.PAYLOAD
        bars = client.trends("600519")
        self.assertEqual(len(bars), 2)
        self.assertEqual(bars[0].dt, datetime(2024, 1, 2, 9, 31))
        self.assertAlmostEqual(bars[0].volume, 123400.0)

    def test_suggest(self):
        client = EastMoneyClient()
        payload = {"QuotationCodeTable": {"Data": [
            {"Code": "600519", "Name": "贵州茅台", "MktNum": "1"},
            {"Code": "600520", "Name": "贵州茅台集团", "MktNum": "1"},
            {"Code": "000001", "Name": "平安银行", "MktNum": "0"},
        ]}}
        seen = {}

        def fake_get(url, params):
            seen.update(params)
            return payload

        client._get = fake_get
        out = client.suggest("茅台", limit=2)
        self.assertEqual(seen["input"], "茅台")
        self.assertEqual(seen["type"], 14)
        self.assertEqual(seen["count"], 2)
        self.assertEqual(out, [("600519", "贵州茅台"), ("600520", "贵州茅台集团")])

    def test_suggest_defensive(self):
        client = EastMoneyClient()
        client._get = lambda url, params: {"QuotationCodeTable": {"Data": [
            {"Code": "600519", "Name": "贵州茅台", "MktNum": "1"},
            {"Code": "", "Name": "缺代码", "MktNum": "1"},
            {"Name": "缺代码字段", "MktNum": "0"},
            "garbage",
        ]}}
        self.assertEqual(client.suggest("茅台"), [("600519", "贵州茅台")])
        client._get = lambda url, params: {}
        self.assertEqual(client.suggest("茅台"), [])


if __name__ == "__main__":
    unittest.main()
