---
globs: ["agents/**", ".claude/agents/**"]
---

# Agent Rules for EOS

Soul docs (agents/*.md):
- Character only — identity, judgment,
  role boundary, communication standard,
  hard stops
- No mechanics — those live in Python modules
- No process steps — those live in skills
- Under 300 lines
- YAML frontmatter required with description
  written as trigger condition

CC native subagents (.claude/agents/*.md):
- Frontmatter: name, description, model,
  tools, context: fork, memory: user, effort
- Description: when CC should auto-delegate
- Gotchas section always
- Verification step always

Never:
- Put process steps in soul docs
- Put character in CC subagents
- Build a subagent without a verification step
- Duplicate content between soul doc and
  CC subagent — they serve different layers
