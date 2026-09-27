import unittest

from stockclient.alerts import AlertEngine
from stockclient.models import Alert, Quote


def q(price, prev=100.0):
    return Quote(code="600519", name="贵州茅台", price=price, prev_close=prev)


class AlertEngineTest(unittest.TestCase):
    def test_price_above_edge_triggered(self):
        engine = AlertEngine([Alert("600519", "price_above", 120.0)])
        self.assertEqual(len(engine.evaluate(q(119))), 0)
        self.assertEqual(len(engine.evaluate(q(121))), 1)   # fires once
        self.assertEqual(len(engine.evaluate(q(125))), 0)   # still above -> silent
        engine.evaluate(q(118))                              # drop below resets
        self.assertEqual(len(engine.evaluate(q(122))), 1)   # fires again

    def test_pct_below(self):
        engine = AlertEngine([Alert("600519", "pct_below", -5.0)])
        self.assertEqual(len(engine.evaluate(q(94))), 1)
        self.assertEqual(len(engine.evaluate(q(94))), 0)

    def test_other_symbol_ignored(self):
        engine = AlertEngine([Alert("000001", "price_above", 1.0)])
        self.assertEqual(engine.evaluate(q(200)), [])

    def test_disabled(self):
        engine = AlertEngine([Alert("600519", "price_above", 1.0, enabled=False)])
        self.assertEqual(engine.evaluate(q(200)), [])


if __name__ == "__main__":
    unittest.main()
