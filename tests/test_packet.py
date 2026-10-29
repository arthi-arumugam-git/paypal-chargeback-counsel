import json
from counsel.models import Dispute, Evidence, Reason
from counsel.packet import build_packet, render_packet, write_packets
from counsel.seed import SEED


def test_packet_starts_unapproved_and_lists_gaps():
    d = Dispute("dp1", "int_1", 100.0, "USD", Reason.NOT_RECEIVED, Evidence(), "2026-11-20")
    p = build_packet(d)
    assert p["approval"] == {"approved": False, "approver": None, "submitted": False}
    assert p["evidence_on_hand"] == []
    assert p["evidence_missing"][0]["field"] == "tracking_delivered"
    assert "Not submitted" in render_packet(p)


def test_on_hand_evidence_reported():
    d = Dispute("dp2", "int_2", 50.0, "EUR", Reason.FRAUD, Evidence(three_ds=True, avs_match=True), "2026-11-20")
    p = build_packet(d)
    assert "three_ds" in p["evidence_on_hand"] and "avs_match" in p["evidence_on_hand"]
    assert p["currency"] == "EUR"


def test_write_packets_one_per_seed(tmp_path):
    paths = write_packets(SEED, str(tmp_path), as_json=True)
    assert len(paths) == len(SEED)
    data = json.loads(open(paths[0]).read())
    assert data["dispute_id"] == SEED[0].id
