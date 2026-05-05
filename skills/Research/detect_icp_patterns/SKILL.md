---
name: detect-icp-patterns
description: "Analyze all ICP insights to identify recurring patterns in the audience's psychology, language, and frustrations — run when 5+ new insights have been added or weekly as part of the intelligence cycle."
allowed-tools: "Read, Bash"
trigger: scheduled
effort: high
context: fork
version: 1.0
---

# Skill: Detect ICP Patterns

## Purpose

Analyze all ICP insights to identify recurring patterns in the audience's psychology, language, and frustrations. Converts individual insights into strategic market intelligence.

---

## Outcome

A structured pattern report covering: top frustrations, top desires, language patterns, psychological states, messaging opportunities, and offer opportunities — backed by frequency counts.

---

## Best-Practice Benchmark

Pattern frequency is signal strength. A pattern reported without frequency data is an opinion, not intelligence. Every pattern must include how many insights support it.

---

## Decision Criteria

- Report a pattern if: it appears in 3+ independent insights
- Elevate to "dominant signal" if: it appears in 5+ insights
- Tag as emerging if: it appears in 2 insights but the recency is within 7 days
- Skip individual observations that don't generalize — those stay in the individual insight files

---

## Execution Steps

1. Scan all ICP insight files in: `07_Knowledge/ICP`
2. Load each file and extract: frustrations, desires, language patterns, psychological states, obstacles
3. Group by category and count frequency
4. Identify dominant signals (5+ occurrences) and emerging signals (2 recent)
5. Generate pattern report with sections:
   - **Top Frustrations** — most common problems with frequency count
   - **Top Desires** — what outcomes the ICP most wants, with frequency count
   - **Language Patterns** — exact phrases worth using in messaging (direct quotes only)
   - **Psychological States** — most common states (e.g., Frustrated Drifter, Ambitious but Stuck)
   - **Messaging Opportunities** — new angles for marketing and content based on patterns
   - **Offer Opportunities** — insights for improving or positioning offers

---

## Failure Modes

- Reporting a pattern without citing frequency (opinion, not data)
- Merging distinct frustrations into vague categories to hit the 3+ threshold
- Including individual insights that don't meet the pattern threshold in the pattern report
- Paraphrasing exact language patterns instead of quoting them directly

---

## Measurement

- Pattern-to-content use rate: % of detected patterns that appear in content or outreach within 30 days
- Pattern accuracy: how well patterns predicted ICP response in live outreach

---

## Improvement Opportunities

- Build a pattern trend tracker — which patterns are growing in frequency vs. declining
- Add timestamp tracking to insights so recency weighting can be applied
- Cross-reference patterns with successful outreach to validate predictive accuracy

---

## Gotchas

- Running this skill on fewer than 5 insights produces noise. Wait for the threshold — patterns detected from 3 signals are opinions, not intelligence.
- Merging distinct frustrations to hit the frequency threshold is a data corruption error. "Can't focus" and "no discipline" are related but not the same. Keep them separate.
- The pattern report should not contain interpretation — it should contain patterns with frequency counts. The Intelligence Agent interprets. This skill surfaces.
- Patterns older than 90 days without corroboration from recent signals should be flagged as potentially stale. Market language shifts.
- The language patterns section must use exact quoted phrases. If you're generating plausible ICP language from memory, stop. Every pattern must be traced to a saved insight file.
- This skill should run on all ICP files in 07_Knowledge/ICP — not a subset. Running on a subset introduces selection bias that compounds across future cycles.
