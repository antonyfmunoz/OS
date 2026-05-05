#!/usr/bin/env python3
"""
PreToolUse hook.
Logs every tool call before execution.
Boris Cherny: "Log every bash command
the model runs (PreToolUse)"

PreToolUse CAN block execution (exit 2).
This implementation: log only, never block.
Blocking logic lives in PermissionRequest.
"""
import sys
import os
import json
import time

sys.path.insert(0, '/opt/OS')


def main():
    try:
        hook_input = json.load(sys.stdin)
    except Exception:
        hook_input = {}

    tool_name = hook_input.get('tool_name', '')
    tool_input = hook_input.get('tool_input', {})
    tool_use_id = hook_input.get(
        'tool_use_id', ''
    )[:8]

    # Only log Bash commands — Boris's pattern
    if tool_name == 'Bash':
        cmd = tool_input.get('command', '')
        try:
            os.makedirs('/opt/OS/logs', exist_ok=True)
            with open(
                '/opt/OS/logs/bash_commands.log',
                'a'
            ) as f:
                f.write(
                    f"{time.strftime('%Y-%m-%dT%H:%M:%S')} "
                    f"[{tool_use_id}] "
                    f"{cmd[:200]}\n"
                )
        except Exception:
            pass

    # Always exit 0 — never block
    sys.exit(0)


if __name__ == '__main__':
    main()
