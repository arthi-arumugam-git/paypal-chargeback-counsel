"""Human-approval gate: nothing is submitted to PayPal without an explicit approve()."""
from dataclasses import dataclass


class NotApproved(Exception):
    pass


@dataclass
class Submission:
    dispute_id: str
    text: str
    approved: bool = False
    submitted: bool = False

    def approve(self, approver: str) -> None:
        if not approver:
            raise ValueError("approver required")
        self.approved = True

    def submit(self, client) -> dict:
        if not self.approved:
            raise NotApproved(self.dispute_id)
        resp = client.submit_evidence(self.dispute_id, self.text)
        self.submitted = True
        return resp
