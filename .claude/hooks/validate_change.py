"""
Pre-tool-use hook for EntrepreneurOS Claude Code sessions.

Fires before Write, Edit, and Bash tool calls to detect
risk level and surface warnings for high-risk operations.

Risk classes:
  LOW:      new files, new methods — proceed silently
  MEDIUM:   existing method changes — log
  HIGH:     confirmed-working core files — warn
  CRITICAL: destructive operations — warn loudly
"""

import sys
import os


HIGH_RISK_FILES = [
    'gateway.py',
    'cognitive_loop.py',
    'agent_runtime.py',
    'memory.py',
    'db.py',
    'schema.ts',
    'migrate.ts',
    'telegram_control.py',
    'authority_engine.py',
    'orchestrator.py',
]

CRITICAL_PATTERNS = [
    'DROP TABLE',
    'DELETE FROM',
    'ALTER TABLE',
    'npm run db:migrate',
    'pkill',
    'rm -rf',
]


def validate_before_change(
    tool_name: str,
    tool_input: dict,
) -> dict:
    """
    Evaluate risk before a tool executes.

    Args:
        tool_name:  'Write' | 'Edit' | 'str_replace' | 'Bash'
        tool_input: the tool's parameter dict

    Returns:
        {'proceed': bool, 'warning': str | None}
    """

    # Write or Edit on a core file
    if tool_name in ('Write', 'Edit', 'str_replace'):
        file_path = (
            tool_input.get('path', '')
            or tool_input.get('file_path', '')
        )
        is_high = any(f in file_path for f in HIGH_RISK_FILES)
        if is_high:
            fname = os.path.basename(file_path)
            return {
                'proceed': True,
                'warning': (
                    f'HIGH RISK: Modifying {fname}. '
                    f'This is a confirmed-working core component. '
                    f'Read current state first.'
                ),
            }

    # Bash — check for critical destructive patterns
    if tool_name == 'Bash':
        cmd = tool_input.get('command', '')
        matches = [
            p for p in CRITICAL_PATTERNS
            if p.lower() in cmd.lower()
        ]
        if matches:
            return {
                'proceed': True,
                'warning': (
                    f'CRITICAL OPERATION detected '
                    f'({", ".join(matches)}): '
                    f'{cmd[:100]}. '
                    f'Verify this is intentional before proceeding.'
                ),
            }

    return {'proceed': True, 'warning': None}


# ─── Stdin hook entrypoint ────────────────────────────────────────────────────
# Claude Code hooks receive JSON on stdin and write JSON to stdout.

if __name__ == '__main__':
    import json

    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
        tool_name  = data.get('tool_name', '')
        tool_input = data.get('tool_input', {})
        result = validate_before_change(tool_name, tool_input)
        # Output warning to stderr so Claude Code surfaces it
        if result.get('warning'):
            print(f"[EOS Hook] {result['warning']}", file=sys.stderr)
        # Exit 0 = proceed, exit 1 = block (we never block, only warn)
        sys.exit(0)
    except Exception as e:
        print(f"[EOS Hook] error: {e}", file=sys.stderr)
        sys.exit(0)  # never block on hook failure
