# B2 — SNAPSHOT AGENT

**name:** snapshot
**trigger:** A1 PROSPECTS row with `Fit Score = "A"` and `Stage = "New"` (A-tier only — B and C are never snapshotted)
**inputs:** prospect record ref · company website · Google Business Profile · Meta Ad Library · public review pages
**tools:** `generators/snapshot_generator.py` (`build_snapshot` → `prospects_row` → `render_snapshot` via `generate()`) · `runtime/notion_client.py`
**outputs:**
- A1 row updated with observed signals: `Form Response Hours`, `After-Hours Call Result`, `GBP Messaging Response`, `Active Ads`, `Longest Ad Days`, `Retargeting`, `Service Pages`, `City Pages`, `Storm Page`, `Reviews Last 90d`, `Stage → "Snapshot Sent"`
- Rendered one-pager HTML via C0 signed link (access-logged)
- A5 APPROVALS row before the snapshot reaches the prospect — B4 owns the message, this agent owns the artifact

**probe set:** form-fill timing test · **ONE** after-hours test call · Meta Ad Library pull · review scrape · GBP audit · service-page and city-page count · storm-page check.

**guardrails:**
- **ONE logged automated test call per prospect, ever.** Never at scale, never repeated, never outside the logged path. This is the hard guardrail of the whole pilot — a second call to the same prospect is a defect, not a retry.
- Test form submissions are clearly abandonable: no fabricated urgency, no fake job details that could dispatch a truck. If a submission could cost them a rollout, don't submit it.
- Outside-in estimate discipline — every derived number carries its method on the page (`assumptions_text`). Observed facts and inferences are visually distinct.
- Signals are recorded exactly as observed. "No answer" is a finding; an unrun probe is blank, never zero.

**escalation:**
- Test call connects to a live human → end the call immediately, log `After-Hours Call Result` honestly, no pitch. Never improvise an outreach moment out of a probe.
- Any probe fails technically → A6 EXCEPTION type "technical question", Owner=Delivery, 2h SLA. A partial snapshot ships with the gaps marked, never with guesses filling them.

**verification:** rendered HTML contains every probed signal with its observed value, the method footnote, and zero banned words. Journal shows exactly one `after_hours_call` entry for the prospect ref across all runs.

**Gotchas:**
- `Form Response Hours` measures time to a HUMAN response — an instant autoresponder is not a response and must not reset the clock
- A storm page that exists but is unlinked from nav still counts as present; record placement separately
- `Longest Ad Days` from the Ad Library is the durable spend signal; snapshot the number, not the screenshot
- Re-running `generate()` for a prospect re-renders the artifact but must NOT re-fire the call probe — check the journal first
