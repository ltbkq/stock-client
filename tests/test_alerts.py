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

    def test_price_below(self):
        engine = AlertEngine([Alert("600519", "price_below", 90.0)])
        self.assertEqual(len(engine.evaluate(q(91))), 0)
        self.assertEqual(len(engine.evaluate(q(89))), 1)    # fires once
        self.assertEqual(len(engine.evaluate(q(88))), 0)    # still below -> silent
        engine.evaluate(q(92))                               # back above resets
        self.assertEqual(len(engine.evaluate(q(88))), 1)    # fires again

    def test_pct_above(self):
        engine = AlertEngine([Alert("600519", "pct_above", 3.0)])
        self.assertEqual(len(engine.evaluate(q(102))), 0)   # +2% -> no
        self.assertEqual(len(engine.evaluate(q(104))), 1)   # +4% -> fires
        self.assertEqual(len(engine.evaluate(q(105))), 0)   # still above -> silent

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

    def test_enable_disable_toggle(self):
        alert = Alert("600519", "price_above", 1.0)
        engine = AlertEngine([alert])
        self.assertEqual(len(engine.evaluate(q(200))), 1)   # fires
        alert.enabled = False
        self.assertEqual(len(engine.evaluate(q(200))), 0)   # disabled -> silent
        alert.enabled = True
        engine.evaluate(q(0.5))                              # 跌破阈值复位
        self.assertEqual(len(engine.evaluate(q(200))), 1)   # 重新触发

    def test_remove(self):
        alert = Alert("600519", "price_above", 1.0)
        engine = AlertEngine([alert])
        engine.remove(alert)
        self.assertEqual(engine.alerts, [])
        self.assertEqual(engine.evaluate(q(200)), [])
        engine.remove(alert)   # 重复删除无副作用
        self.assertEqual(engine.alerts, [])


if __name__ == "__main__":
    unittest.main()
