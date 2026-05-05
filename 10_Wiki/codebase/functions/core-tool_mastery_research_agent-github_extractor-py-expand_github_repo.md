---
type: codebase-function
file: core/tool_mastery_research_agent/github_extractor.py
line: 290
generated: 2026-04-12
---

# expand_github_repo

**File:** [[core-tool_mastery_research_agent-github_extractor-py]] | **Line:** 290
**Signature:** `expand_github_repo(ref) → tuple[list[SourceRef], list[str]]`

Expand a GitHub repo SourceRef into raw.githubusercontent.com children.

Returns ``(new_refs, notes)``. ``new_refs`` is empty if the URL is
not a repo, the API call failed, or the repo has no prioritisable
files. Every failure path writes an explanatory note — we never
...

## Calls

- [[core-tool_mastery_research_agent-github_extractor-py-_classify_label]]
- [[core-tool_mastery_research_agent-github_extractor-py-_get_default_branch_sha]]
- [[core-tool_mastery_research_agent-github_extractor-py-_list_tree]]
- [[core-tool_mastery_research_agent-github_extractor-py-_prioritise_files]]
- [[core-tool_mastery_research_agent-github_extractor-py-_raw_url]]
- [[core-tool_mastery_research_agent-github_extractor-py-parse_github_url]]
