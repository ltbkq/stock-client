"""Cache for K-line series.

Primary backend is SQLite; key is ``(code, period, adjust)`` and only bars newer
than the stored ``last_dt`` need fetching on the next poll (incremental update).

Some minimal Python builds ship without the ``_sqlite3`` extension, so if the
import fails we transparently fall back to an in-process dict with the same API.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

from .models import Bar

try:                                     # pragma: no cover - depends on build
    import sqlite3
    HAVE_SQLITE = True
except ImportError:                      # pragma: no cover
    sqlite3 = None
    HAVE_SQLITE = False

_SCHEMA = """
CREATE TABLE IF NOT EXISTS bars (
    code TEXT NOT NULL,
    period TEXT NOT NULL,
    adjust TEXT NOT NULL,
    dt TEXT NOT NULL,
    open REAL, high REAL, low REAL, close REAL,
    volume REAL, amount REAL,
    PRIMARY KEY (code, period, adjust, dt)
);
CREATE INDEX IF NOT EXISTS idx_bars_key ON bars(code, period, adjust, dt);
"""

_FMT = "%Y-%m-%d %H:%M:%S"


class BarCache:
    backend = "sqlite" if HAVE_SQLITE else "memory"

    def __init__(self, path: str | Path):
        self.path = str(path)
        self._lock = threading.Lock()
        self._mem: OrderedDict[tuple, list[Bar]] = OrderedDict()
        self._conn = None
        if HAVE_SQLITE:
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(self.path, check_same_thread=False)
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    # -- writes ------------------------------------------------------------
    def save(self, code: str, period: str, adjust: str, bars: list[Bar]) -> None:
        if not bars:
            return
        if self._conn is None:
            with self._lock:
                merged = {b.dt: b for b in self._mem.get((code, period, adjust), [])}
                merged.update({b.dt: b for b in bars})
                self._mem[(code, period, adjust)] = [merged[k] for k in sorted(merged)]
                self._mem.move_to_end((code, period, adjust))
            return
        rows = [(code, period, adjust, b.dt.strftime(_FMT),
                 b.open, b.high, b.low, b.close, b.volume, b.amount) for b in bars]
        with self._lock:
            self._conn.executemany(
                "INSERT OR REPLACE INTO bars VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
            self._conn.commit()

    # -- reads -------------------------------------------------------------
    def load(self, code: str, period: str, adjust: str, limit: int = 1000) -> list[Bar]:
        if self._conn is None:
            with self._lock:
                return list(self._mem.get((code, period, adjust), []))[-limit:]
        with self._lock:
            cur = self._conn.execute(
                "SELECT dt,open,high,low,close,volume,amount FROM bars "
                "WHERE code=? AND period=? AND adjust=? ORDER BY dt DESC LIMIT ?",
                (code, period, adjust, limit))
            rows = cur.fetchall()
        out = []
        for dt, o, h, l, c, v, a in reversed(rows):
            try:
                out.append(Bar(datetime.strptime(dt, _FMT), o, h, l, c, v, a))
            except ValueError:
                continue
        return out

    def last_dt(self, code: str, period: str, adjust: str) -> datetime | None:
        bars = self.load(code, period, adjust, limit=1)
        return bars[-1].dt if bars else None

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None


class LruCache:
    """Bounded dict with least-recently-used eviction (thread-safe)."""

    def __init__(self, capacity: int = 256):
        self.capacity = capacity
        self._data: OrderedDict = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            if key not in self._data:
                return None
            self._data.move_to_end(key)
            return self._data[key]

    def put(self, key, value) -> None:
        with self._lock:
            self._data[key] = value
            self._data.move_to_end(key)
            while len(self._data) > self.capacity:
                self._data.popitem(last=False)
