# B7 — SCOREBOARD AGENT

**name:** scoreboard
**trigger:** weekly, per active client (Day 7 first scoreboard, then every 7 days through the guarantee window; biweekly ceiling after Day 30)
**inputs:** A3 LEDGER rows for the client · client record (guarantee window start, pro-rated targets if PRO-RATE) · A9 pars
**tools:** `generators/scoreboard_generator.py` (C1 `guarantee_progress` + C0 render) · `runtime/notion_client.py`
**outputs:**
- Rendered Weekly Scoreboard HTML via C0 signed link (access-logged — feeds the A9 "Scoreboard opens" metric)
- Personalized report-video script draft (`video_script()`)
- A9 METRICS "Activated opportunities / 30 days" Current Value updated
- A5 APPROVALS row for scoreboard delivery (outbound gate applies)

**guardrails:**
- Every number traces to a LEDGER row with an evidence link — no unledgered claims, ever
- Client close rate on OUR opportunities is always shown (their conversion is part of the story)
- Uses the client's pro-rated guarantee numbers when Guarantee Status = PRO-RATE — never the default 20–25
- Delivery day never slips silently: a late scoreboard is an A6 EXCEPTION, not a quiet skip

**escalation:**
- Day ≥ 14 and activated < (guarantee_low × day/30) → A6 EXCEPTION type "trailing par day 14", Owner=Account, same-day SLA: add a pool or an angle, tell the client what changed and why
- Day ≥ 23 and pace short → A6 EXCEPTION type "guarantee at risk <7 days", Owner=Owner, immediate: proactive call BEFORE day 30 with the gap-closing plan

**verification:** scoreboard totals hand-checked against a fixture ledger (harness asserts activated/appointments/booked counts match independent recomputation). Banned-word grep clean.

**Gotchas:**
- "Activated qualified opportunity" = Response=true AND Qualified=true — appointments and bookings are downstream, never substitutes in the guarantee count
- `on_pace` is linear pro-rating; day 0-6 always reads on-pace — the day-14 exception trigger is the real control
- The video script is a DRAFT for AFM's recording — it is not sent anywhere by this agent
