"""East Money (东方财富) public quote client.

All endpoints, request parameters, field mappings, periods and rate limits are
loaded from :mod:`stockclient.datasource` (``data_sources.json``) — change the
interface by editing that file, not this module.

Endpoints (defaults, see ``data_sources.json``)
-----------------------------------------------
    snapshot   push2.eastmoney.com/api/qt/stock/get
    list       push2.eastmoney.com/api/qt/clist/get
    kline      push2his.eastmoney.com/api/qt/stock/kline/get
    trends     push2his.eastmoney.com/api/qt/stock/trends2/get   (分时)
    suggest    searchapi.eastmoney.com/api/suggest/get            (搜索联想)

Field numbers follow the widely used public mapping; the parser is defensive so
missing / suspended-instrument fields never raise.  Verified against a live
sample (secid=1.600519 -> f57/f58/f43/f170) and the standard inventory; run
``tests/test_eastmoney.py`` before relying on a mapping in production.

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

from .datasource import load_source
from .models import Bar, OrderBook, OrderBookLevel, Quote

# --- configuration -----------------------------------------------------------
_DS = load_source("eastmoney")

SNAPSHOT_URL = _DS["endpoints"]["snapshot"]
LIST_URL = _DS["endpoints"]["list"]
KLINE_URL = _DS["endpoints"]["kline"]
TRENDS_URL = _DS["endpoints"]["trends"]
SUGGEST_URL = _DS["endpoints"]["suggest"]

DEFAULT_HEADERS = dict(_DS["headers"])
PERIODS: dict[str, int] = dict(_DS["periods"])       # klt: 周期 -> 代码
ADJUSTS: dict[str, int] = dict(_DS["adjusts"])        # fqt: 复权 -> 代码

_PARAMS = _DS["params"]
_FM = _DS["field_map"]
_SM = _FM["snapshot"]
_CL = _FM["clist"]
_SUG = _FM["suggest"]
_ORDER = _FM["orderbook"]
_BID_FIELDS = [tuple(p) for p in _ORDER["bid"]]       # 买5..买1
_ASK_FIELDS = [tuple(p) for p in _ORDER["ask"]]       # 卖5..卖1
_KLINE_COLS = {name: i for i, name in enumerate(_FM["kline_columns"])}
_TRENDS_COLS = {name: i for i, name in enumerate(_FM["trends_columns"])}
_SNAPSHOT_FIELDS = _PARAMS["snapshot"]["fields"]
_CLIST_FS = _PARAMS["clist"]["fs"]
_CLIST_FIELDS = _PARAMS["clist"]["fields"]
_SUGGEST_TOKEN = _PARAMS["suggest"]["token"]
_VOL_MULT = float(_DS.get("volume_multiplier", 100))  # 手 -> 股
SOURCE_LABEL = str(_DS.get("label", "东方财富"))


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


def _col(cols: dict[str, int], name: str, fallback: int) -> int:
    return cols.get(name, fallback)


def parse_snapshot(data: dict, code: str = "", pre_scaled: bool = True) -> Quote:
    """Map a ``stock/get`` payload (``data`` node) into a :class:`Quote`.

    ``pre_scaled=True`` matches ``fltt=2`` responses (floats already divided by
    the ``decimals`` scale).  Pass ``False`` for the integer form, where price
    fields must be divided by ``10**decimals``.
    """
    if not data:
        return Quote(code=code)
    code = str(data.get(_SM["code"]) or code)
    decimals = int(_num(data.get(_SM["decimals"]), 2))
    scale = 10.0 ** decimals

    def px(key: str) -> float:
        v = data.get(_SM[key])
        if v in (None, "-"):
            return 0.0
        v = float(v)
        return v if pre_scaled else v / scale

    ts = None
    if data.get(_SM["timestamp"]):
        try:
            ts = datetime.fromtimestamp(int(data[_SM["timestamp"]]))
        except (ValueError, OSError, TypeError):
            ts = None

    return Quote(
        code=code,
        name=str(data.get(_SM["name"]) or ""),
        price=px("price"),
        prev_close=px("prev_close"),
        open=px("open"),
        high=px("high"),
        low=px("low"),
        volume=_num(data.get(_SM["volume"])) * _VOL_MULT,
        amount=_num(data.get(_SM["amount"])),
        turnover=_num(data.get(_SM["turnover"])),
        ts=ts,
    )


def parse_orderbook(data: dict, code: str = "", pre_scaled: bool = True) -> OrderBook:
    """Map a ``stock/get`` payload into a 5-level :class:`OrderBook`."""
    if not data:
        return OrderBook(code=code)
    decimals = int(_num(data.get(_SM["decimals"]), 2))
    scale = 10.0 ** decimals

    def px(v):
        v = _num(v)
        return v if pre_scaled else v / scale

    asks = [OrderBookLevel(px(data.get(f"f{p}")), _num(data.get(f"f{v}")) * _VOL_MULT)
            for p, v in _ASK_FIELDS]        # 卖5..卖1
    asks.reverse()                          # -> index 0 == 卖1
    bids = [OrderBookLevel(px(data.get(f"f{p}")), _num(data.get(f"f{v}")) * _VOL_MULT)
            for p, v in _BID_FIELDS]        # 买5..买1
    bids.reverse()                          # -> index 0 == 买1
    pct = _num(data.get(_SM["pct"]))
    return OrderBook(
        code=str(data.get(_SM["code"]) or code),
        asks=asks, bids=bids,
        price=px(data.get(_SM["price"])),
        pct=pct if pre_scaled else pct / 100.0,
    )


def parse_kline(payload: dict, code: str = "") -> list[Bar]:
    """Map a ``kline/get`` payload into a list of :class:`Bar`.

    Column order comes from ``field_map.kline_columns``:
    date, open, close, high, low, volume(手), amount, ...
    """
    node = (payload or {}).get("data") or {}
    rows = node.get("klines") or []
    i_dt = _col(_KLINE_COLS, "dt", 0)
    i_o = _col(_KLINE_COLS, "open", 1)
    i_c = _col(_KLINE_COLS, "close", 2)
    i_h = _col(_KLINE_COLS, "high", 3)
    i_l = _col(_KLINE_COLS, "low", 4)
    i_v = _col(_KLINE_COLS, "volume", 5)
    i_a = _col(_KLINE_COLS, "amount", 6)
    bars: list[Bar] = []
    for row in rows:
        parts = next(csv.reader(io.StringIO(row)))
        if len(parts) <= max(i_o, i_c, i_h, i_l, i_v):
            continue
        try:
            raw_dt = parts[i_dt]
            dt = datetime.strptime(raw_dt, "%Y-%m-%d %H:%M" if " " in raw_dt else "%Y-%m-%d")
            bars.append(Bar(
                dt=dt,
                open=float(parts[i_o]),
                close=float(parts[i_c]),
                high=float(parts[i_h]),
                low=float(parts[i_l]),
                volume=float(parts[i_v]) * _VOL_MULT,
                amount=float(parts[i_a]) if len(parts) > i_a and parts[i_a] else 0.0,
            ))
        except ValueError:
            continue
    return bars


def parse_trends(payload: dict, code: str = "") -> list[Bar]:
    """Map a ``trends2/get`` payload (分时) into a list of :class:`Bar`.

    Column order comes from ``field_map.trends_columns``:
    time, open, close, high, low, volume(手), amount, avg_price.
    The trailing avg_price column has no :class:`Bar` slot and is ignored.
    """
    node = (payload or {}).get("data") or {}
    rows = node.get("klines") or []
    i_dt = _col(_TRENDS_COLS, "dt", 0)
    i_o = _col(_TRENDS_COLS, "open", 1)
    i_c = _col(_TRENDS_COLS, "close", 2)
    i_h = _col(_TRENDS_COLS, "high", 3)
    i_l = _col(_TRENDS_COLS, "low", 4)
    i_v = _col(_TRENDS_COLS, "volume", 5)
    i_a = _col(_TRENDS_COLS, "amount", 6)
    bars: list[Bar] = []
    for row in rows:
        parts = next(csv.reader(io.StringIO(row)))
        if len(parts) <= max(i_o, i_c, i_h, i_l, i_v):
            continue
        try:
            raw_dt = parts[i_dt]
            dt = datetime.strptime(raw_dt, "%Y-%m-%d %H:%M" if " " in raw_dt else "%Y-%m-%d")
            bars.append(Bar(
                dt=dt,
                open=float(parts[i_o]),
                close=float(parts[i_c]),
                high=float(parts[i_h]),
                low=float(parts[i_l]),
                volume=float(parts[i_v]) * _VOL_MULT,
                amount=float(parts[i_a]) if len(parts) > i_a and parts[i_a] else 0.0,
            ))
        except ValueError:
            continue
    return bars


def parse_clist(payload: dict) -> list[Quote]:
    """Map a ``clist/get`` payload into a list of :class:`Quote`.

    Row fields come from ``field_map.clist``.  Defensive: missing fields,
    ``"-"`` and suspended rows (price == ``"-"``) parse to zeros instead of
    raising; ``pct``/``change`` are derived by :class:`Quote` from
    price / prev_close.
    """
    node = (payload or {}).get("data") or {}
    diff = node.get("diff") or []
    if isinstance(diff, dict):            # single-row responses come back as a dict
        diff = [diff]
    quotes: list[Quote] = []
    for row in diff:
        if not isinstance(row, dict):
            continue
        code = str(row.get(_CL["code"]) or "").strip()
        if not code:
            continue
        quotes.append(Quote(
            code=code,
            name=str(row.get(_CL["name"]) or ""),
            price=_num(row.get(_CL["price"])),
            prev_close=_num(row.get(_CL["prev_close"])),
            open=_num(row.get(_CL["open"])),
            high=_num(row.get(_CL["high"])),
            low=_num(row.get(_CL["low"])),
            volume=_num(row.get(_CL["volume"])) * _VOL_MULT,
            amount=_num(row.get(_CL["amount"])),
            turnover=_num(row.get(_CL["turnover"])),
        ))
    return quotes


class EastMoneyClient:
    """Small, rate-limited client with retry/back-off.

    Request defaults (timeout / retries / min_interval / trust_env) come from
    ``data_sources.json``; pass an argument to override for one instance.
    Set ``trust_env=False`` to bypass a system proxy when it misbehaves.
    """

    def __init__(self, timeout: float | None = None, retries: int | None = None,
                 min_interval: float | None = None, trust_env: bool | None = None):
        req = _DS.get("request", {})
        self.timeout = req.get("timeout", 8.0) if timeout is None else timeout
        self.retries = req.get("retries", 3) if retries is None else retries
        self.min_interval = req.get("min_interval", 0.2) if min_interval is None else min_interval
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.session.trust_env = req.get("trust_env", True) if trust_env is None else trust_env
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

    # -- endpoints ---------------------------------------------------------
    def _snapshot_params(self, code: str) -> dict:
        params = dict(_PARAMS["snapshot"])
        params["secid"] = secid(code)
        return params

    def snapshot(self, code: str) -> Quote:
        payload = self._get(SNAPSHOT_URL, self._snapshot_params(code))
        return parse_snapshot(payload.get("data") or {}, code)

    def orderbook(self, code: str) -> OrderBook:
        payload = self._get(SNAPSHOT_URL, self._snapshot_params(code))
        return parse_orderbook(payload.get("data") or {}, code)

    def kline(self, code: str, period: str = "day", adjust: str = "pre",
              limit: int = 320) -> list[Bar]:
        params = dict(_PARAMS["kline"])
        params.update({
            "secid": secid(code),
            "klt": PERIODS.get(period, 101),
            "fqt": ADJUSTS.get(adjust, 1),
            "lmt": limit,
        })
        payload = self._get(KLINE_URL, params)
        return parse_kline(payload, code)

    def trends(self, code: str) -> list[Bar]:
        params = dict(_PARAMS["trends"])
        params["secid"] = secid(code)
        payload = self._get(TRENDS_URL, params)
        return parse_trends(payload, code)

    def clist(self, codes: list[str], fs: str | None = None,
              limit: int | None = None) -> list[Quote]:
        """Batch quotes for ``codes`` with a single ``clist/get`` request.

        The A-share universe matching ``fs`` is fetched in one round trip and
        filtered locally, so a 9-stock watchlist costs one request.  Pass a
        custom ``fs`` to narrow the universe (e.g. one board) or ``limit`` to
        cap the page size.
        """
        params = dict(_PARAMS["clist"])
        params["fs"] = fs or _CLIST_FS
        if limit is not None:
            params["pz"] = limit
        payload = self._get(LIST_URL, params)
        quotes = parse_clist(payload)
        if codes:
            wanted = set(codes)
            quotes = [q for q in quotes if q.code in wanted]
        return quotes

    def suggest(self, keyword: str, limit: int = 10) -> list[tuple[str, str]]:
        """Search suggestions (代码/名称 联想) as ``(code, name)`` tuples."""
        params = dict(_PARAMS["suggest"])
        params.update({"input": keyword, "count": limit})
        payload = self._get(SUGGEST_URL, params)
        table = (payload or {}).get(_SUG["root"]) or {}
        data = table.get(_SUG["list"]) or []
        out: list[tuple[str, str]] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            code, name = item.get(_SUG["code"]), item.get(_SUG["name"])
            if not code or not name:
                continue
            out.append((str(code), str(name)))
            if len(out) >= limit:
                break
        return out
