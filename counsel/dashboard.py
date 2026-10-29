"""Static HTML approval dashboard (no server, no JS; safe to open offline or show in a demo).

Shows the ranked queue with deadlines, EV, the contest/accept call, evidence gaps and an Approve
control per dispute. The page itself cannot submit anything: Approve shows the command that records
an approval in data/approvals.json. Submitting to PayPal is a separate step that requires that record.

Run: python3 -m counsel.dashboard [--today YYYY-MM-DD] [--fee 15] [--out data/dashboard.html]
     python3 -m counsel.dashboard --approve PP-D-... --approver "Name"   # record an approval
"""
from __future__ import annotations
import argparse
import html
import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

from .approval import Approval, NotApproved, approve, require
from .deadlines import classify
from .gaps import evidence_gaps
from .models import Dispute
from .paypal import REASON_MAP
from .queue import DEFAULT_FEE, QueueItem, build_queue

APPROVALS_PATH = "data/approvals.json"
PAYPAL_REASON = {v: k for k, v in REASON_MAP.items()}
ACTION_FOR = {"contest": "provide_evidence", "accept": "accept_claim"}

CSS = ("body{font-family:system-ui,sans-serif;max-width:1180px;margin:2rem auto;padding:0 1rem;color:#1b1b1b}"
       "h1{color:#003087}table{border-collapse:collapse;width:100%;font-size:.92rem}"
       "th,td{border-bottom:1px solid #e3e3e3;padding:.45rem .5rem;text-align:left;vertical-align:top}"
       "th{background:#f3f6fb}td.num{text-align:right;white-space:nowrap}"
       "code{background:#f3f3f3;padding:.1rem .3rem;border-radius:4px;font-size:.85rem}"
       "ul{margin:0;padding-left:1.1rem}summary{cursor:pointer;color:#0070e0;font-weight:600}"
       ".missed{color:#b00020;font-weight:600}.urgent{color:#b35c00;font-weight:600}"
       ".approved{color:#1a7f37;font-weight:600}"
       ".banner{background:#fff4e5;border-left:4px solid #ff8a00;padding:.6rem 1rem;margin:1rem 0}")


def load_approvals(path: str = APPROVALS_PATH) -> list[Approval]:
    p = Path(path)
    return [Approval(**r) for r in json.loads(p.read_text())] if p.exists() else []


def record_approval(dispute_id: str, action: str, approver: str, path: str = APPROVALS_PATH) -> Approval:
    a = approve(dispute_id, action, approver)
    rows = [asdict(x) for x in load_approvals(path)] + [asdict(a)]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(rows, indent=2) + "\n")
    return a


def find_approval(approvals: list[Approval], dispute_id: str, action: str) -> Approval | None:
    """Latest approval that passes approval.require for this dispute and action, else None."""
    for a in reversed(approvals):
        try:
            require(a, dispute_id, action)
            return a
        except NotApproved:
            continue
    return None


def _deadline(d: Dispute, today: date) -> tuple[str, str]:
    """(cell html, css class) for the evidence due date."""
    if not d.due_date:
        return "no deadline given", ""
    left = (date.fromisoformat(d.due_date) - today).days
    level = classify(left, 3)
    note = f"missed {-left} d ago" if left < 0 else f"{left} d left"
    return f"{html.escape(d.due_date)}<br>{note}", level if level != "ok" else ""


def _gaps(d: Dispute) -> str:
    gaps = evidence_gaps(d)[:3]
    if not gaps:
        return "none"
    return "<ul>" + "".join(f"<li><code>{html.escape(g.field)}</code> +{g.gain:.2f}</li>" for g in gaps) + "</ul>"


def _approve_cell(item: QueueItem, approvals: list[Approval]) -> str:
    d, action = item.dispute, ACTION_FOR[item.action]
    a = find_approval(approvals, d.id, action)
    if a:
        return (f"<span class='approved'>Approved</span> <code>{action}</code><br>by {html.escape(a.approver)}, "
                f"{html.escape(a.approved_at)}<br>Not submitted from this page.")
    cmd = f'python3 -m counsel.dashboard --approve {d.id} --action {action} --approver "Your name"'
    return (f"<details><summary>Approve</summary>Not approved. To record approval of "
            f"<code>{action}</code>, run:<br><code>{html.escape(cmd)}</code><br>"
            f"This page cannot submit to PayPal.</details>")


def build_dashboard(disputes: list[Dispute], fee: float = DEFAULT_FEE, today: str | None = None,
                    approvals: list[Approval] | None = None) -> str:
    t = date.fromisoformat(today) if today else date.today()
    approvals = approvals or []
    items = build_queue(disputes, fee)
    rows = []
    for n, i in enumerate(items, 1):
        d = i.dispute
        due, cls = _deadline(d, t)
        rows.append(
            "<tr>"
            f"<td>{n}</td><td><code>{html.escape(d.id)}</code><br>{html.escape(d.status)}</td>"
            f"<td>{html.escape(PAYPAL_REASON.get(d.reason, d.reason.value))}</td>"
            f"<td class='num'>{d.amount:.2f} {html.escape(d.currency)}</td>"
            f"<td class='{cls}'>{due}</td>"
            f"<td class='num'>{i.p_win:.2f}</td><td class='num'>{i.expected_value:.2f}</td>"
            f"<td><strong>{i.action}</strong></td><td>{_gaps(d)}</td>"
            f"<td>{_approve_cell(i, approvals)}</td>"
            "</tr>")
    contest = sum(1 for i in items if i.action == "contest")
    approved = sum(1 for i in items if find_approval(approvals, i.dispute.id, ACTION_FOR[i.action]))
    banner = ('<div class="banner">Approval-gated: nothing is sent to PayPal until the merchant records an '
              'approval for that dispute and action. This page is read-only and submits nothing.</div>')
    head = ("<tr><th>#</th><th>Dispute</th><th>PayPal reason</th><th>Amount</th><th>Evidence due</th>"
            "<th>P(win)</th><th>EV</th><th>Call</th><th>Top evidence gaps</th><th>Approval</th></tr>")
    summary = (f"<p>{len(items)} disputes: {contest} to contest, {len(items) - contest} to accept. "
               f"{approved} approved, {len(items) - approved} awaiting approval. As of {t.isoformat()}.</p>")
    notes = (f"<p>P(win) is a playbook score from the evidence on hand, not a measured win rate. "
             f"EV = P(win) &times; amount &minus; {fee:.2f} assumed handling cost. "
             f"Gaps list missing evidence and how much each would add to P(win).</p>")
    return ("<!doctype html><html><head><meta charset='utf-8'><title>Chargeback Counsel</title>"
            f"<style>{CSS}</style></head><body><h1>Chargeback Counsel: dispute queue</h1>{banner}{summary}"
            f"<table>{head}{''.join(rows)}</table>{notes}</body></html>\n")


def main(argv=None) -> None:
    from .seed import current
    ap = argparse.ArgumentParser(description="Write the static approval dashboard, or record an approval.")
    ap.add_argument("--fee", type=float, default=DEFAULT_FEE)
    ap.add_argument("--today")
    ap.add_argument("--out", default="data/dashboard.html")
    ap.add_argument("--approvals", default=APPROVALS_PATH)
    ap.add_argument("--approve", metavar="DISPUTE_ID")
    ap.add_argument("--action", choices=sorted(ACTION_FOR.values()), default="provide_evidence")
    ap.add_argument("--approver")
    a = ap.parse_args(argv)
    disputes = current()
    if a.approve:
        if a.approve not in {d.id for d in disputes}:
            ap.error(f"unknown dispute {a.approve}")
        if not a.approver:
            ap.error("--approver is required with --approve")
        rec = record_approval(a.approve, a.action, a.approver, a.approvals)
        print(f"recorded approval: {rec.action} on {rec.dispute_id} by {rec.approver} (not submitted)")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(build_dashboard(disputes, a.fee, a.today, load_approvals(a.approvals)))
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
