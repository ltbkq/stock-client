"""Unit tests for the pure-numpy technical indicators."""

import unittest

import numpy as np

from stockclient.indicators import avg_price, boll, break_gaps, ema, kdj, macd, ma, rsi


class MaTest(unittest.TestCase):
    def test_window(self):
        out = ma(np.array([1, 2, 3, 4, 5], dtype=float), 3)
        self.assertTrue(np.isnan(out[0]) and np.isnan(out[1]))
        np.testing.assert_allclose(out[2:], [2, 3, 4])

    def test_too_short(self):
        out = ma(np.array([1.0, 2.0]), 5)
        self.assertEqual(len(out), 2)
        self.assertTrue(np.all(np.isnan(out)))


class EmaTest(unittest.TestCase):
    def test_constant(self):
        out = ema(np.full(10, 3.0), 3)
        np.testing.assert_allclose(out, 3.0)

    def test_converges(self):
        # step input: ema rises monotonically toward the new level
        vals = np.array([0.0] * 5 + [10.0] * 40)
        out = ema(vals, 10)
        self.assertEqual(out[0], 0.0)
        self.assertLess(out[4], 1.0)
        self.assertGreater(out[-1], 9.9)
        self.assertTrue(np.all(np.diff(out[5:]) > 0))


class MacdTest(unittest.TestCase):
    def test_shapes_and_hist(self):
        rng = np.random.default_rng(42)
        close = np.cumsum(rng.standard_normal(200)) + 100.0
        dif, dea, hist = macd(close)
        self.assertEqual(len(dif), len(close))
        self.assertEqual(len(dea), len(close))
        self.assertEqual(len(hist), len(close))
        np.testing.assert_allclose(hist, (dif - dea) * 2.0)

    def test_flat(self):
        dif, dea, hist = macd(np.full(50, 7.5))
        np.testing.assert_allclose(dif, 0.0, atol=1e-12)
        np.testing.assert_allclose(dea, 0.0, atol=1e-12)
        np.testing.assert_allclose(hist, 0.0, atol=1e-12)


class RsiTest(unittest.TestCase):
    def test_bounds(self):
        rng = np.random.default_rng(7)
        close = np.cumsum(rng.standard_normal(100)) + 50.0
        out = rsi(close, 14)
        valid = out[~np.isnan(out)]
        self.assertTrue(np.all(valid >= 0.0))
        self.assertTrue(np.all(valid <= 100.0))

    def test_all_up(self):
        # avg_loss == 0 -> rs capped at 100 -> rsi = 100 - 100/101
        close = np.arange(1.0, 30.0)
        out = rsi(close, 14)
        self.assertAlmostEqual(out[-1], 100.0 - 100.0 / 101.0, places=5)

    def test_all_down(self):
        close = np.arange(30.0, 1.0, -1.0)
        out = rsi(close, 14)
        self.assertAlmostEqual(out[-1], 0.0, places=5)

    def test_too_short(self):
        out = rsi(np.array([1.0, 2.0, 3.0]), 14)
        self.assertTrue(np.all(np.isnan(out)))


class KdjTest(unittest.TestCase):
    def test_j_relation(self):
        rng = np.random.default_rng(3)
        close = np.cumsum(rng.standard_normal(80)) + 100.0
        high = close + rng.random(80) * 2.0
        low = close - rng.random(80) * 2.0
        k, d, j = kdj(high, low, close, 9)
        self.assertEqual(len(k), len(close))
        np.testing.assert_allclose(j, 3.0 * k - 2.0 * d)

    def test_kd_bounds(self):
        rng = np.random.default_rng(5)
        close = np.cumsum(rng.standard_normal(60)) + 100.0
        high = close + rng.random(60)
        low = close - rng.random(60)
        k, d, _ = kdj(high, low, close, 9)
        valid = ~np.isnan(k)
        self.assertTrue(np.all(k[valid] >= 0.0) and np.all(k[valid] <= 100.0))
        self.assertTrue(np.all(d[valid] >= 0.0) and np.all(d[valid] <= 100.0))

    def test_flat(self):
        k, d, j = kdj(np.full(20, 5.0), np.full(20, 5.0), np.full(20, 5.0), 9)
        np.testing.assert_allclose(k, 50.0)   # hi == lo -> rsv = 50
        np.testing.assert_allclose(d, 50.0)
        np.testing.assert_allclose(j, 50.0)


class BollTest(unittest.TestCase):
    def test_ordering(self):
        rng = np.random.default_rng(11)
        close = np.cumsum(rng.standard_normal(120)) + 50.0
        upper, mid, lower = boll(close, 20, 2.0)
        self.assertEqual(len(upper), len(close))
        valid = ~np.isnan(mid)
        self.assertTrue(np.all(upper[valid] >= mid[valid]))
        self.assertTrue(np.all(mid[valid] >= lower[valid]))
        np.testing.assert_allclose(mid, ma(close, 20))

    def test_constant(self):
        close = np.full(30, 5.0)
        upper, mid, lower = boll(close, 20, 2.0)
        valid = ~np.isnan(mid)
        np.testing.assert_allclose(upper[valid], 5.0)   # std == 0
        np.testing.assert_allclose(lower[valid], 5.0)


class BreakGapsTest(unittest.TestCase):
    """回归：分时午休/停牌处不能被连成一条直线。"""

    def test_inserts_nan_across_gap(self):
        xs = np.array([0, 60, 120, 5400, 5460], dtype=float)   # 54x gap
        ys = np.array([1, 2, 3, 4, 5], dtype=float)
        gx, gy = break_gaps(xs, ys)
        self.assertEqual(len(gx), len(xs) + 1)                 # one NaN inserted
        self.assertTrue(np.isnan(gy).any())
        # original samples all preserved
        self.assertTrue(set(np.round(ys)).issubset(set(np.round(gy[~np.isnan(gy)]))))

    def test_uniform_series_unchanged(self):
        xs = np.arange(0, 600, 60, dtype=float)
        ys = np.arange(10, dtype=float)
        gx, gy = break_gaps(xs, ys)
        np.testing.assert_array_equal(gx, xs)
        np.testing.assert_array_equal(gy, ys)

    def test_too_short(self):
        gx, gy = break_gaps(np.array([0.0]), np.array([1.0]))
        self.assertEqual(len(gx), 1)


class AvgPriceTest(unittest.TestCase):
    """分时均价线 = 累计成交额 / 累计成交量。"""

    class _Bar:
        def __init__(self, amount, volume):
            self.amount, self.volume = amount, volume

    def test_vwap(self):
        bars = [self._Bar(100, 10), self._Bar(300, 10)]        # 100/10=10, 400/20=20
        out = avg_price(bars)
        np.testing.assert_allclose(out, [10.0, 20.0])

    def test_zero_volume_is_nan(self):
        bars = [self._Bar(0, 0), self._Bar(100, 10)]
        out = avg_price(bars)
        self.assertTrue(np.isnan(out[0]))
        self.assertAlmostEqual(out[1], 10.0)


if __name__ == "__main__":
    unittest.main()
