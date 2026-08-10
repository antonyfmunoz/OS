# RAILS REHEARSAL CHECKLIST

**Owner:** AFM · **Mode:** TEST ONLY · **Blocks:** first client signature.

A rail is a path money, signature, or a message travels. Every rail below must
be walked **by hand, once, with evidence**, before a real client touches any of
them. Code that compiles is not a proven rail. A screenshot of the thing having
actually happened is.

**The rule:** no rail is checked without its evidence file on disk. A checked
box with no file is an unchecked box.

---

## Evidence convention

All evidence lands in `fixtures/evidence/`.

**Filename:** `YYYY-MM-DD_<rail>_<step>.png`

Examples:
```
2026-08-10_stripe_products-visible.png
2026-08-10_docusign_envelope-signed.png
2026-08-10_ghl_sms-delivered.png
```

**Every screenshot must show, in frame:**
- the **TEST MODE** indicator for that platform (Stripe test toggle, DocuSign
  demo banner, GHL test sub-account name),
- the object with its real identifier (product ID, envelope ID, message ID),
- enough surrounding UI to prove which account it is.

A cropped screenshot showing only a green checkmark proves nothing.

---

## RAIL 1 — STRIPE (4 screenshots)

Can money arrive, be declined, and be given back.

**Setup:**
```bash
export STRIPE_TEST_KEY=sk_test_...       # test key only; live keys are refused
cd projections/empyrean/recovery_pilot/fixtures
python3 stripe_test.py
```

The fixture writes `evidence/stripe_test_log.json`. That log is machine
evidence; the screenshots below are human evidence. **Both are required** — a
log can be produced by a script that lied, and a screenshot cannot be diffed.

- [ ] **1.1 Products visible.** Stripe Dashboard → Products, test mode on.
      Both products visible: "The Job Pipeline System — Activation" ($5,000
      one-time) and "— Monthly" ($2,500/mo recurring).
      → `evidence/YYYY-MM-DD_stripe_products-visible.png`

- [ ] **1.2 Successful charge.** Payments → the succeeded $5,000 PaymentIntent,
      showing `succeeded` and the last four of the test card.
      → `evidence/YYYY-MM-DD_stripe_charge-succeeded.png`

- [ ] **1.3 Declined charge.** Payments → the declined attempt, showing the
      decline code. **A decline that does not appear in the dashboard is a
      failed test** — it means the request never reached Stripe.
      → `evidence/YYYY-MM-DD_stripe_charge-declined.png`

- [ ] **1.4 Refund.** The refunded payment showing `refunded` and the amount.
      → `evidence/YYYY-MM-DD_stripe_refund.png`

- [ ] **1.5** `evidence/stripe_test_log.json` exists, `"mode": "TEST"` (not
      `SIMULATION`), and all four objects have real Stripe IDs.

**Verify:** `python3 -c "import json;d=json.load(open('evidence/stripe_test_log.json'));print(d['mode'],d['summary'])"`

**Gotcha:** if the log says `SIMULATION`, no key was found and **nothing was
tested**. The banner says so. Do not check these boxes off a simulated run.

---

## RAIL 2 — DOCUSIGN (3 screenshots)

Can an agreement be sent, signed, and retrieved.

**Source:** `fixtures/docusign_template.md`

> **Counsel gate.** That document carries a DRAFT — COUNSEL REVIEW REQUIRED
> banner. This rehearsal proves the *mechanism* using the draft. **The rail is
> proven; the document is not cleared.** Do not send it to a real client until
> counsel has reviewed it, then re-upload the reviewed version.

- [ ] **2.1 Template uploaded.** DocuSign (demo/sandbox) → Templates → the
      agreement uploaded with all fields placed per the field map: 3
      recipients, both signature blocks, all **8 initial fields**, and the
      Appendix A radio groups.
      → `evidence/YYYY-MM-DD_docusign_template-uploaded.png`

- [ ] **2.2 Test envelope sent to self.** Send an envelope from the template
      with AFM as Client Signer, showing status `Sent`.
      → `evidence/YYYY-MM-DD_docusign_envelope-sent.png`

- [ ] **2.3 Signed.** Complete signing as the recipient — **including every one
      of the 8 initials** — and capture status `Completed`.
      → `evidence/YYYY-MM-DD_docusign_envelope-signed.png`

- [ ] **2.4** Signed PDF and Certificate of Completion downloaded to
      `evidence/`.

**Gotcha:** if signing completes without prompting for all 8 initials, they
were placed as optional. Fix and re-send. Optional initials on the Guarantee
and liability sections defeat the reason they exist.

---

## RAIL 3 — GHL MESSAGING (2 screenshots)

Can a message actually reach a human.

> **No GHL credential exists on this VPS — verified.** This rail is **BLOCKED**
> until the token lands at 1Password `UMH-Production` / item `GHL` / field
> `token`. Everything in `pod/` is written and ready; nothing is connected.
> Leave these boxes unchecked and say so out loud rather than checking them on
> a simulated basis.

- [ ] **3.1 Test email delivered.** From the test sub-account, send one
      approved template to AFM's own address. Screenshot the **received email
      in the inbox** (not the "sent" confirmation), showing sender, subject,
      and body.
      → `evidence/YYYY-MM-DD_ghl_email-delivered.png`

- [ ] **3.2 Test SMS delivered.** Send one approved SMS template to AFM's own
      phone. Screenshot the **received message on the phone**, showing sender
      number, full body, and the `Reply STOP to opt out.` line.
      → `evidence/YYYY-MM-DD_ghl_sms-delivered.png`

- [ ] **3.3 STOP works.** Reply `STOP` and confirm suppression in the
      sub-account. **This is the one that protects the client's number.**
      → `evidence/YYYY-MM-DD_ghl_stop-suppression.png`

**Gotchas:**
- Screenshot the **receiving device**, not the sending UI. A "sent" status is
  not delivery; carrier filtering happens after send.
- Confirm the sender is the **client's business number**, not an agency
  number. Wrong sender is a misconfigured Pod.
- If the SMS arrives without the opt-out line, the template was edited after
  approval. Stop and fix before anything else.

---

## RAIL 4 — HARNESS RUN, SCREEN-RECORDED (D3)

The full rehearsal, recorded once, doing triple duty: rail evidence, the
plastic-client demo, and lesson one of the curriculum.

**Record:** full screen, audio narration on, unbroken take.
→ `evidence/YYYY-MM-DD_harness-run.mp4`

- [ ] **4.1** Recording started **before** the first command. Starting after
      setup removes exactly the part a viewer needs.
- [ ] **4.2** Harness run start to finish in one take, no cuts.
- [ ] **4.3** Narrate each stage as it runs: what is happening, what artifact
      it produces, why that artifact exists.
- [ ] **4.4** Show the rendered artifacts on screen — snapshot, audit,
      scoreboard.
- [ ] **4.5** Show the eligibility verdict computed from data, and say plainly
      that the guarantee is opportunities, never revenue.
- [ ] **4.6** Show the ledger and name it as what the guarantee is adjudicated
      against.
- [ ] **4.7** State on camera that this is TEST MODE and no homeowner was
      contacted.
- [ ] **4.8** Under 15 minutes. Longer stops being a demo.

**Why one recording serves three purposes:** the demo needs to show the system
working on a plastic client; the curriculum needs a narrated walkthrough of the
same run; the evidence bundle needs proof the harness ran end to end. One
honest take satisfies all three. A polished re-shoot after a failed take
satisfies none of them honestly — if a stage breaks on camera, fix it and
re-record the whole run.

---

## SIGN-OFF

No client signature is requested until every line here is true.

- [ ] Rail 1 — Stripe: 4 screenshots + `stripe_test_log.json` with `"mode": "TEST"`
- [ ] Rail 2 — DocuSign: 3 screenshots + signed PDF + certificate
- [ ] Rail 3 — GHL: 3 screenshots **(BLOCKED — no credential on this VPS)**
- [ ] Rail 4 — Harness recording, single take, under 15 minutes
- [ ] Every evidence file present in `fixtures/evidence/` under the naming convention
- [ ] Counsel has reviewed `docusign_template.md` and the reviewed version is uploaded

**Verify the evidence directory:**
```bash
ls -la projections/empyrean/recovery_pilot/fixtures/evidence/
```

**Blocked rails stay visibly blocked.** Rail 3 cannot pass today, and the
correct state of this checklist is "3 of 4 rails proven, GHL blocked on
credential" — not a full set of checkmarks that implies a messaging path
nobody has ever sent a message through.

**Signed off by:** ________________  **Date:** ____________
