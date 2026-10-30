# Demo video script (target 2:50, YouTube Public)
Storyboard source: the existing offline demo https://youtu.be/ULEQ5x7_Qxk (Airwallex/mock data, 92 s). Keep its structure; swap every data screen for the PayPal sandbox version.

| Time | Screen | Voiceover (approx.) | Reuse from ULEQ5x7_Qxk? |
|---|---|---|---|
| 0:00–0:20 | Title card + one stat | "Small merchants lose disputes they could win because the evidence is late or thin. A missed deadline is an automatic loss." | Reuse problem framing |
| 0:20–0:45 | PayPal sandbox Resolution Center (buyer opens "item not received") → webhook log line in terminal | "A buyer opens a dispute. PayPal sends us the webhook; we check the signature." | New footage |
| 0:45–1:15 | `counsel.queue` output: 5 real sandbox dispute IDs, P(win), EV, contest/accept | "The agent ranks every open dispute by expected recovery, and puts the ones due soonest first." | Same layout, new data |
| 1:15–1:50 | Evidence pack for one dispute: tracking, order, buyer message; gap list; LLM draft | "For 'item not received' it pulls tracking and delivery proof, flags what's missing, and drafts the response. Each sentence points to a record." | Same layout, new data |
| 1:50–2:15 | Dashboard: click **Approve** | "Nothing goes to PayPal without the merchant's approval." | Reuse dashboard |
| 2:15–2:35 | Terminal: `provide-evidence` 200 → refresh sandbox dispute shows evidence attached | "Approved, submitted through the Disputes API, and PayPal shows the evidence on the case." | New footage — the key shot |
| 2:35–2:50 | Recovery total + repo URL + MIT | "Expected recovery on this queue: $X. Code is open source." | New |

Recording notes: 1080p, no music (or a licensed track), captions on. Upload as **Public**. Put the link in Devpost and the README.

Offline cut (available now): `scripts/make_demo_video.py` renders `data/demo/paypal_counsel_demo.mp4` from the mock fixtures. It shows seed, queue, deadlines, packet, approval and dashboard with real CLI output, and says plainly that sandbox runs, submit, webhooks and LLM drafting are not done yet. Replace it with the sandbox footage above once credentials are available.
