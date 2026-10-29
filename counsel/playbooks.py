"""Reason-code playbooks: which evidence wins each dispute type, with weights."""
from .models import Reason, Evidence, Dispute

PLAYBOOKS: dict[Reason, list[tuple[str, float, str]]] = {
    Reason.FRAUD: [
        ("three_ds", 0.45, "The payment was authenticated with 3-D Secure, shifting liability to the issuer."),
        ("avs_match", 0.2, "The billing address matched the cardholder's address (AVS match)."),
        ("cvv_match", 0.15, "The correct card security code was supplied (CVV match)."),
        ("tracking_delivered", 0.2, "The order was delivered to the cardholder's verified address."),
    ],
    Reason.NOT_RECEIVED: [
        ("tracking_delivered", 0.6, "Carrier tracking confirms delivery."),
        ("signature", 0.25, "Delivery was signed for."),
        ("customer_comms", 0.15, "Customer correspondence after delivery acknowledges the order."),
    ],
    Reason.NOT_AS_DESCRIBED: [
        ("product_matches_listing", 0.5, "The item shipped matches the product listing."),
        ("customer_comms", 0.3, "The merchant offered a return or remedy in writing."),
        ("terms_accepted", 0.2, "The customer accepted the return policy at checkout."),
    ],
    Reason.DUPLICATE: [
        ("second_charge_distinct", 0.7, "The two charges are for separate orders."),
        ("refund_issued", 0.3, "Any genuine duplicate was already refunded."),
    ],
    Reason.SUBSCRIPTION_CANCELLED: [
        ("cancel_before_charge", -1.0, "Cancellation preceded the charge (merchant should accept)."),
        ("terms_accepted", 0.5, "The customer accepted recurring-billing terms."),
        ("customer_comms", 0.5, "No cancellation request was received before the charge."),
    ],
}


def _has(ev: Evidence, key: str) -> bool:
    v = getattr(ev, key)
    return bool(v)


def win_likelihood(d: Dispute) -> float:
    score = 0.0
    for key, w, _ in PLAYBOOKS[d.reason]:
        if _has(d.evidence, key):
            if w < 0:
                return 0.0
            score += w
    return round(min(score, 1.0), 2)


def recommend(d: Dispute) -> str:
    p = win_likelihood(d)
    if p >= 0.5:
        return "contest"
    return "accept"


def draft_rebuttal(d: Dispute) -> str:
    points = [txt for key, w, txt in PLAYBOOKS[d.reason] if w > 0 and _has(d.evidence, key)]
    lines = [
        f"Dispute {d.id} ({d.reason.value}) on {d.payment_intent_id}, {d.amount:.2f} {d.currency}.",
        "The merchant contests this dispute for the following reasons:",
    ] + [f"{i}. {p}" for i, p in enumerate(points, 1)]
    lines.append("Supporting documents are attached. STATUS: DRAFT, awaiting merchant approval.")
    return "\n".join(lines)
