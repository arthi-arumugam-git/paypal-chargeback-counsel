"""Human-approval gate: nothing is submitted to PayPal without an explicit approve()."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone

ACTIONS = ("provide_evidence", "accept_claim")


class NotApproved(Exception):
    pass


@dataclass(frozen=True)
class Approval:
    """A merchant's recorded sign-off for one write action on one dispute."""
    dispute_id: str
    action: str
    approver: str
    approved_at: str


def approve(dispute_id: str, action: str, approver: str) -> Approval:
    if not approver:
        raise ValueError("approver required")
    if action not in ACTIONS:
        raise ValueError(f"unknown action {action!r}")
    return Approval(dispute_id, action, approver, datetime.now(timezone.utc).isoformat(timespec="seconds"))


def require(approval, dispute_id: str, action: str) -> None:
    """Raise NotApproved unless `approval` is an Approval for exactly this dispute and action."""
    if not isinstance(approval, Approval):
        raise NotApproved(f"{action} on {dispute_id}: no approval record")
    if approval.dispute_id != dispute_id or approval.action != action or not approval.approver:
        raise NotApproved(f"{action} on {dispute_id}: approval is for {approval.action} on {approval.dispute_id}")


@dataclass
class Submission:
    dispute_id: str
    text: str
    approval: Approval | None = None
    submitted: bool = False

    @property
    def approved(self) -> bool:
        return self.approval is not None

    def approve(self, approver: str) -> Approval:
        self.approval = approve(self.dispute_id, "provide_evidence", approver)
        return self.approval

    def submit(self, client) -> dict:
        if self.approval is None:
            raise NotApproved(self.dispute_id)
        resp = client.provide_evidence(self.dispute_id, self.approval, notes=self.text)
        self.submitted = True
        return resp
