# Judging + submission checklist (deadline Nov 12 2026, 12:00 PM PST = Nov 13, 1:30 AM IST; aim for Nov 11)

## Hard requirements (from the Devpost page, fetched Oct 28)
- [ ] Uses PayPal meaningfully (sandbox OK): Disputes API list/get/provide-evidence, plus webhook
- [ ] Uses AI meaningfully: LLM drafts the evidence response and the gap list; EV triage
- [ ] Working prototype + run instructions (README "Run"; offline `--source mock` mode for judges)
- [ ] Public GitHub repo with a visible LICENSE (MIT)
- [ ] Public YouTube video under 3:00, no unlicensed music or trademarks beyond fair reference
- [ ] Text description + tools list in the Devpost form
- [ ] Existing-project rule: README states what was built during the hackathon (PayPal client, mapping, submit path, new video)

## Prize categories we target, and the evidence to show
| Category | What the judge must see |
|---|---|
| Best Use of PayPal + AI | Real sandbox dispute IDs on screen; the evidence actually arrives on the dispute in PayPal |
| Best Use of Agentic Commerce | The agent plans across several API calls and stops at the approval gate; action log |
| Most Impactful | One number: $ recovered (EV) on the demo queue, and "deadline missed = automatic loss" |
| Best Demo Delivery | Tight 2:50 video, one flow, no dead air (DEMO_SCRIPT.md) |

## Quality gates before submit
- [ ] `pytest -q` passes on a fresh clone
- [ ] No secrets in repo history (`git log -p | grep -i secret`)
- [ ] Video re-rendered with **PayPal sandbox** footage; the current youtu.be/ULEQ5x7_Qxk is the Airwallex/mock version and is Unlisted. Use it only as a storyboard, or relabel it and keep it out of the PayPal submission.
- [ ] Devpost text passes the anti-slop gate
- [ ] Not cross-submitted in a way that breaks the Airwallex hackathon rules (check with Money Magnet notes; Airwallex lane is theirs)
