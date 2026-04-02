---
name: generate-market-report
description: "Synthesize all ICP insights and detected patterns into a clear strategic report — run when 5+ new insights have been added since the last report, or on weekly cadence."
allowed-tools: "Read, Bash"
trigger: scheduled
effort: high
context: fork
version: 1.0
---

# Skill: Generate Market Intelligence Report

## Purpose

Synthesize all ICP insights and detected patterns into a clear strategic report. Convert raw research into founder-level intelligence for content, outreach, and offer positioning.

---

## Outcome

A dated market report saved to `07_Knowledge/Reports/Market_Reports/market_report_YYYY-MM-DD.md` — covering frustrations, desires, language, psychological profile, content angles, outreach angles, and offer insights.

---

## Best-Practice Benchmark

A market report that can't be immediately acted on — that doesn't produce at least one changed message, one new hook, or one repositioned offer element — has failed its purpose.

---

## Decision Criteria

- Run this report if: 5+ new insights have been added since the last report
- Or run on weekly cadence regardless of insight count
- Elevate to "strategic priority" if: a new dominant pattern emerges that contradicts current messaging

---

## Execution Steps

1. Load all ICP insights from: `07_Knowledge/ICP`
2. Load pattern report from: `detect_icp_patterns` output
3. Synthesize: recurring frustrations, desires, objections, language patterns, psychological states
4. Generate report sections:
   - **Top Frustrations** — most common problems in the market with frequency
   - **Top Desires** — what the ICP most wants to achieve
   - **Language to Mirror** — exact phrases used by the ICP (direct quotes only)
   - **Psychological Profile** — dominant mental state description (e.g., Ambitious but Stuck)
   - **Content Angles** — content ideas based on detected patterns
   - **Outreach Angles** — outreach openings that mirror ICP language
   - **Offer Insights** — how the offer should be positioned based on this data
5. Save to: `07_Knowledge/Reports/Market_Reports/market_report_YYYY-MM-DD.md`

---

## Failure Modes

- Generating a report without running `detect_icp_patterns` first (repeating the analysis work)
- Softening ICP language in the "Language to Mirror" section — use their words, not clean versions
- Generating "offer insights" that are speculative rather than grounded in signal data
- Saving without a date — makes historical comparison impossible

---

## Measurement

- Report-to-action rate: how many content, outreach, or offer changes trace back to this report within 14 days
- Outreach angle conversion rate: reply rate on DMs using angles from this report

---

## Improvement Opportunities

- Add a diff section: what changed from last report? (new patterns, disappeared patterns)
- Track which report sections are most frequently acted on — double down on those
- Build a report confidence score based on sample size of underlying insights

---

## Gotchas

- Running this without `detect_icp_patterns` first means you're re-doing pattern analysis inside this skill. Run that skill first, then synthesize here.
- The "Language to Mirror" section must use exact quotes. The moment you clean up their language to sound better, you've destroyed the intelligence. ICP copywriting uses their actual words, not professional paraphrases.
- A report older than 14 days should not drive current outreach. Flag when the last report is getting stale so the cycle triggers.
- "Offer Insights" must be grounded in what the data says the ICP wants — not what you think the offer should be. If the data doesn't support a specific offer insight, leave it blank rather than speculate.
- This report should be read by: the CEO Agent (strategic decisions), the Content Agent (content angles), and the Outreach Agent (outreach angles). Different sections serve different agents — don't let this become a document that gets generated and not read.
