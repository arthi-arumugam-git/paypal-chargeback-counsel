"""PayPal Disputes API v1 client (stdlib only) and the PayPal dispute -> Dispute mapper.

Field names follow PayPal's published Disputes v1 OpenAPI spec
(https://developer.paypal.com/api/customer-disputes/v1/schema.json).
Write methods (provide_evidence, accept_claim) refuse to run without an
approval.Approval for that exact dispute and action.
"""
from __future__ import annotations
import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

from .approval import Approval, require
from .models import Dispute, Evidence, Reason

BASE_URLS = {
    "sandbox": "https://api-m.sandbox.paypal.com",
    "live": "https://api-m.paypal.com",
}

REASON_MAP = {
    "MERCHANDISE_OR_SERVICE_NOT_RECEIVED": Reason.NOT_RECEIVED,
    "MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED": Reason.NOT_AS_DESCRIBED,
    "UNAUTHORISED": Reason.FRAUD,
    "DUPLICATE_TRANSACTION": Reason.DUPLICATE,
    "INCORRECT_AMOUNT": Reason.INCORRECT_AMOUNT,
    "CREDIT_NOT_PROCESSED": Reason.CREDIT_NOT_PROCESSED,
    "CANCELED_RECURRING_BILLING": Reason.SUBSCRIPTION_CANCELLED,
}
# Not mapped (no playbook yet): PAYMENT_BY_OTHER_MEANS, PROBLEM_WITH_REMITTANCE, OTHER.


class UnsupportedReason(ValueError):
    pass


class PayPalError(Exception):
    def __init__(self, status: int, body: str):
        super().__init__(f"PayPal HTTP {status}: {body[:300]}")
        self.status = status
        self.body = body


def from_paypal(dj: dict, evidence: Evidence | None = None) -> Dispute:
    """Map a PayPal dispute object (details or list-item summary) to a Dispute.

    PayPal does not hold the merchant's own records (tracking, AVS, policies), so
    `evidence` comes from the merchant side; it defaults to empty.
    """
    reason = dj.get("reason", "")
    if reason not in REASON_MAP:
        raise UnsupportedReason(f"{dj.get('dispute_id')}: no playbook for PayPal reason {reason!r}")
    amount = dj.get("dispute_amount") or {}
    txns = dj.get("disputed_transactions") or []  # absent in list-item summaries
    seller_txn = txns[0].get("seller_transaction_id", "") if txns else ""
    due = dj.get("seller_response_due_date") or ""
    return Dispute(
        id=dj["dispute_id"],
        payment_intent_id=seller_txn,
        amount=float(amount.get("value", 0)),
        currency=amount.get("currency_code", ""),
        reason=REASON_MAP[reason],
        evidence=evidence or Evidence(),
        due_date=due[:10],
        status=dj.get("status", ""),
    )


def _multipart(parts: list[tuple[str, str, bytes, str | None]]) -> tuple[bytes, str]:
    """parts: (name, content_type, data, filename). Returns (body, Content-Type header)."""
    boundary = uuid.uuid4().hex
    out = b""
    for name, ctype, data, filename in parts:
        disp = f'form-data; name="{name}"' + (f'; filename="{filename}"' if filename else "")
        out += (f"--{boundary}\r\nContent-Disposition: {disp}\r\nContent-Type: {ctype}\r\n\r\n").encode()
        out += data + b"\r\n"
    out += f"--{boundary}--\r\n".encode()
    return out, f"multipart/form-data; boundary={boundary}"


class PayPalClient:
    def __init__(self, client_id: str, client_secret: str, env: str = "sandbox", opener=None):
        if env not in BASE_URLS:
            raise ValueError(f"env must be one of {sorted(BASE_URLS)}")
        self.client_id = client_id
        self.client_secret = client_secret
        self.base = BASE_URLS[env]
        self._urlopen = opener or urllib.request.urlopen
        self._token: str | None = None
        self._token_exp = 0.0

    @classmethod
    def from_env(cls, **kw) -> "PayPalClient":
        cid, sec = os.environ.get("PAYPAL_CLIENT_ID"), os.environ.get("PAYPAL_CLIENT_SECRET")
        if not cid or not sec:
            raise RuntimeError("PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET must be set (see SANDBOX_SETUP.md)")
        return cls(cid, sec, os.environ.get("PAYPAL_ENV", "sandbox"), **kw)

    def _send(self, req: urllib.request.Request) -> dict:
        try:
            with self._urlopen(req, timeout=30) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as e:
            raise PayPalError(e.code, e.read().decode("utf-8", "replace")) from None
        return json.loads(raw) if raw else {}

    def token(self) -> str:
        if self._token and time.time() < self._token_exp - 60:
            return self._token
        basic = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        req = urllib.request.Request(
            self.base + "/v1/oauth2/token",
            data=b"grant_type=client_credentials",
            method="POST",
            headers={"Authorization": f"Basic {basic}", "Accept": "application/json",
                     "Content-Type": "application/x-www-form-urlencoded"},
        )
        body = self._send(req)
        self._token = body["access_token"]
        self._token_exp = time.time() + float(body.get("expires_in", 0))
        return self._token

    def _request(self, method: str, path: str, query: dict | None = None,
                 data: bytes | None = None, content_type: str | None = None) -> dict:
        url = self.base + path
        if query:
            url += "?" + urllib.parse.urlencode({k: v for k, v in query.items() if v is not None})
        headers = {"Authorization": f"Bearer {self.token()}", "Accept": "application/json"}
        if content_type:
            headers["Content-Type"] = content_type
        return self._send(urllib.request.Request(url, data=data, method=method, headers=headers))

    # reads

    def list_disputes(self, dispute_state: str | None = None, page_size: int | None = None,
                      next_page_token: str | None = None, **query) -> dict:
        """GET /v1/customer/disputes. Returns {"items": [dispute_info...], "links": [...]}."""
        q = {"dispute_state": dispute_state, "page_size": page_size, "next_page_token": next_page_token, **query}
        return self._request("GET", "/v1/customer/disputes", q)

    def get_dispute(self, dispute_id: str) -> dict:
        return self._request("GET", f"/v1/customer/disputes/{urllib.parse.quote(dispute_id)}")

    # writes (approval-gated)

    def provide_evidence(self, dispute_id: str, approval: Approval, notes: str = "",
                         evidences: list[dict] | None = None,
                         files: list[tuple[str, bytes, str]] | None = None) -> dict:
        """POST /v1/customer/disputes/{id}/provide-evidence (multipart/form-data).

        evidences: PayPal evidence objects, e.g.
          {"evidence_type": "PROOF_OF_FULFILLMENT",
           "evidence_info": {"tracking_info": [{"carrier_name": "FEDEX", "tracking_number": "..."}]},
           "notes": "..."}
        Defaults to a single OTHER evidence carrying `notes`.
        files: (filename, bytes, content_type) attachments.
        """
        require(approval, dispute_id, "provide_evidence")
        if evidences is None:
            evidences = [{"evidence_type": "OTHER", "notes": notes}]
        # TODO: verify the JSON part name. The v1 OpenAPI spec only lists the file
        # part ("evidence-file"); PayPal's curl examples send the JSON as part "input".
        parts = [("input", "application/json", json.dumps({"evidences": evidences}).encode(), None)]
        for fname, data, ctype in files or []:
            parts.append(("evidence-file", ctype, data, fname))
        body, ctype = _multipart(parts)
        return self._request("POST", f"/v1/customer/disputes/{urllib.parse.quote(dispute_id)}/provide-evidence",
                             data=body, content_type=ctype)

    def accept_claim(self, dispute_id: str, approval: Approval, note: str,
                     accept_claim_type: str | None = None, **extra) -> dict:
        """POST /v1/customer/disputes/{id}/accept-claim. PayPal refunds the buyer from the merchant balance.

        accept_claim_type must be one of the dispute's allowed_response_options.accept_claim.accept_claim_types
        (REFUND, REFUND_WITH_RETURN, PARTIAL_REFUND, REFUND_WITH_RETURN_SHIPMENT_LABEL).
        """
        require(approval, dispute_id, "accept_claim")
        # TODO: the v1 OpenAPI spec documents this body only as multipart with an
        # "accept-claim-document" file; "note"/"accept_claim_type" as a JSON body come
        # from PayPal's request examples. Confirm against sandbox before the demo.
        payload = {"note": note, **extra}
        if accept_claim_type:
            payload["accept_claim_type"] = accept_claim_type
        return self._request("POST", f"/v1/customer/disputes/{urllib.parse.quote(dispute_id)}/accept-claim",
                             data=json.dumps(payload).encode(), content_type="application/json")
