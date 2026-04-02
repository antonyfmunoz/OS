---
name: adversarial-review
description: "Use after any code implementation before marking task complete. Runs two-model adversarial review: Claude Code writes, Codex reviews adversarially, CC synthesizes. Boris Cherny: second Claude as staff engineer before execution."
allowed-tools: "Read, Bash"
effort: high
trigger: both
context: fork
version: "1.0"
last_updated: "2026-04-02"
---

# Adversarial Code Review

## Purpose

Boris Cherny's adversarial review pattern:
Claude Code writes -> Codex reviews critically
-> CC synthesizes -> stronger output.

EOS implementation: eos-code-reviewer subagent
performs the adversarial pass.
adversarial_code_review() in model_router.py
handles the two-model orchestration.

## When to Run

- After any code change by Developer Agent
- Before any PR is created
- Before any skill is marked complete
- When quality matters more than speed

## Execution Steps

1. Identify what was just built or changed.
   Read the file(s) fully.

2. Run adversarial review:
   !`python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.model_router import adversarial_code_review
import sys as _s
code = open(_s.argv[1]).read() if len(_s.argv)>1 else ''
if code:
    result = adversarial_code_review(code)
    print(result)
" $FILE_PATH 2>/dev/null`

3. Parse the critique.
   Address every CRITICAL before proceeding.
   Consider every WARNING.
   Incorporate synthesis into final output.

4. Verify the improved version:
   python3 -m py_compile $FILE_PATH
   python3 -c "import sys;
     sys.path.insert(0,'/opt/OS');
     import [module]"

5. Only mark complete after verification passes.

## Gotchas

- Codex must be authenticated (codex --version)
- If Codex unavailable: eos-code-reviewer
  subagent performs single-model adversarial pass
- adversarial_code_review() currently returns input
  unchanged — Codex subprocess is unstable.
  Restore when Codex exec is stable or
  Anthropic credits available.
- Never skip review because "it's a small change"
  — small changes break systems
- CRITICAL findings are blocking — fix before done
- adversarial_code_review() uses --bare -p internally
  so it needs ANTHROPIC_API_KEY or CC auth
