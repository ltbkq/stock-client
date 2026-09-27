"""Deterministic offline sample data so the UI runs without any network.

Used by ``run.py --demo`` and by the test-suite.  Everything is derived from a
seed so repeated runs render exactly the same chart.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from .models import Bar, OrderBook, OrderBookLevel, Quote

WATCHLIST: list[tuple[str, str]] = [
    ("600519", "贵州茅台"),
    ("000001", "平安银行"),
    ("300750", "宁德时代"),
    ("601318", "中国平安"),
    ("000858", "五粮液"),
    ("002594", "比亚迪"),
    ("600036", "招商银行"),
    ("000333", "美的集团"),
    ("601899", "紫金矿业"),
]


def _seed(code: str) -> int:
    return int(code) % 100000 or 1


def daily_bars(code: str, count: int = 240) -> list[Bar]:
    rng = random.Random(_seed(code))
    price = 20.0 + (_seed(code) % 1800)
    bars: list[Bar] = []
    start = datetime.now() - timedelta(days=count)
    for i in range(count):
        dt = (start + timedelta(days=i)).replace(hour=15, minute=0, second=0, microsecond=0)
        drift = rng.uniform(-0.03, 0.03)
        open_ = max(0.5, price * (1 + rng.uniform(-0.01, 0.01)))
        close = max(0.5, open_ * (1 + drift))
        high = max(open_, close) * (1 + abs(rng.uniform(0, 0.012)))
        low = min(open_, close) * (1 - abs(rng.uniform(0, 0.012)))
        vol = rng.uniform(3e6, 8e7)
        bars.append(Bar(dt, round(open_, 2), round(high, 2), round(low, 2),
                        round(close, 2), round(vol), round(vol * close)))
        price = close
    return bars


def intraday_bars(code: str) -> list[Bar]:
    """One trading day of 1-minute bars (09:30-11:30, 13:00-15:00)."""
    rng = random.Random(_seed(code) + 7)
    base = daily_bars(code, 2)[-1].close
    price = base
    bars: list[Bar] = []
    day = datetime.now().replace(second=0, microsecond=0)
    for start_h, end_h in ((9, 11), (13, 15)):
        t = day.replace(hour=start_h, minute=30 if start_h == 9 else 0)
        limit = t.replace(hour=end_h, minute=30 if start_h == 9 else 0)
        while t <= limit:
            price = max(0.5, price * (1 + rng.uniform(-0.0015, 0.0015)))
            vol = rng.uniform(1e4, 6e5)
            bars.append(Bar(t, price, price, price, price, round(vol)))
            t += timedelta(minutes=1)
    return bars


def quote(code: str) -> Quote:
    bars = daily_bars(code, 2)
    prev, last = bars[-2].close, bars[-1].close
    day = daily_bars(code, 1)[0]
    return Quote(code=code, name=dict(WATCHLIST).get(code, code),
                 price=last, prev_close=prev, open=day.open, high=day.high,
                 low=day.low, volume=day.volume, amount=day.amount,
                 turnover=round(abs(last - prev) / prev * 100, 2), ts=datetime.now())


def orderbook(code: str) -> OrderBook:
    q = quote(code)
    tick = max(0.01, round(q.price * 0.0005, 2))
    asks = [OrderBookLevel(round(q.price + tick * (i + 1), 2), (i + 1) * 40000.0)
            for i in range(5)]
    bids = [OrderBookLevel(round(q.price - tick * (i + 1), 2), (i + 1) * 52000.0)
            for i in range(5)]
    return OrderBook(code=code, asks=asks, bids=bids, price=q.price,
                     pct=q.pct, avg_price=round((q.high + q.low) / 2, 2), volume=q.volume)
