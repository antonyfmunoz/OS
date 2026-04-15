---
type: codebase-function
file: scripts/salience.py
line: 163
generated: 2026-04-12
---

# score_summary

**File:** [[scripts-salience-py]] | **Line:** 163
**Signature:** `score_summary(parsed, body_text) → SalienceResult`

Score a parsed summary for salience.

Args:
    parsed: Dict with keys like decisions, constraints, entities,
            open_loops, wiki_candidates, topics, title.
...

## Calls

- [[scripts-salience-py-_consolidation_recommendation]]
- [[scripts-salience-py-_count_architecture_entities]]
- [[scripts-salience-py-_has_signal]]
- [[scripts-salience-py-_promotion_recommendation]]

## Called By

- [[scripts-salience-py-score_from_frontmatter]]
