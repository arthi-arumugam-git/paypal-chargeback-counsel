import json

import pytest

from counsel import dashboard, seed
from counsel.approval import approve
from counsel.queue import build_queue


def test_dashboard_shows_ranked_queue_with_paypal_reasons():
    ds = seed.from_mock()
    out = dashboard.build_dashboard(ds, today="2026-10-30")
    order = [i.dispute.id for i in build_queue(ds)]
    positions = [out.index(f"<code>{i}</code>") for i in order]
    assert positions == sorted(positions)
    assert "MERCHANDISE_OR_SERVICE_NOT_RECEIVED" in out and "CREDIT_NOT_PROCESSED" in out
    for col in ("Evidence due", "P(win)", "EV", "Call", "Top evidence gaps", "Approval"):
        assert f"<th>{col}</th>" in out


def test_dashboard_is_static_and_cannot_submit():
    out = dashboard.build_dashboard(seed.from_mock(), today="2026-10-30")
    low = out.lower()
    assert "<script" not in low and "<form" not in low and "http" not in low
    assert out.count("<summary>Approve</summary>") == len(seed.from_mock())


def test_deadline_levels():
    out = dashboard.build_dashboard(seed.SEED, today="2026-11-12")
    assert "missed 2 d ago" in out and "0 d left" in out
    assert "class='missed'" in out and "class='urgent'" in out


def test_missing_due_date_is_labelled():
    d = seed.SEED[0]
    from dataclasses import replace
    out = dashboard.build_dashboard([replace(d, due_date="")], today="2026-10-30")
    assert "no deadline given" in out


def test_approval_only_counts_for_matching_dispute_and_action():
    ds = seed.from_mock()
    items = {i.dispute.id: i for i in build_queue(ds)}
    contest_id = next(k for k, i in items.items() if i.action == "contest")
    wrong_action = approve(contest_id, "accept_claim", "Alex")
    out = dashboard.build_dashboard(ds, today="2026-10-30", approvals=[wrong_action])
    assert "0 approved" in out
    ok = approve(contest_id, "provide_evidence", "Alex")
    out = dashboard.build_dashboard(ds, today="2026-10-30", approvals=[wrong_action, ok])
    assert "1 approved" in out and "by Alex" in out and "Not submitted from this page." in out


def test_cli_writes_dashboard_and_records_approval(tmp_path, monkeypatch):
    monkeypatch.setattr(seed, "current", lambda path=None: seed.from_mock())
    out, appr = tmp_path / "dash.html", tmp_path / "approvals.json"
    args = ["--out", str(out), "--approvals", str(appr), "--today", "2026-10-30"]
    dashboard.main(args)
    assert "0 approved" in out.read_text() and not appr.exists()
    dashboard.main(args + ["--approve", "PP-D-SYNTH-0001", "--approver", "Alex"])
    rec = json.loads(appr.read_text())
    assert rec[0]["dispute_id"] == "PP-D-SYNTH-0001" and rec[0]["action"] == "provide_evidence"
    assert "1 approved" in out.read_text()


def test_cli_rejects_unknown_dispute_and_missing_approver(tmp_path, monkeypatch):
    monkeypatch.setattr(seed, "current", lambda path=None: seed.from_mock())
    base = ["--out", str(tmp_path / "d.html"), "--approvals", str(tmp_path / "a.json")]
    with pytest.raises(SystemExit):
        dashboard.main(base + ["--approve", "NOPE", "--approver", "Alex"])
    with pytest.raises(SystemExit):
        dashboard.main(base + ["--approve", "PP-D-SYNTH-0001"])
    assert not (tmp_path / "a.json").exists()
