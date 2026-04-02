"""
Operational Standards Template
================================
CANONICAL TEMPLATE v1.0
Maintained by: Empyrean Creative

These are pre-instance operational knowledge bases built from
authoritative frameworks. Not the same as the best practices principle
(which is dynamic research -> document -> skill). These encode proven
practitioner frameworks as executable operational rules.

Naming convention:
  [agent_name]_operational_standards.py

Inject in gateway.py:
  if agent_to_use == '[agent_id]':
      from eos_ai.[agent]_operational_standards import get_all_[agent]_standards
      standards = get_all_[agent]_standards()
      prompt = f'{standards}\\n\\n{prompt}'

Knowledge sources must be authoritative:
- Official frameworks from originators
- Proven practitioners with documented results
"""

# -- [SECTION NAME] -----------------------------------------------------------
# Source: [Authoritative source + URL]

SECTION_RULES = """
## SECTION TITLE
Source: [Author / Framework / Documentation URL]

RULE CATEGORY:
- Specific executable rule.
  Scenario: when X, do Y.
- Another rule.
  Why: [consequence if ignored].
- Never [anti-pattern]:
  [what happens when violated].
"""


def get_section_rules() -> str:
    return SECTION_RULES


def get_all_agent_standards() -> str:
    """
    Complete operational standards.
    Sources: [list authoritative sources]
    Injected by gateway.py for [domain].
    """
    return '\n\n'.join([
        '# [AGENT] OPERATIONAL STANDARDS',
        '# Sources: [list]',
        SECTION_RULES,
    ])
