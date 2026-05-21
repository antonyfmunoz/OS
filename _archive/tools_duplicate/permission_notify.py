#!/usr/bin/env python3
"""
PermissionRequest hook.
Channel-agnostic permission notification.
Uses ChannelRouter — works with Discord,
Telegram, Webhook, or any configured channel.
"""
import sys
import os
import json
import time

sys.path.insert(0, '/opt/OS')


SAFE_TOOLS = {
    'Read', 'Grep', 'Glob',
    'WebSearch', 'WebFetch',
    'TaskList', 'TaskGet',
    'CronList',
}

SAFE_BASH_PREFIXES = [
    'echo', 'cat ', 'ls', 'grep',
    'find', 'git status', 'git log',
    'git diff', 'git branch',
    'docker ps', 'docker logs',
    'which', 'pwd', 'date',
    'python3 -c "import', 'head',
    'tail', 'wc',
]


def is_safe(tool_name: str,
            tool_input: dict) -> bool:
    if tool_name in SAFE_TOOLS:
        return True
    if tool_name == 'Bash':
        cmd = tool_input.get('command', '').strip()
        for prefix in SAFE_BASH_PREFIXES:
            if cmd.startswith(prefix):
                return True
    return False


def log_permission(tool_name: str,
                   tool_use_id: str,
                   safe: bool) -> None:
    try:
        os.makedirs('/opt/OS/logs', exist_ok=True)
        with open(
            '/opt/OS/logs/permissions.log', 'a'
        ) as f:
            f.write(
                f"{time.strftime('%Y-%m-%dT%H:%M:%S')} "
                f"tool={tool_name} "
                f"safe={safe} "
                f"id={tool_use_id[:8]}\n"
            )
    except Exception:
        pass


def main():
    try:
        hook_input = json.load(sys.stdin)
    except Exception:
        hook_input = {}

    tool_name = hook_input.get('tool_name', '')
    tool_input = hook_input.get('tool_input', {})
    tool_use_id = hook_input.get(
        'tool_use_id', 'unknown'
    )

    safe = is_safe(tool_name, tool_input)
    log_permission(tool_name, tool_use_id, safe)

    if safe:
        sys.exit(0)

    try:
        from umh.runtime_engine.channel import get_channel_router
        router = get_channel_router()
        cmd_preview = str(tool_input)[:300]
        router.request_approval(
            title=f"Permission: {tool_name}",
            body=cmd_preview,
            request_id=tool_use_id,
            is_safe=False,
        )
    except Exception as e:
        print(
            f"[Permission] Channel error: {e}",
            file=sys.stderr
        )

    sys.exit(0)


if __name__ == '__main__':
    main()
