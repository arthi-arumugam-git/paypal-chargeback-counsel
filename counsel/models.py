from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class Reason(str, Enum):
    FRAUD = "fraud"
    NOT_RECEIVED = "product_not_received"
    NOT_AS_DESCRIBED = "not_as_described"
    DUPLICATE = "duplicate"
    SUBSCRIPTION_CANCELLED = "subscription_cancelled"


@dataclass
class Evidence:
    avs_match: bool = False
    cvv_match: bool = False
    three_ds: bool = False
    tracking_delivered: bool = False
    signature: bool = False
    customer_comms: list[str] = field(default_factory=list)
    refund_issued: bool = False
    second_charge_distinct: bool = False
    cancel_before_charge: bool = False
    terms_accepted: bool = False
    product_matches_listing: bool = False


@dataclass
class Dispute:
    id: str
    payment_intent_id: str
    amount: float
    currency: str
    reason: Reason
    evidence: Evidence
    due_date: str
