from counsel.gaps import evidence_gaps, flips_to_contest, report
from counsel.models import Dispute, Evidence, Reason
from counsel.seed import SEED


def d(reason, **ev):
    return Dispute("x", "int", 10.0, "USD", reason, Evidence(**ev), "2026-11-20")


def test_not_received_with_nothing_ranks_tracking_first_and_flips():
    x = d(Reason.NOT_RECEIVED)
    gaps = evidence_gaps(x)
    assert gaps[0].field == "tracking_delivered" and gaps[0].gain == 0.6
    assert flips_to_contest(x) == ["tracking_delivered"]


def test_full_evidence_has_no_gaps():
    x = d(Reason.DUPLICATE, second_charge_distinct=True, refund_issued=True)
    assert evidence_gaps(x) == []


def test_cancel_before_charge_never_flips():
    x = d(Reason.SUBSCRIPTION_CANCELLED, cancel_before_charge=True)
    assert evidence_gaps(x) == [] and flips_to_contest(x) == []


def test_list_field_gap_counts():
    x = d(Reason.NOT_RECEIVED, tracking_delivered=True, signature=True)
    assert [g.field for g in evidence_gaps(x)] == ["customer_comms"]


def test_already_contest_has_no_flips():
    x = d(Reason.FRAUD, three_ds=True, avs_match=True)
    assert flips_to_contest(x) == []


def test_report_covers_all_seed():
    r = report(SEED)
    assert all(s.id in r for s in SEED)
