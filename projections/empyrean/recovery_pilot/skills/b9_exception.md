# B9 — EXCEPTION AGENT

**name:** exception
**trigger:** continuous — watches all nine `EXCEPTION_SOP` conditions raised by any agent, plus SLA clocks on open A6 rows
**inputs:** exception type · client ref · detecting agent · detection payload · `EXCEPTION_SOP` (owner + sla_hours) · open A6 rows
**tools:** `runtime/notion_client.py` (`write_row`, `request_approval`) · `runtime/notion_schema.py` (`EXCEPTION_SOP`, `EXCEPTION_FIELDS`)
**outputs:**
- A6 EXCEPTIONS row: `Exception`, `Client`, `Type`, `Detected At`, `Owner`, `SLA Due` (= `Detected At` + `sla_hours`), `Action Taken`, `Resolved At`, `Seen Twice`
- A5 APPROVALS row for client communication whenever the exception is client-visible
- A8 DEFECTS row when a type is seen twice — carrying the proposed template or automation

**the nine watched types** (owner / SLA read from `EXCEPTION_SOP`, never hardcoded): angry reply / stop request (Delivery, 1h) · technical question (Delivery, 2h) · approval overdue 48h (Account, 48h) · send failure / deliverability (Delivery, 0h) · trailing par day 14 (Account, 24h) · attribution dispute (Account, 24h) · health below 3.0 (Owner, 48h) · out of scope request (Account, 24h) · guarantee at risk <7 days (Owner, 0h).

**guardrails:**
- **"We tell them before they notice."** A client-visible exception files its client-communication APPROVALS row at detection time — not after triage, not after resolution. The approval may sit; the drafting never waits.
- Owner and SLA come from `EXCEPTION_SOP` lookup. An unknown type is itself an exception — route to Owner rather than inventing an SLA.
- `sla_hours = 0` means immediate, not "no deadline". Zero-hour types page the owner at detection.
- Never resolve an exception the agent itself opened without a recorded `Action Taken`; a row closed with an empty action is a defect.

**the standing rule:** anything seen twice becomes a template or an automation. Second occurrence of a type (per client for delivery types, globally for systemic types) sets `Seen Twice = true` and opens an A8 DEFECTS row naming the specific artifact to build. A third occurrence with no A8 row is a process failure to escalate to Owner.

**escalation:**
- SLA breach (now > `SLA Due`, unresolved) → escalate one level: Delivery → Account → Owner, journaled at each hop, with the elapsed time in the message
- Any zero-hour type unacknowledged after 15 minutes → straight to Owner

**verification:** every A6 row's `Type` ∈ `EXCEPTION_SOP` keys with `Owner` and `SLA Due` matching the table's `owner` / `sla_hours` (asserted by recomputation, not by eyeball); a fixture raising the same type twice produces `Seen Twice = true` and exactly one A8 row; every client-visible fixture exception produces an A5 row at detection.

**Gotchas:**
- "angry reply / stop request" has a 1h SLA but suppression is immediate at B6 — the SLA governs the human response, never the suppression
- "guarantee at risk <7 days" and "trailing par day 14" both come from B7; they are distinct rows with distinct owners, not one escalating row
- Seen-twice counting is per client for delivery-type exceptions and global for systemic ones — a send-failure at two clients is one systemic pattern, not two isolated incidents
- Client-facing text in the APPROVALS payload obeys the banned-word rules; internal `Action Taken` notes may name the mechanics plainly
