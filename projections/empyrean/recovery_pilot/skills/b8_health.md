# B8 — HEALTH AGENT

**name:** health
**trigger:** monthly, per active client (and on demand before any renewal or Day 30 review)
**inputs:** A2 client record · A3 LEDGER rows for the month · C0 scoreboard access log (opens) · A5 APPROVALS decision timestamps · A6 EXCEPTION history · A9 pars
**tools:** `runtime/notion_client.py` · `runtime/notion_schema.py` (`HEALTH_WEIGHTS`, `HEALTH_ALERT_THRESHOLD`, `EXCEPTION_SOP`)
**outputs:**
- A2 CLIENTS row updated: `Health Score` (weighted 0–5), and `Stage → "At Risk"` when below threshold
- Component breakdown journaled — each of the six inputs with its raw measure, its normalized 0–5, and its weighted contribution
- A6 EXCEPTION row when the score falls below 3.0

**scoring:** weighted from `HEALTH_WEIGHTS` — opportunities vs par 25% · booked jobs 25% · scoreboard opens 15% · approval latency 15% · responsiveness 10% · sentiment 10%. Weights are read from the schema module, never re-typed here; they must sum to 1.0.

**guardrails:**
- Every component traces to a recorded measurement — ledger rows, access-log entries, approval timestamps, exception records. No component is estimated, and no component defaults to a passing value when its data is missing; a missing input is surfaced, not imputed.
- The score is deterministic arithmetic. Sentiment is the only judged component and it is scored from logged client communications, bounded 0–5, never from a general impression.
- Opportunities-vs-par uses the client's PRO-RATE targets when `Guarantee Status = "PRO-RATE"` — never the default 20–25.
- A falling score is reported to the client in the normal scoreboard rhythm; it is never a surprise revealed at renewal.

**escalation:**
- `Health Score` < 3.0 → A6 EXCEPTION type `"health below 3.0"`, Owner=**Owner**, SLA 48h, flagged **PHONE CALL — never email**. The record carries the two lowest-weighted-contribution components so the call has a subject before it starts.
- Score below 3.0 for a second consecutive month → set `Seen Twice = true` on the exception and escalate to Owner as a relationship decision, not a delivery fix

**verification:** sum of `HEALTH_WEIGHTS.values()` asserted == 1.0 before scoring; recomputing from the journaled component breakdown reproduces the stored `Health Score` exactly; a fixture client seeded below 3.0 produces exactly one A6 row with Owner="Owner" and `SLA Due` = detected + 48h.

**Gotchas:**
- Approval latency is OUR exposure to THEIR speed — a slow-approving client scores low on a component they control; the call names that plainly rather than treating it as our defect
- Scoreboard opens come from the C0 access log, not from email opens; an unopened scoreboard with strong booked jobs is a communication problem, not a delivery one
- Booked jobs lag opportunities by weeks — a month-1 score is directionally weak by construction; compare to par, not to a mature client
- The 48h SLA is time-to-CALL, not time-to-resolve
