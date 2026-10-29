"""Per-dispute evidence packet: one reviewable file per dispute for the merchant to approve.

Each packet bundles the recommendation, win likelihood, expected value, evidence on hand vs missing,
the draft rebuttal, and an approval block that starts unsigned. Nothing is submitted from here.
Run: python3 -m counsel.packet [--fee 15] [--out data/packets] [--json]
"""
from __future__ import annotations
import argparse
import json
import os
from dataclasses import asdict, fields

from .models import Dispute
from .playbooks import PLAYBOOKS, win_likelihood, recommend, draft_rebuttal, _has
from .gaps import evidence_gaps
from .queue import DEFAULT_FEE, expected_value


def build_packet(d: Dispute, fee: float = DEFAULT_FEE) -> dict:
    relevant = [k for k, _w, _t in PLAYBOOKS[d.reason]]
    on_hand = [k for k in relevant if _has(d.evidence, k)]
    return {
        "dispute_id": d.id,
        "payment_intent_id": d.payment_intent_id,
        "amount": d.amount,
        "currency": d.currency,
        "reason": d.reason.value,
        "due_date": d.due_date,
        "p_win": round(win_likelihood(d), 2),
        "expected_value": expected_value(d, fee),
        "recommendation": recommend(d),
        "evidence_on_hand": on_hand,
        "evidence_missing": [{"field": g.field, "gain": g.gain, "why": g.why} for g in evidence_gaps(d)],
        "rebuttal_draft": draft_rebuttal(d),
        "approval": {"approved": False, "approver": None, "submitted": False},
    }


def render_packet(p: dict) -> str:
    missing = "\n".join(f"- {m['field']} (+{m['gain']:.2f}): {m['why']}" for m in p["evidence_missing"]) or "- none"
    on_hand = "\n".join(f"- {k}" for k in p["evidence_on_hand"]) or "- none"
    return "\n".join([
        f"# Evidence packet: {p['dispute_id']}", "",
        f"Payment {p['payment_intent_id']}, {p['amount']:.2f} {p['currency']}, reason {p['reason']}, "
        f"evidence due {p['due_date']}.", "",
        f"Recommendation: **{p['recommendation']}** (win likelihood {p['p_win']:.2f}, "
        f"expected net {p['expected_value']:.2f} {p['currency']}).", "",
        "## Evidence on hand", "", on_hand, "",
        "## Evidence still missing", "", missing, "",
        "## Draft rebuttal", "", p["rebuttal_draft"], "",
        "## Approval", "", "- [ ] Merchant approves submission (name, date): ________", "",
        "Not submitted. Chargeback Counsel only submits after explicit merchant approval.", "",
    ])


def write_packets(disputes: list[Dispute], out_dir: str, fee: float = DEFAULT_FEE, as_json: bool = False) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for d in disputes:
        p = build_packet(d, fee)
        ext = "json" if as_json else "md"
        path = os.path.join(out_dir, f"{d.id}.{ext}")
        with open(path, "w") as f:
            f.write(json.dumps(p, indent=2) if as_json else render_packet(p))
        paths.append(path)
    return paths


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fee", type=float, default=DEFAULT_FEE)
    ap.add_argument("--out", default="data/packets")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    from .seed import SEED
    for p in write_packets(SEED, a.out, a.fee, a.json):
        print(p)


if __name__ == "__main__":
    main()
