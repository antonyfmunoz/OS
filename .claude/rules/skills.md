---
globs: ["skills/**"]
---

# Skills Rules for EOS

Every SKILL.md must have:
- name: (slug, not path)
- description: written as trigger condition
  "Use when [specific condition]"
  NOT "This skill does [description]"
- trigger: scheduled|conversational|both
- effort: low|medium|high|max
- Gotchas section (add real failures over time)
- Verification step in execution steps
- context: fork if reading many files
- !`command` for dynamic context if applicable

Never:
- Write skills without a Gotchas section
- Write descriptions that describe instead
  of trigger
- Write prescriptive step-by-step when
  goals and constraints work better
- State the obvious — focus on what pushes
  CC out of default behavior
