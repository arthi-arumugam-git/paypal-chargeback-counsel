import base64
import io
import json
import urllib.error
import urllib.parse

import pytest

from counsel import seed
from counsel.approval import Approval, NotApproved, approve
from counsel.models import Evidence, Reason
from counsel.paypal import PayPalClient, PayPalError, UnsupportedReason, from_paypal
from counsel.queue import build_queue


def pp(reason, **kw):
    d = {
        "dispute_id": "PP-D-1",
        "reason": reason,
        "status": "WAITING_FOR_SELLER_RESPONSE",
        "dispute_amount": {"currency_code": "USD", "value": "12.34"},
        "seller_response_due_date": "2026-11-05T23:59:59.000Z",
        "disputed_transactions": [{"seller_transaction_id": "TXN1", "buyer_transaction_id": "BTXN1"}],
    }
    d.update(kw)
    return d


# mapper

@pytest.mark.parametrize("pp_reason,reason", [
    ("MERCHANDISE_OR_SERVICE_NOT_RECEIVED", Reason.NOT_RECEIVED),
    ("MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED", Reason.NOT_AS_DESCRIBED),
    ("UNAUTHORISED", Reason.FRAUD),
    ("DUPLICATE_TRANSACTION", Reason.DUPLICATE),
    ("INCORRECT_AMOUNT", Reason.INCORRECT_AMOUNT),
    ("CREDIT_NOT_PROCESSED", Reason.CREDIT_NOT_PROCESSED),
])
def test_mapper_per_reason(pp_reason, reason):
    d = from_paypal(pp(pp_reason))
    assert d.reason == reason
    assert (d.id, d.payment_intent_id, d.amount, d.currency) == ("PP-D-1", "TXN1", 12.34, "USD")
    assert d.due_date == "2026-11-05" and d.status == "WAITING_FOR_SELLER_RESPONSE"
    assert d.evidence == Evidence()


def test_mapper_rejects_reason_without_playbook():
    with pytest.raises(UnsupportedReason):
        from_paypal(pp("PROBLEM_WITH_REMITTANCE"))


def test_mapper_handles_list_summary_without_transactions_or_due_date():
    d = from_paypal(pp("UNAUTHORISED", disputed_transactions=None, seller_response_due_date=None))
    assert d.payment_intent_id == "" and d.due_date == ""


def test_mapper_keeps_merchant_evidence():
    d = from_paypal(pp("MERCHANDISE_OR_SERVICE_NOT_RECEIVED"), Evidence(tracking_delivered=True))
    assert d.evidence.tracking_delivered


def test_mock_fixtures_load_and_rank():
    ds = seed.from_mock()
    assert len(ds) == 5 and all(d.id.startswith("PP-D-SYNTH-") for d in ds)
    assert {d.reason for d in ds} >= {Reason.NOT_RECEIVED, Reason.FRAUD, Reason.CREDIT_NOT_PROCESSED}
    actions = {i.dispute.id: i.action for i in build_queue(ds)}
    assert actions["PP-D-SYNTH-0001"] == "contest" and actions["PP-D-SYNTH-0005"] == "accept"


def test_seed_cli_mock_roundtrip(tmp_path):
    out = tmp_path / "disputes.json"
    seed.main(["--source", "mock", "--out", str(out)])
    assert seed.load(str(out)) == seed.from_mock()


# client

class Resp(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): self.close()


class FakeOpener:
    def __init__(self, responses=None):
        self.requests = []
        self.responses = list(responses or [])

    def __call__(self, req, timeout=None):
        self.requests.append(req)
        if req.full_url.endswith("/v1/oauth2/token"):
            return Resp(json.dumps({"access_token": "TOKEN", "expires_in": 3600}).encode())
        body = self.responses.pop(0) if self.responses else {}
        if isinstance(body, Exception):
            raise body
        return Resp(json.dumps(body).encode())


def client(opener):
    return PayPalClient("cid", "secret", "sandbox", opener=opener)


def test_oauth_client_credentials_request_and_token_cache():
    op = FakeOpener([{"items": []}, {"items": []}])
    c = client(op)
    c.list_disputes(); c.list_disputes()
    tok = op.requests[0]
    assert tok.full_url == "https://api-m.sandbox.paypal.com/v1/oauth2/token"
    assert tok.get_method() == "POST" and tok.data == b"grant_type=client_credentials"
    assert tok.get_header("Authorization") == "Basic " + base64.b64encode(b"cid:secret").decode()
    assert tok.get_header("Content-type") == "application/x-www-form-urlencoded"
    assert len(op.requests) == 3  # one token fetch, two API calls


def test_list_disputes_request():
    op = FakeOpener([{"items": [{"dispute_id": "PP-D-1"}]}])
    out = client(op).list_disputes(dispute_state="REQUIRED_ACTION", page_size=10)
    req = op.requests[1]
    url = urllib.parse.urlsplit(req.full_url)
    assert (url.netloc, url.path) == ("api-m.sandbox.paypal.com", "/v1/customer/disputes")
    assert urllib.parse.parse_qs(url.query) == {"dispute_state": ["REQUIRED_ACTION"], "page_size": ["10"]}
    assert req.get_method() == "GET" and req.get_header("Authorization") == "Bearer TOKEN"
    assert out["items"][0]["dispute_id"] == "PP-D-1"


def test_get_dispute_request():
    op = FakeOpener([pp("UNAUTHORISED")])
    assert client(op).get_dispute("PP-D-1")["dispute_id"] == "PP-D-1"
    assert op.requests[1].full_url == "https://api-m.sandbox.paypal.com/v1/customer/disputes/PP-D-1"


def test_live_env_uses_live_host():
    assert PayPalClient("a", "b", "live").base == "https://api-m.paypal.com"
    with pytest.raises(ValueError):
        PayPalClient("a", "b", "prod")


def test_provide_evidence_multipart_request():
    op = FakeOpener([{"links": []}])
    ev = [{"evidence_type": "PROOF_OF_FULFILLMENT",
           "evidence_info": {"tracking_info": [{"carrier_name": "FEDEX", "tracking_number": "123"}]}}]
    client(op).provide_evidence("PP-D-1", approve("PP-D-1", "provide_evidence", "m@example.com"),
                                evidences=ev, files=[("pod.pdf", b"%PDF-1", "application/pdf")])
    req = op.requests[1]
    assert req.full_url.endswith("/v1/customer/disputes/PP-D-1/provide-evidence") and req.get_method() == "POST"
    ctype = req.get_header("Content-type")
    assert ctype.startswith("multipart/form-data; boundary=")
    body = req.data.decode()
    assert 'name="input"' in body and json.dumps({"evidences": ev}) in body
    assert 'name="evidence-file"; filename="pod.pdf"' in body and "%PDF-1" in body


def test_provide_evidence_defaults_to_notes():
    op = FakeOpener([{}])
    client(op).provide_evidence("PP-D-1", approve("PP-D-1", "provide_evidence", "m"), notes="Delivered 10/22")
    assert json.dumps({"evidences": [{"evidence_type": "OTHER", "notes": "Delivered 10/22"}]}) in op.requests[1].data.decode()


def test_accept_claim_request():
    op = FakeOpener([{}])
    client(op).accept_claim("PP-D-1", approve("PP-D-1", "accept_claim", "m"), note="Refunding", accept_claim_type="REFUND")
    req = op.requests[1]
    assert req.full_url.endswith("/v1/customer/disputes/PP-D-1/accept-claim")
    assert req.get_header("Content-type") == "application/json"
    assert json.loads(req.data) == {"note": "Refunding", "accept_claim_type": "REFUND"}


def test_http_error_raises_paypal_error():
    err = urllib.error.HTTPError("u", 422, "Unprocessable", {}, io.BytesIO(b'{"name":"UNPROCESSABLE_ENTITY"}'))
    with pytest.raises(PayPalError) as e:
        client(FakeOpener([err])).get_dispute("PP-D-1")
    assert e.value.status == 422


# approval gate

@pytest.mark.parametrize("bad", [
    None,
    {"dispute_id": "PP-D-1", "action": "provide_evidence", "approver": "m"},  # not an Approval record
    Approval("PP-D-2", "provide_evidence", "m", "t"),                          # other dispute
    Approval("PP-D-1", "accept_claim", "m", "t"),                              # other action
    Approval("PP-D-1", "provide_evidence", "", "t"),                           # no approver
])
def test_provide_evidence_blocked_without_matching_approval(bad):
    op = FakeOpener()
    with pytest.raises(NotApproved):
        client(op).provide_evidence("PP-D-1", bad, notes="x")
    assert op.requests == []  # nothing sent, not even the token call


@pytest.mark.parametrize("bad", [None, Approval("PP-D-1", "provide_evidence", "m", "t")])
def test_accept_claim_blocked_without_matching_approval(bad):
    op = FakeOpener()
    with pytest.raises(NotApproved):
        client(op).accept_claim("PP-D-1", bad, note="x")
    assert op.requests == []


def test_approve_requires_approver_and_known_action():
    with pytest.raises(ValueError):
        approve("PP-D-1", "provide_evidence", "")
    with pytest.raises(ValueError):
        approve("PP-D-1", "refund_everything", "m")


def test_seed_from_api_fetches_details_and_skips_unsupported():
    op = FakeOpener([
        {"items": [{"dispute_id": "PP-D-1"}, {"dispute_id": "PP-D-2"}]},
        pp("MERCHANDISE_OR_SERVICE_NOT_RECEIVED"),
        pp("OTHER", dispute_id="PP-D-2"),
    ])
    ds = seed.from_paypal_api(client(op))
    assert [d.id for d in ds] == ["PP-D-1"]
    assert [r.get_method() for r in op.requests[1:]] == ["GET", "GET", "GET"]
