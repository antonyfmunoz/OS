---
type: codebase-file
path: scripts/salience.py
module: scripts.salience
lines: 595
size: 22566
generated: 2026-05-07
---

# scripts/salience.py

Salience scoring for conversation summaries.

Deterministic heuristic scoring — no LLM required.
Operates on structured summary data (parsed frontmatter + body sections).

...

**Lines:** 595 | **Size:** 22,566 bytes

## Contains

- **class** [[scripts-salience-py-SalienceResult]] — 1 methods
- **class** [[scripts-salience-py-CrossSessionResult]] — 1 methods
- **fn** [[scripts-salience-py-_count_architecture_entities]]`(entities) → int`
- **fn** [[scripts-salience-py-_has_signal]]`(text, signal_set) → bool`
- **fn** [[scripts-salience-py-score_summary]]`(parsed, body_text) → SalienceResult`
- **fn** [[scripts-salience-py-_promotion_recommendation]]`(label, n_wiki_candidates) → str`
- **fn** [[scripts-salience-py-_consolidation_recommendation]]`(label) → str`
- **fn** [[scripts-salience-py-score_from_frontmatter]]`(fm, body) → SalienceResult`
- **fn** [[scripts-salience-py-_extract_list_items]]`(body, section_header) → list[str]`
- **fn** [[scripts-salience-py-_load_recent_summaries]]`(summaries_dir, exclude_session, window_days) → list[dict]`
- **fn** [[scripts-salience-py-_normalize]]`(text) → str`
- **fn** [[scripts-salience-py-_find_repeated]]`(current_items, past_summaries, field) → list[str]`
- **fn** [[scripts-salience-py-score_cross_session]]`(parsed, body_text, summaries_dir, exclude_session) → CrossSessionResult`

## Import Statements

```python
import re
from dataclasses import dataclass
from dataclasses import field
```
