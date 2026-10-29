import pytest
from counsel.seed import SEED
from counsel.playbooks import win_likelihood, recommend, draft_rebuttal
from counsel.approval import Submission, NotApproved

by = {d.id: d for d in SEED}

def test_strong_fraud_contest():
    assert recommend(by["dsp_001"]) == "contest"

def test_empty_not_received_accept():
    assert win_likelihood(by["dsp_004"]) == 0.0 and recommend(by["dsp_004"]) == "accept"

def test_cancel_before_charge_forces_accept():
    assert recommend(by["dsp_010"]) == "accept"

def test_rebuttal_is_draft_and_cites_evidence():
    t = draft_rebuttal(by["dsp_003"])
    assert "awaiting merchant approval" in t and "tracking" in t.lower()

class FakeClient:
    def __init__(self): self.calls = []
    def submit_evidence(self, did, text): self.calls.append(did); return {"ok": True}

def test_no_submit_without_approval():
    c = FakeClient(); s = Submission("dsp_001", "x")
    with pytest.raises(NotApproved): s.submit(c)
    assert c.calls == []
    s.approve("merchant@example.com"); assert s.submit(c) == {"ok": True}

def test_all_seeds_scored_in_range():
    assert all(0.0 <= win_likelihood(d) <= 1.0 for d in SEED) and len(SEED) == 10
