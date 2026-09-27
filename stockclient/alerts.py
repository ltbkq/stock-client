"""Pure-python alert rule engine (no Qt) so it is easy to unit-test.

Rules are evaluated on each new snapshot; a rule that is already satisfied is
not re-fired until it goes false again (edge-triggered), which prevents an
alert storm while a price stays beyond a threshold.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import Alert, Quote


@dataclass(slots=True)
class Trigger:
    alert: Alert
    price: float
    message: str


def _satisfied(alert: Alert, q: Quote) -> bool:
    if alert.kind == "price_above":
        return q.price >= alert.threshold
    if alert.kind == "price_below":
        return q.price <= alert.threshold
    if alert.kind == "pct_above":
        return q.pct >= alert.threshold
    if alert.kind == "pct_below":
        return q.pct <= alert.threshold
    return False


class AlertEngine:
    def __init__(self, alerts: list[Alert] | None = None):
        self.alerts: list[Alert] = list(alerts or [])
        self._fired: set[int] = set()   # ids of alerts currently satisfied

    def add(self, alert: Alert) -> None:
        self.alerts.append(alert)

    def remove(self, alert: Alert) -> None:
        if alert in self.alerts:
            self.alerts.remove(alert)

    def evaluate(self, q: Quote) -> list[Trigger]:
        out: list[Trigger] = []
        for a in self.alerts:
            if not a.enabled or a.code != q.code:
                continue
            hit = _satisfied(a, q)
            key = id(a)
            if hit and key not in self._fired:
                self._fired.add(key)
                out.append(Trigger(a, q.price, f"{q.name or q.code} {a.label()} @ {q.price:g}"))
            elif not hit:
                self._fired.discard(key)
        return out
