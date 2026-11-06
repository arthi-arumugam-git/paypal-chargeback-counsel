# Devpost submission draft: PayPal AI Hackathon
Deadline Nov 12 2026, 12:00 PM PST (Nov 13, 1:30 AM IST). Target submit: Nov 11.
Status Nov 3 2026: offline (`--source mock`) flow works; sandbox path written but not yet run (no PayPal sandbox credentials). Do not claim sandbox results until SANDBOX_SETUP.md has been run.

## Name
Chargeback Counsel for PayPal

## Tagline (under 200 chars)
An approval-gated agent that works a PayPal merchant's dispute queue: ranks disputes by expected recovery, drafts evidence per reason code, and submits only after the merchant approves.

## Inspiration
A small merchant who misses a PayPal evidence deadline loses the dispute automatically, money plus fee. Most winnable disputes are lost to paperwork, not facts.

## What it does
- Pulls open disputes from the PayPal Disputes API (`GET /v1/customer/disputes`), or offline fixtures for judges with no account.
- Sorts by `seller_response_due_date`; anything due within 48 h goes to the top.
- Estimates P(win) from per-reason playbooks and the evidence on hand, computes expected value, and recommends contest or accept.
- Builds an evidence pack and lists what is missing.
- Writes a static approval dashboard. Nothing goes back to PayPal without a recorded human approval (`data/approvals.json`).

## How we built it
Python. PayPal REST: OAuth2 client-credentials, Disputes list/get, provide-evidence and accept-claim behind the approval gate. Reason-code mapping for MERCHANDISE_OR_SERVICE_NOT_RECEIVED, NOT_AS_DESCRIBED, UNAUTHORISED, DUPLICATE_TRANSACTION, INCORRECT_AMOUNT, CREDIT_NOT_PROCESSED. Reusable triage core ported from an earlier Chargeback Counsel prototype; the PayPal client, mapping, submit path, dashboard port and demo were built during the hackathon window (commits 455b6b1..84b30c4).

## Challenges
Keeping the agent from acting on its own: every write path checks for an approval record first, and tests cover that refusal.

## What's next
Run against sandbox disputes, port the webhook (`CUSTOMER.DISPUTE.CREATED`, signature verified) and LLM drafting with record-linked citations.

## Built with
python, paypal-rest-api, paypal-disputes-api, oauth2, html, ffmpeg

## Links (fill before submit)
- Repo (public, MIT LICENSE visible): https://github.com/arthi-arumugam-git/paypal-chargeback-counsel
- Video (YouTube, Public, under 3:00): https://youtu.be/7OIXezJqkSs (uploaded Nov 6 2026 ~5:04 AM IST from data/demo/paypal_counsel_demo.mp4, 2:31, synthetic fixtures labeled).
- Try it: `pip install -e . && python3 -m counsel.seed --source mock && python3 -m counsel.queue`

## Open blockers
1. PayPal sandbox client ID/secret (Arthi) for real sandbox dispute IDs on screen (Best Use of PayPal + AI).
2. Confirm Devpost registration for the PayPal AI Hackathon (deadline Nov 13 1:30 AM IST).

## Done (do not re-do)
- Public repo: https://github.com/arthi-arumugam-git/paypal-chargeback-counsel
- YouTube Public demo (2:31): https://youtu.be/7OIXezJqkSs (Nov 6 ~5:04 AM IST)
