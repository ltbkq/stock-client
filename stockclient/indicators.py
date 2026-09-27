"""Technical indicators (pure numpy, no Qt)."""

from __future__ import annotations

import numpy as np


def close_array(bars) -> np.ndarray:
    return np.array([b.close for b in bars], dtype=float)


def avg_price(bars) -> np.ndarray:
    """分时均价线：累计成交额 / 累计成交量；累计量为 0 的位置返回 nan。"""
    amount = np.array([b.amount for b in bars], dtype=float)
    volume = np.array([b.volume for b in bars], dtype=float)
    cum_volume = np.cumsum(volume)
    out = np.full(len(bars), np.nan)
    np.divide(np.cumsum(amount), cum_volume, out=out, where=cum_volume > 0)
    return out


def ma(values: np.ndarray, n: int) -> np.ndarray:
    if len(values) < n:
        return np.full(len(values), np.nan)
    out = np.full(len(values), np.nan)
    c = np.cumsum(np.insert(values, 0, 0.0))
    out[n - 1:] = (c[n:] - c[:-n]) / n
    return out


def ema(values: np.ndarray, n: int) -> np.ndarray:
    out = np.full(len(values), np.nan)
    if len(values) == 0:
        return out
    k = 2.0 / (n + 1)
    out[0] = values[0]
    for i in range(1, len(values)):
        out[i] = values[i] * k + out[i - 1] * (1 - k)
    return out


def macd(close: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9):
    dif = ema(close, fast) - ema(close, slow)
    dea = ema(dif, signal)
    hist = (dif - dea) * 2.0
    return dif, dea, hist


def rsi(close: np.ndarray, n: int = 14) -> np.ndarray:
    out = np.full(len(close), np.nan)
    if len(close) <= n:
        return out
    delta = np.diff(close)
    gain = np.clip(delta, 0, None)
    loss = -np.clip(delta, None, 0)
    avg_gain, avg_loss = gain[:n].mean(), loss[:n].mean()
    for i in range(n, len(close)):
        avg_gain = (avg_gain * (n - 1) + gain[i - 1]) / n
        avg_loss = (avg_loss * (n - 1) + loss[i - 1]) / n
        rs = avg_gain / avg_loss if avg_loss else 100.0
        out[i] = 100 - 100 / (1 + rs)
    return out


def kdj(high: np.ndarray, low: np.ndarray, close: np.ndarray, n: int = 9):
    k = np.full(len(close), np.nan)
    d = np.full(len(close), np.nan)
    j = np.full(len(close), np.nan)
    prev_k = prev_d = 50.0
    for i in range(len(close)):
        lo = low[max(0, i - n + 1):i + 1].min()
        hi = high[max(0, i - n + 1):i + 1].max()
        rsv = 50.0 if hi == lo else (close[i] - lo) / (hi - lo) * 100
        prev_k = 2 / 3 * prev_k + 1 / 3 * rsv
        prev_d = 2 / 3 * prev_d + 1 / 3 * prev_k
        k[i], d[i], j[i] = prev_k, prev_d, 3 * prev_k - 2 * prev_d
    return k, d, j


def boll(close: np.ndarray, n: int = 20, k: float = 2.0):
    mid = ma(close, n)
    std = np.full(len(close), np.nan)
    for i in range(n - 1, len(close)):
        std[i] = close[i - n + 1:i + 1].std()
    return mid + k * std, mid, mid - k * std
