# Chargeback Counsel for PayPal
An approval-gated AI agent that works a PayPal merchant's dispute queue. It pulls open disputes from the PayPal Disputes API, ranks them by expected recovery, drafts an evidence-backed response for each reason code, and waits for the merchant to approve before it submits anything back to PayPal.

Built for the PayPal AI Hackathon (Devpost, deadline Nov 12 2026 12:00 PM PST). Grows out of the Chargeback Counsel prototype (offline demo: https://youtu.be/ULEQ5x7_Qxk). Work done in the hackathon window: the PayPal client, the PayPal reason-code mapping, the sandbox submit path and the new demo.

## Why
A small merchant who misses an evidence deadline loses the dispute automatically: the money plus the fee. Most disputes that could be won are lost to paperwork, not to the facts.

## What it does
1. **Ingest:** `CUSTOMER.DISPUTE.CREATED` webhook (signature verified), plus a polling fallback on `GET /v1/customer/disputes`.
2. **Triage:** for each dispute, estimates P(win) from reason-code playbooks and evidence on hand, then computes expected value = P(win) × amount − handling cost. Recommends contest or accept.
3. **Deadlines first:** sorts by `seller_response_due_date`. Anything due within 48 h goes to the top.
4. **Evidence pack:** pulls the order, the shipping/tracking record and the buyer messages, lists what's missing, and drafts the response text with an LLM.
5. **Human approval gate:** nothing goes to PayPal until the merchant clicks Approve. Every action is logged.
6. **Submit:** `POST /v1/customer/disputes/{id}/provide-evidence` (or `accept-claim` when the EV says accept).

| PayPal reason | Playbook |
|---|---|
| MERCHANDISE_OR_SERVICE_NOT_RECEIVED | tracking + delivery confirmation |
| MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED | listing snapshot, photos, buyer messages, return policy |
| UNAUTHORISED | AVS/IP/device match, prior orders from the same buyer |
| DUPLICATE_TRANSACTION / INCORRECT_AMOUNT | ledger lines showing distinct charges / correct amount |
| CREDIT_NOT_PROCESSED | refund record or policy showing no refund due |

## Run
```bash
python3 -m pip install -e .
cp .env.example .env            # PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET, PAYPAL_ENV=sandbox, LLM key
python3 -m counsel.seed --source paypal   # pull sandbox disputes (or --source mock for offline)
python3 -m counsel.queue                  # ranked triage queue
python3 -m counsel.dashboard              # approval dashboard -> data/dashboard.html
python3 -m pytest -q
```
Offline mode (`--source mock`) runs with no keys, so judges can try it without a PayPal account.

## Safety
- Sandbox only in this submission. No real buyer data.
- The agent never submits without a recorded human approval.
- Evidence text is drafted from records; the LLM is told not to invent facts, and every claim in a draft links to the record it came from.

## Tools
Python, PayPal REST APIs (OAuth2, Disputes, Orders), an LLM for drafting, static HTML dashboard.

## License
MIT (see LICENSE).

> Status Oct 30 2026: the core (playbooks, triage queue, deadlines, packets, approval gate), the PayPal Disputes client and the reason mapping are in `counsel/`. `--source mock` works offline. `--source paypal` is implemented but has not been run against the sandbox yet (no credentials; see SANDBOX_SETUP.md). The webhook, LLM drafting and `counsel.dashboard` are not ported yet.
