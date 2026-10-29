# PayPal sandbox setup (do this when Arthi has a PayPal Developer login)
Time needed: about 30 minutes.

## 1. App credentials 🔒 (Arthi)
1. Log in at https://developer.paypal.com → **Apps & Credentials** → toggle **Sandbox**.
2. **Create App** → name `chargeback-counsel` → type Merchant → copy **Client ID** and **Secret**.
3. Save them in the vault / `.env` (never commit):
```
PAYPAL_ENV=sandbox
PAYPAL_CLIENT_ID=...
PAYPAL_CLIENT_SECRET=...
PAYPAL_WEBHOOK_ID=...      # step 4
```
4. Default sandbox accounts are created under **Testing Tools → Sandbox Accounts**: one Business (merchant) and one Personal (buyer). Note both logins.

## 2. Smoke test
```bash
curl -s -u "$PAYPAL_CLIENT_ID:$PAYPAL_CLIENT_SECRET" \
  -d grant_type=client_credentials https://api-m.sandbox.paypal.com/v1/oauth2/token | jq .access_token
curl -s -H "Authorization: Bearer $TOKEN" https://api-m.sandbox.paypal.com/v1/customer/disputes | jq .
```
An empty `items` list is fine at this point.

## 3. Create real sandbox disputes (needed for the demo)
1. Create and capture 4–5 orders from the buyer account to the merchant (Orders v2 API with the buyer approving in the sandbox checkout, or a sandbox PayPal button).
2. Log in to https://www.sandbox.paypal.com as the **buyer** → Resolution Center → open a dispute on each order, using different reasons (item not received, not as described, unauthorized).
3. Check `GET /v1/customer/disputes` now lists them with `seller_response_due_date`.
4. Sandbox-only helpers to move disputes along for the video: `POST /v1/customer/disputes/{id}/require-evidence` and `POST /v1/customer/disputes/{id}/adjudicate`. Check the current Disputes API reference before using; field names may have changed.

## 4. Webhook
Developer Dashboard → your app → **Webhooks → Add** → URL = the Render/ngrok URL `/webhooks/paypal` → events `CUSTOMER.DISPUTE.CREATED`, `CUSTOMER.DISPUTE.UPDATED`, `CUSTOMER.DISPUTE.RESOLVED`. Copy the Webhook ID into `.env`. Verify signatures with `POST /v1/notifications/verify-webhook-signature`.

## 5. Port plan (code, via Claude Code CLI)
- `counsel/paypal_client.py`: OAuth token cache, list/get disputes, provide-evidence (multipart), accept-claim.
- Map PayPal dispute JSON → existing `counsel.models.Dispute`; map PayPal reason codes to the 5 playbooks.
- `counsel.seed --source paypal|mock`; keep mock as the default so tests run without keys.
- Tests: recorded sandbox responses as fixtures.
Run: `/home/box/.local/bin/claude -p --permission-mode acceptEdits "<task>"` in the new repo.

## Blockers
- 🔒 PayPal Developer account + sandbox app (Arthi). Nebius is **not** needed for this lane.
- 🔒 Devpost registration for the PayPal AI Hackathon (Arthi to confirm).
