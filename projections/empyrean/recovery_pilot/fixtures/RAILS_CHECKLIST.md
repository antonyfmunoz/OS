# RAILS REHEARSAL CHECKLIST — manual pass (AFM)

The harness proved the CODE path. This checklist proves the RAILS — real
Stripe screens, a real DocuSign envelope, real GHL deliveries. Run it by
hand, drop each screenshot into `fixtures/evidence/` with the exact
filename, then record the on-camera full rehearsal (D3).

## 1. Stripe (test mode) — 4 screenshots
Run first: `STRIPE_TEST_KEY=sk_test_... python3 fixtures/stripe_test.py`
- [ ] `stripe_01_products.png` — dashboard Products page showing "The Job Pipeline System — Activation" ($5,000) and "— Monthly" ($2,500/mo), TEST badge visible
- [ ] `stripe_02_charge_succeeded.png` — the successful $5,000 PaymentIntent
- [ ] `stripe_03_charge_declined.png` — the declined PaymentIntent (card_declined)
- [ ] `stripe_04_refund.png` — the refund on the successful charge

## 2. DocuSign — 3 screenshots
Template source: `fixtures/docusign_template.md` (counsel review banner stands — test envelope to YOURSELF only)
- [ ] `docusign_01_template.png` — template saved with party "Empyrean Creative LLC dba Empyrean Studios" and all field tabs placed
- [ ] `docusign_02_envelope_sent.png` — test envelope sent to your own email
- [ ] `docusign_03_signed.png` — completed/signed test envelope

## 3. GHL — 2 screenshots
- [ ] `ghl_01_test_email.png` — one test email delivered to your own inbox from the pod
- [ ] `ghl_02_test_sms.png` — one test SMS delivered to your own phone (from a test/tracking number, opt-out line present)
- Note: when the GHL Private Integration token lands in 1Password (UMH-Production / item `GHL` / field `token`), the C4 docs upgrade to a live current-state diff.

## 4. D3 — the recording
- [ ] Screen-record one clean end-to-end harness run + the rendered surfaces:
  `UMH_ROOT=/opt/OS python3 -m projections.empyrean.recovery_pilot.rehearsal.harness`
  then open in order: rehearsal-snapshot.html → rehearsal-audit.html → rehearsal-scoreboard.html (in `data/output/`)
- [ ] Save as `rehearsal_recording_YYYY-MM-DD.mp4` (or link) — this recording IS the plastic-client demo video and curriculum lesson one
- [ ] Log any moment you needed knowledge that isn't written down → A8 DEFECTS (that's the real rescue count)

## Done =
All 9 screenshots + the recording exist in `fixtures/evidence/` → update A7 ARTIFACTS rows (2.7, 2.8, GHL comms) to BUILT with evidence links → go/no-go call.
