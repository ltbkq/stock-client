"""Domain models shared by the data, UI and alert layers.

All prices are expressed in yuan and volumes in *shares* unless stated otherwise.
The upstream (East Money) reports volume in lots (手, 1 lot = 100 shares); the
client normalises to shares at the parsing boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class Quote:
    """A real-time snapshot of one instrument."""

    code: str
    name: str = ""
    price: float = 0.0        # 最新价
    prev_close: float = 0.0   # 昨收
    open: float = 0.0         # 今开
    high: float = 0.0         # 最高
    low: float = 0.0          # 最低
    volume: float = 0.0       # 成交量（股）
    amount: float = 0.0       # 成交额（元）
    turnover: float = 0.0     # 换手率 %
    avg_price: float = 0.0    # 均价（分时）
    ts: datetime | None = None

    @property
    def change(self) -> float:
        if not self.prev_close:
            return 0.0
        return self.price - self.prev_close

    @property
    def pct(self) -> float:
        if not self.prev_close:
            return 0.0
        return (self.price - self.prev_close) / self.prev_close * 100.0


@dataclass(slots=True)
class Bar:
    """One OHLCV candle."""

    dt: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0   # 股
    amount: float = 0.0   # 元


@dataclass(slots=True)
class OrderBookLevel:
    price: float
    volume: float  # 股


@dataclass(slots=True)
class OrderBook:
    """Level-1..5 depth for one instrument (卖5..卖1 / 买1..买5)."""

    code: str
    asks: list[OrderBookLevel] = field(default_factory=list)  # index 0 == 卖1
    bids: list[OrderBookLevel] = field(default_factory=list)  # index 0 == 买1
    price: float = 0.0
    pct: float = 0.0
    avg_price: float = 0.0
    volume: float = 0.0


# --- alert rules -----------------------------------------------------------

ALERT_KINDS = {
    "price_above": "价格上穿",
    "price_below": "价格下破",
    "pct_above": "涨幅超过",
    "pct_below": "跌幅超过",
}


@dataclass(slots=True)
class Alert:
    code: str
    kind: str
    threshold: float
    enabled: bool = True
    note: str = ""

    def label(self) -> str:
        return f"{ALERT_KINDS.get(self.kind, self.kind)} {self.threshold:g}"
