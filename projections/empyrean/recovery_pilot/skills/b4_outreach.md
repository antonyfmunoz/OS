# B4 — OUTREACH AGENT

**name:** outreach
**trigger:** A1 PROSPECTS row reaches `Stage = "Snapshot Sent"` with a rendered one-pager and its signals populated
**inputs:** prospect record ref · snapshot signals from the A1 row · C0 signed link to the one-pager · demo video link · owner name
**tools:** `runtime/notion_client.py` (`request_approval`, `assert_approved`, `execute_outbound`) · `runtime/notion_schema.py`
**outputs:**
- A5 APPROVALS row, `Status = "pending"`, `Requesting Agent = "outreach"`, `Payload` = the full email object (to, subject, body, snapshot link, video link) — **this is the terminal state of this agent**
- A1 row updated: `Stage → "Outreach Drafted"`, `Next Action`, `Owner`
- On human approval: `execute_outbound()` sends and the row advances to `"Outreach Approved"`

**message structure:** their diagnosis first — what was observed about their own operation, in their own numbers. The demo video link second. The ask is a conversation, never a purchase.

**guardrails:**
- **EMAIL ONLY. Never SMS.** TCPA exposure on cold contact is absolute — no text, no ringless voicemail, no messaging app, regardless of what a phone number field contains.
- Nothing sends without an approved record. `assert_approved()` raises `ApprovalRequired` and the agent stops — it does not queue, retry, or downgrade to a "draft send".
- Outcome language only. Banned from all client-facing copy: recovery, leak, lost, missed, broken, fix, problem, leads, AI, automation, CRM, sequences, funnels. The canonical positioning sentence is the single sanctioned use of lead-language and is copied verbatim, never paraphrased.
- One prospect, one drafted email per approval cycle. No variants A/B tested against a live prospect.

**escalation:**
- Approval pending > 48h → A6 EXCEPTION type "approval overdue 48h", Owner=Account, 48h SLA
- Send failure / bounce / deliverability signal → A6 EXCEPTION type "send failure / deliverability", Owner=Delivery, immediate (0h SLA)
- Prospect replies asking not to be contacted → A6 EXCEPTION type "angry reply / stop request", Owner=Delivery, 1h SLA, suppress permanently

**verification:** banned-word grep over the rendered `Payload` body returns zero hits before the APPROVALS row is filed. Attempting `execute_outbound()` on a pending or missing approval raises `ApprovalRequired` and journals `GATE_BLOCKED` — this is asserted, not assumed.

**Gotchas:**
- The banned list applies to CLIENT-FACING copy; internal field names and this file may name the mechanics
- "Fix" and "missed" hide in ordinary phrasing ("missed call", "quick fix") — grep the assembled body, not the template
- A drafted email is not a sent email: `Stage = "Outreach Drafted"` must never be read downstream as contact made
- Payload is truncated to 1900 chars in the APPROVALS row — the approver reviews the rendered body, so keep the canonical copy in the artifact, not only in the payload blob
