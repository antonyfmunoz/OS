# Skill: Extract ICP Insight

## Purpose

Pull a reusable psychological insight from a single lead interaction that can improve targeting, messaging, and content strategy.

---

## Outcome

One precisely scoped ICP insight saved to the knowledge base — tagged, evidence-backed, and with a clear application. Specific enough to write a hook from.

---

## Best-Practice Benchmark

One sharp specific insight beats five vague ones. If the insight could apply to any human being in any market, it is not specific enough. It must reveal something true about men 18-25 who are capable but stuck.

---

## Decision Criteria

- Extract insight if: the signal contains clear evidence of a belief, desire, fear, language pattern, or objection
- Tag as `belief` if: it reveals a mental model that keeps them stuck
- Tag as `desire` if: it reveals what they actually want but haven't acted on
- Tag as `fear` if: it reveals what's blocking their decision
- Tag as `language` if: it reveals exact words worth using in messaging
- Tag as `objection` if: it reveals a reason they'd resist buying
- Skip extraction if: the signal is too vague to generalize beyond this individual

---

## Execution Steps

1. Load source material from: `03_CRM/` or `01_Inbox/processed_signals/`
2. Read the source in full
3. Identify one specific insight about the ICP's psychology
4. Generalize: does this apply broadly to the ICP, or only this individual?
5. Tag: belief | desire | fear | language | objection
6. Write the insight in one sentence
7. Record the evidence (exact quote or close paraphrase)
8. Define the application: how to use this in content or outreach
9. Save to: `07_Knowledge/ICP/[insight_slug].md`
   - `insight:` one sentence summary
   - `type:` belief | desire | fear | language | objection
   - `evidence:` exact quote or paraphrase from source
   - `application:` how to use in content or outreach

---

## Failure Modes

- Saving vague insights that don't inform any specific message or hook
- Confusing individual behavior with ICP-wide pattern before seeing recurrence
- Paraphrasing their words into your own framing — use their exact language
- Skipping extraction when the signal seems minor (small insights compound)

---

## Measurement

- Insight-to-use rate: % of saved insights that are applied in content or outreach within 30 days
- Hook conversion rate for content built directly from an insight

---

## Improvement Opportunities

- Cross-reference new insights against existing ones to detect emerging patterns
- Build frequency tracking: tag each insight with recurrence count as more signals are processed
- Promote high-frequency insights to `detect_icp_patterns` for pattern-level reporting
