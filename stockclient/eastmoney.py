"""East Money (东方财富) public quote client.

Endpoints
---------
    snapshot   push2.eastmoney.com/api/qt/stock/get
    list       push2.eastmoney.com/api/qt/clist/get
    kline      push2his.eastmoney.com/api/qt/stock/kline/get
    trends     push2his.eastmoney.com/api/qt/stock/trends2/get   (分时)

Field numbers follow the widely used public mapping; the parser is defensive so
missing / suspended-instrument fields never raise.  Verified against a live
sample (secid=1.600519 -> f57/f58/f43/f170) and the standard inventory; run
``pytest`` (tests/test_eastmoney.py) before relying on a mapping in production.

This is an undocumented third-party interface: keep the request rate low,
cache aggressively and do not redistribute the data.
"""

from __future__ import annotations

import csv
import io
import random
import threading
import time
from datetime import datetime

import requests

from .models import Bar, OrderBook, OrderBookLevel, Quote

SNAPSHOT_URL = "https://push2.eastmoney.com/api/qt/stock/get"
LIST_URL = "https://push2.eastmoney.com/api/qt/clist/get"
KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
TRENDS_URL = "https://push2his.eastmoney.com/api/qt/stock/trends2/get"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Referer": "https://quote.eastmoney.com/",
}

# klt (K line type) -> label used by the UI
PERIODS: dict[str, int] = {
    "1m": 1, "5m": 5, "15m": 15, "30m": 30, "60m": 60,
    "day": 101, "week": 102, "month": 103,
}
# fqt (adjustment) -> label
ADJUSTS: dict[str, int] = {"none": 0, "pre": 1, "post": 2}

_SNAPSHOT_FIELDS = ",".join([
    "f43", "f44", "f45", "f46", "f47", "f48", "f57", "f58", "f59", "f60",
    "f86", "f116", "f117", "f162", "f167", "f168", "f169", "f170", "f171",
    "f11", "f12", "f13", "f14", "f15", "f16", "f17", "f18", "f19", "f20",
    "f31", "f32", "f33", "f34", "f35", "f36", "f37", "f38", "f39", "f40",
])
# 买5..买1 are (f11,f12) .. (f19,f20); 卖5..卖1 are (f31,f32) .. (f39,f40).
_BID_FIELDS = [(11, 12), (13, 14), (15, 16), (17, 18), (19, 20)]   # 买5..买1
_ASK_FIELDS = [(31, 32), (33, 34), (35, 36), (37, 38), (39, 40)]   # 卖5..卖1


def secid(code: str) -> str:
    """Return the East Money ``secid`` for an A-share code.

    market 1 = 上交所 (6xxxxx / 5xxxxx / 9xxxxx), market 0 = 深交所 & 北交所.
    """
    code = code.strip()
    if code.startswith(("6", "5", "9")):
        return f"1.{code}"
    return f"0.{code}"


def _num(v, default: float = 0.0) -> float:
    try:
        if v in (None, "-", ""):
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def parse_snapshot(data: dict, code: str = "", pre_scaled: bool = True) -> Quote:
    """Map a ``stock/get`` payload (``data`` node) into a :class:`Quote`.

    ``pre_scaled=True`` matches ``fltt=2`` responses (floats already divided by
    the ``f59`` scale).  Pass ``False`` for the integer form, where price fields
    must be divided by ``10**f59``.
    """
    if not data:
        return Quote(code=code)
    code = str(data.get("f57") or code)
    decimals = int(_num(data.get("f59"), 2))
    scale = 10.0 ** decimals

    def px(field: str) -> float:
        v = data.get(field)
        if v in (None, "-"):
            return 0.0
        v = float(v)
        return v if pre_scaled else v / scale

    ts = None
    if data.get("f86"):
        try:
            ts = datetime.fromtimestamp(int(data["f86"]))
        except (ValueError, OSError, TypeError):
            ts = None

    return Quote(
        code=code,
        name=str(data.get("f58") or ""),
        price=px("f43"),
        prev_close=px("f60"),
        open=px("f46"),
        high=px("f44"),
        low=px("f45"),
        volume=_num(data.get("f47")) * 100.0,   # 手 -> 股
        amount=_num(data.get("f48")),
        turnover=_num(data.get("f168")),
        ts=ts,
    )


def parse_orderbook(data: dict, code: str = "", pre_scaled: bool = True) -> OrderBook:
    """Map a ``stock/get`` payload into a 5-level :class:`OrderBook`."""
    if not data:
        return OrderBook(code=code)
    decimals = int(_num(data.get("f59"), 2))
    scale = 10.0 ** decimals

    def px(v):
        v = _num(v)
        return v if pre_scaled else v / scale

    asks = [OrderBookLevel(px(data.get(f"f{p}")), _num(data.get(f"f{v}")) * 100.0)
            for p, v in _ASK_FIELDS]        # 卖5..卖1
    asks.reverse()                          # -> index 0 == 卖1
    bids = [OrderBookLevel(px(data.get(f"f{p}")), _num(data.get(f"f{v}")) * 100.0)
            for p, v in _BID_FIELDS]        # 买5..买1
    bids.reverse()                          # -> index 0 == 买1
    pct = _num(data.get("f170"))
    return OrderBook(
        code=str(data.get("f57") or code),
        asks=asks, bids=bids,
        price=px(data.get("f43")),
        pct=pct if pre_scaled else pct / 100.0,
    )


def parse_kline(payload: dict, code: str = "") -> list[Bar]:
    """Map a ``kline/get`` payload into a list of :class:`Bar`.

    Row layout: date, open, close, high, low, volume(手), amount, ...
    """
    node = (payload or {}).get("data") or {}
    rows = node.get("klines") or []
    bars: list[Bar] = []
    for row in rows:
        parts = next(csv.reader(io.StringIO(row)))
        if len(parts) < 6:
            continue
        try:
            dt = datetime.strptime(parts[0], "%Y-%m-%d %H:%M" if " " in parts[0] else "%Y-%m-%d")
            bars.append(Bar(
                dt=dt,
                open=float(parts[1]),
                close=float(parts[2]),
                high=float(parts[3]),
                low=float(parts[4]),
                volume=float(parts[5]) * 100.0,
                amount=float(parts[6]) if len(parts) > 6 and parts[6] else 0.0,
            ))
        except ValueError:
            continue
    return bars


class EastMoneyClient:
    """Small, rate-limited client with retry/back-off.

    Set ``trust_env=False`` to bypass a system proxy when it misbehaves.
    """

    def __init__(self, timeout: float = 8.0, retries: int = 3,
                 min_interval: float = 0.2, trust_env: bool = True):
        self.timeout = timeout
        self.retries = retries
        self.min_interval = min_interval
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.session.trust_env = trust_env
        self._lock = threading.Lock()
        self._last = 0.0

    def _throttle(self) -> None:
        with self._lock:
            wait = self.min_interval - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()

    def _get(self, url: str, params: dict) -> dict:
        last_exc: Exception | None = None
        for attempt in range(self.retries):
            self._throttle()
            try:
                r = self.session.get(url, params=params, timeout=self.timeout)
                r.raise_for_status()
                return r.json()
            except Exception as exc:            # network / json / http
                last_exc = exc
                time.sleep(min(2 ** attempt, 8) + random.random())
        raise RuntimeError(f"request failed after {self.retries} tries: {last_exc}")

    def snapshot(self, code: str) -> Quote:
        payload = self._get(SNAPSHOT_URL, {
            "secid": secid(code), "fields": _SNAPSHOT_FIELDS, "fltt": 2, "invt": 2,
        })
        return parse_snapshot(payload.get("data") or {}, code)

    def orderbook(self, code: str) -> OrderBook:
        payload = self._get(SNAPSHOT_URL, {
            "secid": secid(code), "fields": _SNAPSHOT_FIELDS, "fltt": 2, "invt": 2,
        })
        return parse_orderbook(payload.get("data") or {}, code)

    def kline(self, code: str, period: str = "day", adjust: str = "pre",
              limit: int = 320) -> list[Bar]:
        payload = self._get(KLINE_URL, {
            "secid": secid(code),
            "klt": PERIODS.get(period, 101),
            "fqt": ADJUSTS.get(adjust, 1),
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "lmt": limit, "end": "20500101",
        })
        return parse_kline(payload, code)

    def trends(self, code: str) -> list[Bar]:
        payload = self._get(TRENDS_URL, {
            "secid": secid(code), "ndays": 1, "iscr": 0, "iscca": 1,
            "fields1": "f1,f2,f3,f4,f5,f6,f7,f8",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58",
        })
        return parse_kline(payload, code)
