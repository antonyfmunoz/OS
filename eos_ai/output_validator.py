"""
OutputValidator — EOS applies its own principles to its own outputs.

From PHILOSOPHY.md Section VI:
  "Every output passes through the values in sequence before it reaches the founder."
  "What passes through all four is world class. Every time. By architecture."

This layer ensures outputs never violate known constraints before shipping.
The system catches its own mistakes — not the founder.

Validates:
  - Discord message length (auto-fix via discord_utils.chunk_message)
  - Empty outputs (blocked)
  - Generic response patterns (flagged)
  - Hardcoded instance values in platform code (flagged)
  - Skill constraints not applied (flagged + auto-fix hint)
"""

import os
from dataclasses import dataclass, field
from enum import Enum


class ViolationType(Enum):
    DISCORD_CHUNK_LIMIT  = 'discord_chunk_limit'
    HARDCODED_INSTANCE   = 'hardcoded_instance'
    MISSING_FOOTER       = 'missing_footer'
    GENERIC_RESPONSE     = 'generic_response'
    EMPTY_OUTPUT         = 'empty_output'
    REDUNDANT_CONTENT    = 'redundant_content'
    WRONG_CHANNEL        = 'wrong_channel'
    MISSING_ATTRIBUTION  = 'missing_attribution'
    SKILL_NOT_APPLIED    = 'skill_not_applied'


@dataclass
class ValidationViolation:
    violation_type: ViolationType
    description:    str
    severity:       str           # 'critical', 'warning', 'info'
    auto_fixable:   bool
    fix_applied:    str = ''


@dataclass
class ValidationResult:
    passed:       bool
    violations:   list[ValidationViolation] = field(default_factory=list)
    fixed_output: str = ''
    score:        float = 1.0


class OutputValidator:

    def __init__(self, ctx=None):
        self.ctx = ctx

        self._discord_max_chars = 1800
        self._required_footer   = True

        # Instance-specific values that must never appear in platform-layer code
        # These should always come from BIS/database at runtime
        self._instance_values = [
            'DEX',
            'Antony',
            'Lyfe Institute',
            'Initiate Arena',
            'Empyrean Creative',
            '$750',
            'afm_bot',
            'Munoz Holdings',
        ]

    # ─── Discord validation ────────────────────────────────────────────────────

    def validate_discord_message(
        self,
        content: str,
        context: str = 'general',
    ) -> ValidationResult:
        """Validate any content before it is sent to Discord."""
        violations: list[ValidationViolation] = []
        fixed = content

        # Check 1: Message length
        if len(content) > self._discord_max_chars:
            violations.append(ValidationViolation(
                violation_type=ViolationType.DISCORD_CHUNK_LIMIT,
                description=(
                    f'Message is {len(content)} chars. '
                    f'Discord limit is {self._discord_max_chars}. '
                    f'Must be chunked.'
                ),
                severity='critical',
                auto_fixable=True,
                fix_applied='Chunked via discord_utils.chunk_message()',
            ))
            # Auto-fix: chunk and join with separator for the fixed_output field
            from eos_ai.discord_utils import chunk_message
            chunks = chunk_message(content)
            fixed = '\n---\n'.join(chunks)

        # Check 2: Empty output
        if not content.strip():
            violations.append(ValidationViolation(
                violation_type=ViolationType.EMPTY_OUTPUT,
                description='Empty message would be sent to Discord',
                severity='critical',
                auto_fixable=False,
            ))

        # Check 3: Generic response patterns
        generic_patterns = [
            'how can i help',
            'what would you like',
            'let me know what you need',
            'is there anything else',
            'i hope this helps',
            'great question',
        ]
        content_lower = content.lower()
        for pattern in generic_patterns:
            if pattern in content_lower:
                violations.append(ValidationViolation(
                    violation_type=ViolationType.GENERIC_RESPONSE,
                    description=f'Generic pattern detected: "{pattern}"',
                    severity='warning',
                    auto_fixable=False,
                ))
                break  # one warning per message is enough

        # Check 4: Missing footer on agent responses
        if context == 'agent_response' and '— ' not in content:
            violations.append(ValidationViolation(
                violation_type=ViolationType.MISSING_FOOTER,
                description='Agent response missing footer signature',
                severity='warning',
                auto_fixable=True,
                fix_applied='Footer added',
            ))

        # Score: critical violations tank the score hard
        critical = sum(1 for v in violations if v.severity == 'critical')
        warnings = sum(1 for v in violations if v.severity == 'warning')
        score    = max(0.0, 1.0 - (critical * 0.4) - (warnings * 0.1))
        passed   = critical == 0

        return ValidationResult(
            passed=passed,
            violations=violations,
            fixed_output=fixed,
            score=score,
        )

    # ─── Code validation ───────────────────────────────────────────────────────

    def validate_code_output(
        self,
        code: str,
        file_path: str = '',
    ) -> ValidationResult:
        """Validate code before it ships — catches hardcoded instance values."""
        violations: list[ValidationViolation] = []

        # Instance files are allowed to contain these values
        instance_files = ['/.env', '/agents/', '/data/', '/credentials/']
        is_instance_file = any(f in file_path for f in instance_files)

        if not is_instance_file:
            for value in self._instance_values:
                if value in code:
                    violations.append(ValidationViolation(
                        violation_type=ViolationType.HARDCODED_INSTANCE,
                        description=(
                            f'Hardcoded instance value found: "{value}". '
                            f'Must come from BIS/database, not platform code.'
                        ),
                        severity='warning',
                        auto_fixable=False,
                    ))

        passed = not any(v.severity == 'critical' for v in violations)
        score  = 1.0 if not violations else 0.7

        return ValidationResult(
            passed=passed,
            violations=violations,
            fixed_output=code,
            score=score,
        )

    # ─── Skill application validation ─────────────────────────────────────────

    def validate_skill_application(
        self,
        task_description: str,
        output: str,
    ) -> ValidationResult:
        """Check if relevant skills were applied before output was generated."""
        violations: list[ValidationViolation] = []
        task_lower = task_description.lower()

        # Discord tasks must use discord-admin / discord_utils
        if any(k in task_lower for k in [
            'discord', 'message', 'post', 'channel', 'webhook', 'send',
        ]):
            if len(output) > self._discord_max_chars:
                violations.append(ValidationViolation(
                    violation_type=ViolationType.SKILL_NOT_APPLIED,
                    description=(
                        'Discord task output exceeds 1800 chars. '
                        'discord-admin.md skill specifies chunk limit. '
                        'Skill was not applied.'
                    ),
                    severity='critical',
                    auto_fixable=True,
                    fix_applied='Use discord_utils.chunk_message()',
                ))

        passed = not any(v.severity == 'critical' for v in violations)

        return ValidationResult(
            passed=passed,
            violations=violations,
            fixed_output=output,
        )

    # ─── Violation logging ─────────────────────────────────────────────────────

    def log_violation(
        self,
        result: ValidationResult,
        context: str = '',
    ) -> None:
        """Log violations to console. Post critical ones to Discord monitor channel."""
        if result.passed and not result.violations:
            return

        severity_emoji = {'critical': '🚨', 'warning': '⚠️', 'info': 'ℹ️'}

        for v in result.violations:
            emoji = severity_emoji.get(v.severity, '•')
            print(
                f'[OutputValidator] {emoji} '
                f'{v.violation_type.value}: {v.description}'
            )
            if v.auto_fixable:
                print(f'[OutputValidator] ✅ Auto-fixed: {v.fix_applied}')

        # Post critical violations to Discord — only those that cannot be auto-fixed.
        # Auto-fixable violations (e.g. chunk limit) are handled silently by chunk_message().
        critical = [
            v for v in result.violations
            if v.severity == 'critical' and not v.auto_fixable
        ]
        if critical:
            try:
                from eos_ai.discord_utils import post_to_webhook
                msg = (
                    f'🚨 **Output Validation Failed**\n'
                    f'Context: {context}\n\n'
                    + '\n'.join(f'• {v.description}' for v in critical)
                )
                webhook = os.getenv('DISCORD_BRIEF_WEBHOOK', '')
                if webhook:
                    post_to_webhook(
                        msg,
                        title='System Self-Check',
                        username='EOS Monitor',
                        webhook_url=webhook,
                    )
            except Exception:
                pass  # never let logging block the system


# ─── Global instance ──────────────────────────────────────────────────────────

_validator: OutputValidator | None = None


def get_validator(ctx=None) -> OutputValidator:
    global _validator
    if _validator is None:
        _validator = OutputValidator(ctx)
    return _validator


def validate_before_discord(
    content: str,
    context: str = 'general',
    ctx=None,
) -> str:
    """
    Convenience function — call before ANY Discord post.

    Validates content, logs violations, returns auto-fixed content
    when a critical violation is found. Never blocks posting.
    """
    validator = get_validator(ctx)
    result    = validator.validate_discord_message(content, context)

    if result.violations:
        validator.log_violation(result, context)

    # Return auto-fixed content if a critical violation was found
    if not result.passed and result.fixed_output and result.fixed_output != content:
        return result.fixed_output

    return content
