# Mobile Browser Voice Evidence — pre-P4S-31D-5 observation (Lane C)

Date: 2026-07-07. Recorded during the P4S-31D-1 wave, classified as EVIDENCE
FOR THE LATER MOBILE-BROWSER LANE (P4S-31D-5) — explicitly NOT a P4S-31D-1
failure. P4S-31D-1's Class-A target is desktop browser Chrome on the
executor node.

## Observation

Owner opened the deployed cockpit on a MOBILE BROWSER, tapped the mic, and
received: "Voice consent required — enable push-to-talk for this device."

## Classification

| Dimension | Finding |
|---|---|
| Surface | Mobile browser (P4S-31D-5 lane; matrix verdict: PTT CONSTRAINED — tap-to-talk only, iOS Safari drops mic on background/lock; wake/ambient NOT_FEASIBLE) |
| Consent gate | WORKED AS DESIGNED — fail-closed refusal with typed CONSENT_REQUIRED; no capture without an active VoiceConsentGrant(push_to_talk). This is the P4S-31D-1 security contract behaving correctly on an unproven surface. |
| Consent UX gap | REAL — the refusal was a dead-end message with no inline grant path. Fixed in Lane A (inline "Enable Push-to-Talk for this device" control in the voice status strip, calling the governed grant route; no blocking dialog; no auto-grant). The Lane A control renders on any surface the cockpit serves, so the mobile dead-end disappears too — but granting consent on mobile does NOT make mobile PTT a proven surface. |
| Microphone permission behavior | Not reached (UMH consent layer refused before the browser permission prompt — correct two-layer ordering). Mobile browser mic permission behavior (per-origin, HTTPS-only, iOS Safari re-prompt semantics) remains to be characterized in P4S-31D-5. |
| Viewport/UI behavior | The voice status strip and mic affordance render on mobile viewport; consent refusal text was readable. Full small-viewport audit (draft bubble, held-message reveal, intent-loop panel reachability for the in-thread gate flow) deferred to P4S-31D-5. |
| Later adapter requirements (P4S-31D-5) | tap-to-talk only (no hold gesture reliance); explicit handling of mic-drop on background/lock → typed refusal + turn cancel; WS keepalive strategy for mobile radio; on-device STT unavailable in browser → server STT via authenticated WS only; same PlatformVoiceAdapter interface; same consent per-mode gate; identity = mobile Clerk session; NO background capture, NO wake word (NOT_FEASIBLE per matrix). |

## Disposition

- P4S-31D-1 desktop proof proceeds unaffected (Lane B).
- This record seeds the P4S-31D-5 packet's ground truth.
- The screenshot itself lives with the owner's session records; this document
  is the canonical classification.
