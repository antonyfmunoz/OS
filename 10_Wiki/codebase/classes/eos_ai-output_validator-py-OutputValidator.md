---
type: codebase-class
file: eos_ai/output_validator.py
line: 53
generated: 2026-04-12
---

# OutputValidator

**File:** [[eos_ai-output_validator-py]] | **Line:** 53

*No docstring.*

## Methods

- [[eos_ai-output_validator-py-OutputValidator-__init__]]`(ctx)` — 
- [[eos_ai-output_validator-py-OutputValidator-validate_discord_message]]`(content, context) → ValidationResult` — Validate any content before it is sent to Discord.
- [[eos_ai-output_validator-py-OutputValidator-validate_code_output]]`(code, file_path) → ValidationResult` — Validate code before it ships — catches hardcoded instance values.
- [[eos_ai-output_validator-py-OutputValidator-validate_skill_application]]`(task_description, output) → ValidationResult` — Check if relevant skills were applied before output was generated.
- [[eos_ai-output_validator-py-OutputValidator-log_violation]]`(result, context) → None` — Log violations to console. Post critical ones to Discord monitor channel.
