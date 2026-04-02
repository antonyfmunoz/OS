---
name: analyze-icp-signal
description: "Extract meaningful customer intelligence from raw signals such as comments, forum posts, or conversations — run on any raw signal from Reddit, Instagram, YouTube, or DM conversations."
allowed-tools: "Read, Bash"
trigger: both
version: 1.0
---

# Skill: Analyze ICP Signal

## Purpose

Extract meaningful customer intelligence from raw signals such as comments, forum posts, or conversations. Convert unstructured signals into structured market intelligence for messaging, outreach, content, and offer development.

---

## Outcome

A structured analysis with: signal summary, pain pattern, desired transformation, language patterns, psychological state, ICP match score, content opportunities, and outreach opportunities. High-value signals saved to `07_Knowledge/ICP/`.

---

## Best-Practice Benchmark

Exact language from real people always beats AI-generated paraphrases. If you reword what they said, you lose the intelligence. Quote directly. Interpret separately.

---

## Decision Criteria

- Save as ICP insight if: ICP match is HIGH or MEDIUM and at least one reusable pattern exists
- Tag as strong ICP if: clear pain, self-awareness, and ownership language are all present
- Tag as weak ICP if: pain present but ownership language absent or external blame dominant
- Tag as not ICP if: no real pain, wrong demographic, or engagement farming signals

---

## Execution Steps

1. Accept raw signal: Reddit post/comment, Instagram comment, Quora question, YouTube comment, Twitter/X post, forum discussion, DM conversation, or sales call transcript
2. Identify the core frustration or pain signal being expressed
3. Extract the exact language used by the person — do not paraphrase
4. Identify the underlying desire or transformation they want
5. Detect the psychological state of the speaker:
   - Frustrated Drifter
   - Ambitious but Stuck
   - Curious Observer
   - Ego Defender
   - Early Adopter
6. Identify obstacles or constraints they believe are blocking them
7. Extract content opportunities: hooks, discussion topics, myth-busting angles, controversial takes
8. Determine ICP match: High / Medium / Low
9. Output structured analysis:
   - **Signal Summary** — short description of the signal
   - **Pain Pattern** — what problem the person is experiencing
   - **Desired Transformation** — what they actually want
   - **Language Patterns** — exact phrases worth saving for marketing
   - **Psychological State** — classification of the speaker
   - **ICP Match** — High / Medium / Low
   - **Content Opportunities** — list of potential hooks or angles
   - **Outreach Opportunities** — ideas for direct conversation or outreach angles
10. If ICP match is HIGH or MEDIUM: generate knowledge entry and save to `07_Knowledge/ICP/`

---

## Failure Modes

- Paraphrasing their words — always use direct quotes for language patterns
- Projecting pain that wasn't explicitly expressed
- Missing weak ICP signals because they don't match the "ideal" profile exactly
- Classifying without evidence — every classification needs a specific quote supporting it

---

## Measurement

- Signal-to-insight conversion rate: % of signals that produce a saved ICP insight
- Insight utility rate: % of saved insights referenced in content or outreach within 30 days
- ICP match accuracy: % of HIGH matches that qualify positively in outreach

---

## Improvement Opportunities

- Build a psychological state taxonomy with distinguishing markers for each state
- Track which signal sources produce the highest-quality insights
- Add recency weighting — recent signals should carry more weight in pattern detection

---

## Gotchas

- The most common error: paraphrasing what someone said because you "got the gist." The actual language is the intelligence. Paraphrase = intelligence destroyed.
- "Ambitious but Stuck" and "Frustrated Drifter" look similar on the surface. The distinction: Ambitious but Stuck has tried things and failed. Frustrated Drifter hasn't started. The outreach angle is different for each.
- Ego Defenders are high risk. They express pain but blame everything external. Low ICP match regardless of pain level because they won't take ownership.
- Reddit signals skew older than Instagram. A Reddit pattern may not reflect current Instagram ICP behavior. Note the source and don't conflate platforms.
- A signal with no ownership language is not a match even if the pain language is perfect. The offer requires self-awareness as a prerequisite.
- Don't save LOW ICP signals to 07_Knowledge/ICP. The intelligence folder should only contain actionable patterns. Low-quality signal stored = diluted pattern analysis later.
