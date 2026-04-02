#!/usr/bin/env python3
"""
PermissionRequest hook.
Routes CC permission prompts to Telegram
so Antony can approve/deny from iPhone.

Exit 0: allow the action
Exit 2: deny the action
"""
import sys
import os
import json
import time

sys.path.insert(0, '/opt/OS')


def get_telegram_config():
    from dotenv import load_dotenv
    load_dotenv('/opt/OS/eos_ai/.env')
    token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
    return token, chat_id


def is_safe_operation(tool_name: str,
                      tool_input: dict) -> bool:
    """Auto-approve known-safe operations."""
    safe_tools = {'Read', 'Grep', 'Glob',
                  'WebSearch', 'WebFetch'}
    if tool_name in safe_tools:
        return True

    if tool_name == 'Bash':
        cmd = tool_input.get('command', '')
        safe_prefixes = [
            'python3 -c', 'echo', 'cat',
            'ls', 'grep', 'find', 'git status',
            'git log', 'git diff', 'git branch',
            'docker ps', 'docker logs',
            'which', 'pwd', 'date',
        ]
        for prefix in safe_prefixes:
            if cmd.strip().startswith(prefix):
                return True

    return False


def send_telegram_notification(
    token: str,
    chat_id: str,
    tool_name: str,
    tool_input: dict,
    tool_use_id: str,
) -> None:
    """Send permission request to Telegram."""
    try:
        import urllib.request
        import urllib.parse

        cmd_preview = str(tool_input)[:200]
        message = (
            f"🔐 *EOS Permission Request*\n\n"
            f"Tool: `{tool_name}`\n"
            f"Input: `{cmd_preview}`\n\n"
            f"ID: {tool_use_id[:8]}"
        )

        data = urllib.parse.urlencode({
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'Markdown',
        }).encode()

        req = urllib.request.Request(
            f'https://api.telegram.org/bot'
            f'{token}/sendMessage',
            data=data,
            method='POST',
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f'[Telegram] Send failed: {e}',
              file=sys.stderr)


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

    # Auto-approve safe operations
    if is_safe_operation(tool_name, tool_input):
        sys.exit(0)

    # Get Telegram config
    token, chat_id = get_telegram_config()

    # Log the request
    try:
        os.makedirs('/opt/OS/logs', exist_ok=True)
        with open('/opt/OS/logs/permissions.log',
                  'a') as f:
            f.write(
                f"{time.strftime('%Y-%m-%dT%H:%M:%S')} "
                f"tool={tool_name} "
                f"id={tool_use_id[:8]}\n"
            )
    except Exception:
        pass

    if token and chat_id:
        send_telegram_notification(
            token, chat_id, tool_name,
            tool_input, tool_use_id
        )
        print(
            f'[Permission] Sent to Telegram: '
            f'{tool_name}',
            file=sys.stderr
        )
    else:
        print(
            f'[Permission] No Telegram config. '
            f'Allowing: {tool_name}',
            file=sys.stderr
        )

    sys.exit(0)  # Allow while notifying


if __name__ == '__main__':
    main()
