"""Triage queue: rank disputes by expected recovery and urgency, and render a review table.

Run: python3 -m counsel.queue [--fee 15] [--json]
"""
from __future__ import annotations
import argparse
import json
from dataclasses import dataclass
from .models import Dispute
from .playbooks import win_likelihood, recommend
from .seed import SEED

DEFAULT_FEE = 15.0  # assumed per-dispute handling cost in the dispute currency


@dataclass
class QueueItem:
    dispute: Dispute
    p_win: float
    action: str
    expected_value: float


def expected_value(d: Dispute, fee: float = DEFAULT_FEE) -> float:
    """Expected net recovery from contesting: p(win) * amount - handling fee."""
    return round(win_likelihood(d) * d.amount - fee, 2)


def build_queue(disputes: list[Dispute], fee: float = DEFAULT_FEE) -> list[QueueItem]:
    items = []
    for d in disputes:
        ev = expected_value(d, fee)
        action = recommend(d)
        if action == "contest" and ev <= 0:
            action = "accept"  # winnable but not worth the cost
        items.append(QueueItem(d, win_likelihood(d), action, ev))
    # contest items first, earliest due date, then highest expected value
    items.sort(key=lambda i: (i.action != "contest", i.dispute.due_date, -i.expected_value))
    return items


def render(items: list[QueueItem]) -> str:
    rows = ["| Dispute | Reason | Amount | Due | P(win) | EV | Action |",
            "|---|---|---|---|---|---|---|"]
    for i in items:
        d = i.dispute
        rows.append(f"| {d.id} | {d.reason.value} | {d.amount:.2f} {d.currency} | {d.due_date} | "
                    f"{i.p_win:.2f} | {i.expected_value:.2f} | {i.action} |")
    contest = sum(1 for i in items if i.action == "contest")
    rows.append(f"\n{contest} to contest (pending merchant approval), {len(items) - contest} to accept.")
    return "\n".join(rows)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fee", type=float, default=DEFAULT_FEE)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    items = build_queue(SEED, a.fee)
    if a.json:
        print(json.dumps([{"id": i.dispute.id, "p_win": i.p_win, "ev": i.expected_value,
                           "action": i.action} for i in items], indent=2))
    else:
        print(render(items))


if __name__ == "__main__":
    main()
