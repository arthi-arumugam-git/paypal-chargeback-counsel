"""Dispute sources: built-in synthetic SEED, offline PayPal-shaped fixtures, or the PayPal sandbox.

Run: python3 -m counsel.seed --source mock|paypal [--out data/disputes.json]
Writes the mapped disputes to --out; queue/deadlines/packet/gaps read that file.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from .models import Dispute, Evidence, Reason

MOCK_PATH = Path(__file__).resolve().parent.parent / "data" / "mock_paypal_disputes.json"
DEFAULT_OUT = "data/disputes.json"

E = Evidence
SEED = [
    Dispute("dsp_001", "int_001", 129.0, "USD", Reason.FRAUD, E(three_ds=True, avs_match=True), "2026-11-10"),
    Dispute("dsp_002", "int_002", 54.5, "USD", Reason.FRAUD, E(cvv_match=True), "2026-11-11"),
    Dispute("dsp_003", "int_003", 220.0, "AUD", Reason.NOT_RECEIVED, E(tracking_delivered=True, signature=True), "2026-11-12"),
    Dispute("dsp_004", "int_004", 75.0, "AUD", Reason.NOT_RECEIVED, E(), "2026-11-12"),
    Dispute("dsp_005", "int_005", 310.0, "GBP", Reason.NOT_AS_DESCRIBED, E(product_matches_listing=True, customer_comms=["Offered return"]), "2026-11-13"),
    Dispute("dsp_006", "int_006", 42.0, "GBP", Reason.NOT_AS_DESCRIBED, E(terms_accepted=True), "2026-11-13"),
    Dispute("dsp_007", "int_007", 99.0, "USD", Reason.DUPLICATE, E(second_charge_distinct=True), "2026-11-14"),
    Dispute("dsp_008", "int_008", 99.0, "USD", Reason.DUPLICATE, E(refund_issued=True), "2026-11-14"),
    Dispute("dsp_009", "int_009", 19.0, "SGD", Reason.SUBSCRIPTION_CANCELLED, E(terms_accepted=True, customer_comms=["No cancel request"]), "2026-11-15"),
    Dispute("dsp_010", "int_010", 19.0, "SGD", Reason.SUBSCRIPTION_CANCELLED, E(cancel_before_charge=True, terms_accepted=True), "2026-11-15"),
]


def dump(disputes: list[Dispute] = SEED, path: str = DEFAULT_OUT) -> None:
    def enc(d):
        x = d.__dict__.copy(); x["reason"] = d.reason.value; x["evidence"] = d.evidence.__dict__; return x
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps([enc(d) for d in disputes], indent=2) + "\n")


def load(path: str = DEFAULT_OUT) -> list[Dispute]:
    rows = json.loads(Path(path).read_text())
    return [Dispute(**{**r, "reason": Reason(r["reason"]), "evidence": Evidence(**r["evidence"])}) for r in rows]


def current(path: str = DEFAULT_OUT) -> list[Dispute]:
    """Disputes written by the last `counsel.seed` run, or the built-in SEED if none."""
    return load(path) if Path(path).exists() else SEED


def from_mock(path: Path = MOCK_PATH) -> list[Dispute]:
    from .paypal import from_paypal
    doc = json.loads(Path(path).read_text())
    records = doc.get("merchant_records", {})
    return [from_paypal(item, Evidence(**records.get(item["dispute_id"], {}))) for item in doc["items"]]


def from_paypal_api(client=None, dispute_state: str | None = "REQUIRED_ACTION") -> list[Dispute]:
    from .paypal import PayPalClient, UnsupportedReason, from_paypal
    client = client or PayPalClient.from_env()
    out = []
    # TODO: follow links/next_page_token; one page is enough for the sandbox demo.
    for summary in client.list_disputes(dispute_state=dispute_state, page_size=50).get("items", []):
        detail = client.get_dispute(summary["dispute_id"])  # list items lack disputed_transactions
        try:
            # TODO: merchant-side evidence (tracking, order records) is not wired yet; starts empty.
            out.append(from_paypal(detail))
        except UnsupportedReason as e:
            print(f"skip: {e}", file=sys.stderr)
    return out


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Load disputes and write them for the queue.")
    ap.add_argument("--source", choices=["mock", "paypal", "seed"], default="mock")
    ap.add_argument("--out", default=DEFAULT_OUT)
    a = ap.parse_args(argv)
    try:
        disputes = {"mock": from_mock, "paypal": from_paypal_api, "seed": lambda: SEED}[a.source]()
    except RuntimeError as e:
        sys.exit(f"error: {e}")
    dump(disputes, a.out)
    print(f"{len(disputes)} disputes from {a.source} -> {a.out}")


if __name__ == "__main__":
    main()
