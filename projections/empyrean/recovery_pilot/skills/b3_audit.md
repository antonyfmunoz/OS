# B3 — AUDIT AGENT

**name:** audit
**trigger:** PROSPECTS row reaches Stage = "Access Granted" (CRM export received)
**inputs:** CRM CSV export path · company name · prospect record ref · optional config (avg job value, close rate from Call 1 notes)
**tools:** `generators/audit_generator.py` (classification + C1 math + C0 render) · `runtime/notion_client.py`
**outputs:**
- A1 PROSPECTS row updated: `Eligibility Verdict`, `Pipeline Estimate`, `Stage → "Audit Delivered"`
- Rendered Job Pipeline Audit HTML via C0 signed link (7-day expiry)
- A5 APPROVALS row for the audit-delivery email (nothing sends without it)

**guardrails:**
- Every dollar figure labeled an estimate; assumptions printed on-page (C1 `assumptions_text` — never hand-write assumptions)
- NEVER implies a revenue guarantee; the guarantee is activated qualified opportunities only
- Eligibility verdict computed from the same CSV — PASS / PRO-RATE / NOT ELIGIBLE always shown before the numbers
- Target ≤ 2 hours from access to delivered (A9 par "Audit turnaround"); log actual duration
- CSV stays local; only aggregates leave the machine; source file deleted per Data Promise (7 days on a no-go)

**escalation:**
- CSV unparseable / columns undetected → A6 EXCEPTION type "technical question", Owner=Delivery — never guess a schema silently
- Verdict = NOT ELIGIBLE → route to Owner before any delivery: pitch changes to the no-guarantee variant or the DWY path

**verification:** rendered HTML contains the verdict table, three pool sections, an "Estimates. Assumptions:" footnote, and zero banned words. `python3 -m projections.empyrean.recovery_pilot.rehearsal.harness --stage audit` exercises this end-to-end.

**Gotchas:**
- Estimates older than 12 months are excluded from the pool by the conditions precedent — do not count them just because the CSV has them
- Resolved estimates (status won/lost) are not "open" — the `_OPEN_STATUS` regex governs
- A thin CSV is a QUALIFICATION FAILURE, not a rendering problem — surface the verdict, don't pad the numbers
