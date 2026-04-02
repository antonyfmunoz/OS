---
name: crm-stage-update
description: "Standardize how every agent updates the pipeline stage in Notion — run whenever any agent touches a lead or customer record or any stage change occurs in the relationship."
allowed-tools: "Read, Bash"
version: 1.0
effort: low
trigger: both
---

# Skill: CRM Stage Update

## Purpose
Standardize how every agent updates the pipeline stage in Notion. One authoritative process. No inconsistency.

## Outcome
Notion pipeline reflects exact real-time stage of every lead and customer.

## Decision Criteria
- Any agent touching a lead or customer record
- Any stage change in the relationship

## Execution Steps
1. Identify the lead/customer record in Notion Pipeline/CRM
2. Update Stage field to the correct value:
   - Lead → Contacted → Qualified → Proposal → Negotiation → Closed Won → Active Customer → At Risk → Churned
3. Update Last Contact date to today
4. Update Next Action field with specific next step and date
5. Update Assigned To field with responsible agent
6. Add note to Notes field: what happened, what was said, what's next
7. Log event in Neon events table

## Failure Modes
- Updating stage without updating Next Action
- Generic notes that lose the conversation context
- Multiple agents touching the same record without a single source of truth
- Logging in Notion but not in Neon (or vice versa)

## Measurement
- CRM data accuracy audit weekly
- Percentage of records with all required fields complete


## Gotchas
- Add failures here as they occur.
- This section compounds over time.
