---
type: codebase-function
file: core/tool_mastery_research_agent/github_extractor.py
line: 100
generated: 2026-04-12
---

# parse_github_url

**File:** [[core-tool_mastery_research_agent-github_extractor-py]] | **Line:** 100
**Signature:** `parse_github_url(url) → RepoCoordinates | None`

Return ``(owner, repo)`` if ``url`` points at a GitHub repo.

Accepts common variants:
    https://github.com/owner/repo
    https://github.com/owner/repo.git
...

## Called By

- [[core-tool_mastery_research_agent-github_extractor-py-expand_github_repo]]
