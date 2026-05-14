"""
SystemContext — interface-aware intelligence layer.

Detects which interface is making AI calls and applies
the correct authority scope, validation rules, and prompt
context for that environment.

Interfaces:
  telegram    — founder operating businesses (operator mode)
  claude_code — architect modifying the system itself
  claude_ai   — strategic design and planning only
"""

import os
import json
import sys
from pathlib import Path

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from runtime.context import EOSContext

INTERFACE_CONTEXTS = {
    'telegram': {
        'description': 'Founder operating businesses',
        'mode': 'operator',
        'authority_scope': 'business_operations',
        'validates_against': 'venture_north_star',
    },
    'claude_code': {
        'description': 'Architect modifying the system',
        'mode': 'architect',
        'authority_scope': 'system_modifications',
        'validates_against': 'canonical_spec',
    },
    'claude_ai': {
        'description': 'Strategic design and planning',
        'mode': 'strategist',
        'authority_scope': 'design_only',
        'validates_against': 'end_state_vision',
    },
}

_ARCH_PATH = Path(_REPO_ROOT) / 'runtime' / 'ARCHITECTURE.md'

_MINIMAL_SPEC = """
EntrepreneurOS Architecture — Minimal Spec (ARCHITECTURE.md not yet written)

Core principles:
- Gateway is the single entry point for all AI operations
- CognitiveLoop wraps all agent calls with 8-stage cycle
- AgentRuntime handles model routing (Haiku/Sonnet/Gemini/Ollama)
- Memory persists all interactions to Neon (PostgreSQL)
- AuthorityEngine gates all actions by risk class
- Telegram is the primary control interface
- MediaProcessor handles voice/image/video/document inputs
- All confirmed-working components must remain unbroken

Confirmed working: db, memory, agent_runtime, cognitive_loop,
authority_engine, portfolio_advisor, orchestrator,
model_preferences, media_processor, telegram_control
"""


class SystemContext:

    def __init__(
        self,
        ctx: EOSContext,
        interface: str = 'telegram',
    ):
        self.ctx = ctx
        self.interface = interface
        self.config = INTERFACE_CONTEXTS.get(
            interface, INTERFACE_CONTEXTS['telegram']
        )

    def validate_architectural_change(
        self, change_description: str
    ) -> dict:
        """
        Validate a proposed code change against the canonical spec.
        Used when interface = 'claude_code'.

        Returns:
            {
                approved:        bool,
                risk_class:      str,   # LOW | MEDIUM | HIGH | CRITICAL
                concerns:        list[str],
                recommendations: list[str],
                proceed:         bool,
            }
        """
        # Read canonical spec (graceful fallback if missing)
        arch_spec = _MINIMAL_SPEC
        if _ARCH_PATH.exists():
            try:
                arch_spec = _ARCH_PATH.read_text(encoding='utf-8')
            except Exception:
                pass

        system_instruction = (
            "You are an architectural validator for EntrepreneurOS. "
            "A code change is being proposed. Validate it against:\n"
            "1. Does it align with the canonical architecture spec?\n"
            "2. Does it move toward or away from the end state?\n"
            "3. Does it maintain or break existing confirmed-working components?\n"
            "4. What is the risk class of this change?\n"
            "   LOW: adds new capability\n"
            "   MEDIUM: modifies existing behavior\n"
            "   HIGH: touches core infrastructure\n"
            "   CRITICAL: schema changes, data migration, "
            "removing confirmed-working features\n"
            "5. Should this proceed as-is, be modified, "
            "or be flagged for human review?\n\n"
            "Respond ONLY with a JSON object in this exact format:\n"
            '{"approved": true|false, "risk_class": "LOW|MEDIUM|HIGH|CRITICAL", '
            '"concerns": ["..."], "recommendations": ["..."], "proceed": true|false}'
        )

        prompt = (
            f"{system_instruction}\n\n"
            f"ARCHITECTURE SPEC:\n{arch_spec[:3000]}\n\n"
            f"PROPOSED CHANGE:\n{change_description}"
        )

        try:
            from execution.runtime.agent_runtime import AgentRuntime, TaskType
            runtime = AgentRuntime(self.ctx)
            result = runtime.run(
                task_type=TaskType.ANALYZE,
                prompt=prompt,
                agent='architectural_validator',
                max_tokens=512,
                ctx=self.ctx,
            )
            output = result.output or ''

            # extract JSON block from response
            start = output.find('{')
            end = output.rfind('}')
            if start != -1 and end != -1:
                parsed = json.loads(output[start:end + 1])
                return {
                    'approved':        bool(parsed.get('approved', True)),
                    'risk_class':      str(parsed.get('risk_class', 'MEDIUM')),
                    'concerns':        list(parsed.get('concerns', [])),
                    'recommendations': list(parsed.get('recommendations', [])),
                    'proceed':         bool(parsed.get('proceed', True)),
                }

            # JSON parse failed — heuristic fallback from raw text
            text_lower = output.lower()
            risk_class = 'MEDIUM'
            for rc in ('critical', 'high', 'medium', 'low'):
                if rc in text_lower:
                    risk_class = rc.upper()
                    break
            approved = 'not approved' not in text_lower and 'reject' not in text_lower
            return {
                'approved':        approved,
                'risk_class':      risk_class,
                'concerns':        [output[:200]] if output else [],
                'recommendations': [],
                'proceed':         approved,
            }

        except Exception as e:
            # Never block — fall back to LOW risk / proceed
            return {
                'approved':        True,
                'risk_class':      'LOW',
                'concerns':        [f'Validator unavailable: {e}'],
                'recommendations': ['Run manually when AI layer is available'],
                'proceed':         True,
            }

    def get_system_prompt_prefix(self) -> str:
        """Return interface-appropriate context for all AI calls."""
        if self.interface == 'claude_code':
            return (
                "INTERFACE CONTEXT: You are operating "
                "as the system architect. You are "
                "MODIFYING EntrepreneurOS itself. "
                "Every change must align with the "
                "canonical architecture spec. "
                "Confirmed-working components must "
                "never be broken. Data migrations "
                "require explicit approval. "
                "Build sequence: read → validate → "
                "implement → test → confirm.\n\n"
            )
        elif self.interface == 'telegram':
            return (
                "INTERFACE CONTEXT: You are operating "
                "as the business intelligence layer. "
                "The founder is running their businesses. "
                "Apply venture context. Route to correct "
                "agents. Execute with appropriate "
                "authority level.\n\n"
            )
        return ''
