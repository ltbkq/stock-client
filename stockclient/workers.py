"""Qt threading glue: blocking I/O runs in a QThreadPool, never on the UI thread.

``DataService`` abstracts demo vs. live sources; ``PollController`` owns a
QTimer that submits short-lived :class:`QRunnable` tasks and forwards results as
signals, so the main window only ever touches widgets on the UI thread.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal

from .alerts import AlertEngine
from .cache import BarCache, LruCache
from .config import AppConfig
from . import sample
from .models import Bar, OrderBook, Quote


class DataService:
    """Routes requests to the offline generator or the live client."""

    def __init__(self, cfg: AppConfig, client=None, cache: BarCache | None = None):
        self.cfg = cfg
        self.client = client
        self.cache = cache
        self._book_lru = LruCache(64)

    @property
    def offline(self) -> bool:
        return self.cfg.demo_mode or self.client is None

    def quote(self, code: str) -> Quote:
        if self.offline:
            return sample.quote(code)
        return self.client.snapshot(code)

    def orderbook(self, code: str) -> OrderBook:
        if self.offline:
            return sample.orderbook(code)
        try:
            book = self.client.orderbook(code)
        except Exception:
            return self._book_lru.get(code) or OrderBook(code=code)
        if book.bids or book.asks:
            self._book_lru.put(code, book)
        return book

    def bars(self, code: str, period: str, adjust: str, limit: int = 320) -> list[Bar]:
        if self.offline:
            return sample.intraday_bars(code) if period == "intraday" \
                else sample.daily_bars(code, 240)

        if period == "intraday":
            bars = self.client.trends(code)
        else:
            bars = self.client.kline(code, period, adjust, limit)
        if self.cache is not None:
            self.cache.save(code, period, adjust, bars)
        return bars


class _Task(QRunnable):
    """Runs ``fn`` in the pool and forwards the result to ``ok`` / ``err``."""

    def __init__(self, fn, ok, err):
        super().__init__()
        self._fn, self._ok, self._err = fn, ok, err
        self.setAutoDelete(True)

    def run(self) -> None:
        try:
            result = self._fn()
        except Exception as exc:                 # noqa: BLE001 - surface to UI
            self._err(str(exc))
            return
        self._ok(result)


class PollController(QObject):
    """Polls the current symbol and pushes updates to the UI via signals."""

    quoteReady = Signal(object)
    bookReady = Signal(object)
    barsReady = Signal(str, object)
    triggered = Signal(object)
    failed = Signal(str)

    def __init__(self, service: DataService, engine: AlertEngine, parent=None):
        super().__init__(parent)
        self.service = service
        self.engine = engine
        self.pool = QThreadPool.globalInstance()

        self.code = ""
        self.period = service.cfg.period
        self.adjust = service.cfg.adjust
        self.want_book = service.cfg.show_orderbook
        self._busy = False

        self.quoteReady.connect(self._check_alerts)   # main-thread slot

        self.timer = QTimer(self)
        self.timer.setInterval(max(1, service.cfg.refresh_seconds) * 1000)
        self.timer.timeout.connect(self._tick)

    # -- control -----------------------------------------------------------
    def set_symbol(self, code: str) -> None:
        self.code = code
        self.reload_series()
        self._tick()

    def set_period(self, period: str) -> None:
        self.period = period
        self.reload_series()

    def set_adjust(self, adjust: str) -> None:
        self.adjust = adjust
        self.reload_series()

    def set_orderbook(self, on: bool) -> None:
        self.want_book = on
        if on:
            self._tick()

    def start(self) -> None:
        self.timer.start()
        self.reload_series()
        self._tick()

    def stop(self) -> None:
        self.timer.stop()

    def refresh_now(self) -> None:
        self._tick()

    # -- internals ---------------------------------------------------------
    def reload_series(self) -> None:
        if not self.code:
            return
        code = self.code
        self.pool.start(_Task(
            lambda: (code, self.service.bars(code, self.period, self.adjust)),
            lambda res: self.barsReady.emit(*res),
            self.failed.emit,
        ))

    def _tick(self) -> None:
        if not self.code or self._busy:
            return
        self._busy = True
        code = self.code
        want_book = self.want_book

        def job():
            quote = self.service.quote(code)
            book = self.service.orderbook(code) if want_book else None
            return quote, book

        def ok(result) -> None:                  # runs in worker thread
            self._busy = False
            quote, book = result
            self.quoteReady.emit(quote)
            if book is not None:
                self.bookReady.emit(book)

        self.pool.start(_Task(job, ok, self._fail))

    def _fail(self, message: str) -> None:       # runs in worker thread
        self._busy = False
        self.failed.emit(message)

    def _check_alerts(self, quote: Quote) -> None:      # main thread
        for trig in self.engine.evaluate(quote):
            self.triggered.emit(trig)
