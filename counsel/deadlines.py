"""Deadline alerts: flag contest-worthy disputes whose evidence due date is close or already missed.

A missed evidence deadline is an automatic loss, so the agent surfaces these first for merchant approval.
Run: python3 -m counsel.deadlines [--today 2026-11-01] [--warn-days 3]
"""
from __future__ import annotations
import argparse
from dataclasses import dataclass
from datetime import date
from .queue import build_queue, DEFAULT_FEE
from .models import Dispute
from .seed import SEED


@dataclass
class Alert:
    dispute_id: str
    days_left: int
    level: str  # "missed" | "urgent" | "ok"
    amount: float
    currency: str


def classify(days_left: int, warn_days: int) -> str:
    if days_left < 0:
        return "missed"
    if days_left <= warn_days:
        return "urgent"
    return "ok"


def alerts(disputes: list[Dispute], today: date, warn_days: int = 3, fee: float = DEFAULT_FEE) -> list[Alert]:
    out = []
    for item in build_queue(disputes, fee):
        if item.action != "contest":
            continue
        d = item.dispute
        left = (date.fromisoformat(d.due_date) - today).days
        out.append(Alert(d.id, left, classify(left, warn_days), d.amount, d.currency))
    order = {"missed": 0, "urgent": 1, "ok": 2}
    out.sort(key=lambda a: (order[a.level], a.days_left))
    return out


def render(items: list[Alert]) -> str:
    lines = ["| Dispute | Days left | Level | Amount |", "|---|---|---|---|"]
    for a in items:
        lines.append(f"| {a.dispute_id} | {a.days_left} | {a.level} | {a.amount:.2f} {a.currency} |")
    urgent = sum(1 for a in items if a.level == "urgent")
    missed = sum(1 for a in items if a.level == "missed")
    lines.append(f"\n{urgent} urgent and {missed} missed contest-worthy disputes need merchant approval.")
    return "\n".join(lines)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--today", default=date.today().isoformat())
    ap.add_argument("--warn-days", type=int, default=3)
    a = ap.parse_args(argv)
    print(render(alerts(SEED, date.fromisoformat(a.today), a.warn_days)))


if __name__ == "__main__":
    main()
