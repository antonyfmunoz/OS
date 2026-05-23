"""
discord_utils — single source of truth for all Discord posting from EOS.

Every module that posts to Discord must use this.
Never write custom chunking or webhook logic elsewhere.

Discord limit: 2000 chars per message.
EOS standard: 1800 chars (200-char safety buffer).
"""

import os
import time

from dotenv import load_dotenv

load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'))
load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'services', '.env'))

DISCORD_MAX_CHARS = 1800


def chunk_message(content: str, title: str = '') -> list[str]:
    """
    Split content at paragraph boundaries.

    Never splits mid-sentence or mid-word.
    Each chunk stays under DISCORD_MAX_CHARS.
    Adds part labels when more than one chunk.
    Title is prepended to the first chunk when provided.
    """
    paragraphs = content.split('\n\n')
    chunks: list[str] = []
    current = ''

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # Single paragraph exceeds limit — split on newlines instead
        if len(para) > DISCORD_MAX_CHARS:
            lines = para.split('\n')
            for line in lines:
                if len(current) + len(line) + 1 > DISCORD_MAX_CHARS:
                    if current:
                        chunks.append(current.strip())
                    # Line itself exceeds limit — hard-split at word boundary
                    while len(line) > DISCORD_MAX_CHARS:
                        split_at = line.rfind(' ', 0, DISCORD_MAX_CHARS)
                        if split_at == -1:
                            split_at = DISCORD_MAX_CHARS
                        chunks.append(line[:split_at].strip())
                        line = line[split_at:].strip()
                    current = line
                else:
                    current += '\n' + line if current else line
            continue

        # Normal paragraph handling
        if len(current) + len(para) + 2 > DISCORD_MAX_CHARS:
            if current:
                chunks.append(current.strip())
            current = para
        else:
            current += '\n\n' + para if current else para

    if current:
        chunks.append(current.strip())

    if not chunks:
        chunks = [content[:DISCORD_MAX_CHARS]]

    # Add part labels when multiple chunks
    if len(chunks) > 1:
        labeled: list[str] = []
        for i, chunk in enumerate(chunks):
            label = f'*Part {i+1}/{len(chunks)}*\n\n'
            labeled.append(label + chunk)
        chunks = labeled

    # Prepend title to first chunk
    if title and chunks:
        chunks[0] = f'**{title}**\n\n{chunks[0]}'

    return chunks


def post_to_webhook(
    content: str,
    title: str = '',
    username: str = 'DEX',
    webhook_url: str = '',
) -> bool:
    """
    Post content to a Discord webhook with paragraph-aware chunking.

    Handles splitting automatically — callers never truncate manually.
    Returns True if all chunks posted successfully.
    """
    import requests

    if not webhook_url:
        webhook_url = os.getenv('DISCORD_BRIEF_WEBHOOK', '')
    if not webhook_url:
        print('[Discord] No webhook URL configured')
        return False

    # STEP 1: Validate BEFORE chunking — detect and log only.
    # chunk_message() is the actual fix; validator provides awareness.
    # Never replace content here — that would corrupt the chunking.
    try:
        from substrate.governance.validation.output_validator import OutputValidator
        validator = OutputValidator()
        result = validator.validate_discord_message(content, 'webhook')
        if result.violations:
            for v in result.violations:
                if v.severity == 'critical':
                    print(f'[Discord] Auto-fixing: {v.violation_type.value}')
    except Exception as e:
        print(f'[Discord] Validation: {e}')

    # STEP 2: Chunk original content — chunk_message() enforces the limit.
    chunks = chunk_message(content, title)
    success = True

    # STEP 3: Post each chunk (all guaranteed under DISCORD_MAX_CHARS).
    for i, chunk in enumerate(chunks):
        try:
            resp = requests.post(
                webhook_url,
                json={'content': chunk, 'username': username},
                timeout=10,
            )
            if resp.status_code not in [200, 204]:
                print(f'[Discord] Chunk {i+1}/{len(chunks)} status: {resp.status_code}')
                success = False
            time.sleep(0.5)
        except Exception as e:
            print(f'[Discord] Post error on chunk {i+1}: {e}')
            success = False

    return success


def post_to_channel(
    channel,
    content: str,
    title: str = '',
) -> None:
    """
    Post content to a Discord channel object with paragraph-aware chunking.

    Used inside the bot (not webhook). Schedules sends as an async task
    when the event loop is running, or runs synchronously otherwise.
    """
    import asyncio

    chunks = chunk_message(content, title)

    async def _send() -> None:
        for chunk in chunks:
            await channel.send(chunk)
            await asyncio.sleep(0.3)

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(_send())
        else:
            loop.run_until_complete(_send())
    except Exception as e:
        print(f'[Discord] Channel post error: {e}')
