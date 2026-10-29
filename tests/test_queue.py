from counsel.queue import build_queue, expected_value
from counsel.seed import SEED


def test_contest_items_first_and_sorted_by_due():
    q = build_queue(SEED)
    actions = [i.action for i in q]
    assert actions == sorted(actions, key=lambda a: a != "contest")
    dues = [i.dispute.due_date for i in q if i.action == "contest"]
    assert dues == sorted(dues)


def test_cancel_before_charge_is_accepted():
    q = {i.dispute.id: i for i in build_queue(SEED)}
    assert q["dsp_010"].action == "accept"


def test_low_value_winnable_dispute_accepted_when_fee_exceeds_ev():
    d = next(x for x in SEED if x.id == "dsp_009")
    assert expected_value(d, fee=100) < 0
    q = {i.dispute.id: i for i in build_queue(SEED, fee=100)}
    assert q["dsp_009"].action == "accept"
