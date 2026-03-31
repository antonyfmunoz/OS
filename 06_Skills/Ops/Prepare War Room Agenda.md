# Skill: Prepare War Room Agenda

## Purpose

Build the weekly War Room meeting agenda by pulling live pipeline data, content performance, and open priorities.

---

## Outcome

An agenda saved to `05_Workflows/Delivery/weekly War Room workflow.md` — completable in 30 minutes, max 3 open actions, every item tied to a decision or owner.

---

## Best-Practice Benchmark

An agenda that requires more than 30 minutes to complete or has more than 3 open actions is a planning failure, not a meeting problem. Cut ruthlessly.

---

## Decision Criteria

- Include a lead if: they are in Qualifying or Ready stage — these are highest priority
- Include a content item if: it performed above average or below average (both require decisions)
- Include a system issue if: it is blocking revenue or outreach
- Cap open actions at 3 — if more exist, prioritize by proximity to revenue

---

## Execution Steps

1. Pull current pipeline counts from: `03_CRM/Pipeline.md`
   - Count by stage: Contacted / Replied / Qualifying / Booked
2. Identify top 3 open actions from this week
3. List all leads in Qualifying or Ready stage — these are highlighted first
4. Note content posted this week and standout performance (high or low)
5. Flag any system issues or blocked workflows
6. Assemble agenda with the following sections:
   - **Pipeline snapshot** — counts by stage
   - **Hot leads** — anyone in Qualifying or Ready
   - **This week's wins** — what worked
   - **Open actions** — top 3 priorities with owner
   - **Blockers** — anything stopping progress
7. Review: is this completable in 30 minutes? Are open actions capped at 3? If no: cut.

---

## Failure Modes

- Including more than 3 open actions (creates decision paralysis)
- Listing leads who are in Cold or Contacted stage as priority (they are not)
- Reporting content performance without a decision attached to it
- Skipping blockers because they feel too complex to address in the meeting (they must be named)

---

## Measurement

- Meeting completion time (target: ≤30 minutes)
- Decision rate: % of open actions that have a clear owner and next step assigned by end of meeting
- Action completion rate: % of last week's 3 actions that were completed before this meeting

---

## Improvement Opportunities

- Track which blocker types recur and build playbooks for the common ones
- Preload hot leads section automatically from CRM pipeline data
- Add a one-line KPI dashboard at the top: revenue this week vs. target
