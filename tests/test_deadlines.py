from datetime import date
from counsel.deadlines import alerts, classify
from counsel.models import Dispute, Evidence, Reason


def _d(i, due, amount=500.0):
    ev = Evidence(avs_match=True, cvv_match=True, three_ds=True)
    return Dispute(i, "pi_" + i, amount, "USD", Reason.FRAUD, ev, due)


def test_classify():
    assert classify(-1, 3) == "missed"
    assert classify(0, 3) == "urgent"
    assert classify(3, 3) == "urgent"
    assert classify(4, 3) == "ok"


def test_alerts_order_and_levels():
    ds = [_d("a", "2026-11-10"), _d("b", "2026-11-02"), _d("c", "2026-10-30")]
    out = alerts(ds, date(2026, 11, 1), warn_days=3)
    assert [a.dispute_id for a in out] == ["c", "b", "a"]
    assert [a.level for a in out] == ["missed", "urgent", "ok"]


def test_accepted_disputes_are_skipped():
    out = alerts([_d("tiny", "2026-11-02", amount=1.0)], date(2026, 11, 1))
    assert out == []
