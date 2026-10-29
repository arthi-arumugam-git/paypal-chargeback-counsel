"""Ten synthetic disputes across reason codes for offline development and evals."""
import json
from pathlib import Path
from .models import Dispute, Evidence, Reason

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


def dump(path: str = "data/disputes.json") -> None:
    def enc(d):
        x = d.__dict__.copy(); x["reason"] = d.reason.value; x["evidence"] = d.evidence.__dict__; return x
    Path(path).write_text(json.dumps([enc(d) for d in SEED], indent=2))


if __name__ == "__main__":
    dump()
