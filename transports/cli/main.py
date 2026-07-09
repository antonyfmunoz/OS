#!/usr/bin/env python3
"""UMH CLI — operator terminal interface.

Entry point. REPL loop using prompt_toolkit for input (history,
Ctrl+C handling) and Rich for output.
"""

from __future__ import annotations

import argparse
import logging

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from rich.console import Console

from transports.cli import display
from transports.cli.client import APIError, UMHClient
from transports.cli.commands import handle_command
from transports.cli.theme import BANNER_LINE, UMH_THEME, VERSION

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="umh",
        description="UMH CLI — operator terminal interface",
    )
    p.add_argument("--url", help="API base URL (default: $UMH_API_URL or localhost)")
    p.add_argument("--api-key", help="API key (default: $UMH_API_KEY)")
    p.add_argument("--version", action="version", version=f"umh {VERSION}")
    p.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")
    return p.parse_args()


def _print_banner(console: Console, base_url: str, connected: bool) -> None:
    """Print startup banner."""
    console.print()
    console.print(f"  [header]{BANNER_LINE}[/header]")
    console.print(f"  [dim]{base_url}[/dim]")
    dot = "[dot.ok]●[/dot.ok]" if connected else "[dot.danger]●[/dot.danger]"
    status = "connected" if connected else "disconnected"
    console.print(f"  API: {dot} {status}")
    console.print("  [dim]Type /help for commands[/dim]")
    console.print()


def _run_voice_capture(console: Console, client) -> str | None:
    """CLI /voice: capture push-to-talk audio → governed WS → transcript string.

    Thin edge on the ONE governed voice runtime. Returns the transcript to feed
    the converse path, or None on unavailable capture / a typed failure (the
    reason is printed). Degrades gracefully when sounddevice is not installed.
    """
    from transports.cli import cli_voice

    if not cli_voice.sounddevice_available():
        console.print(
            "  [warn]Voice needs the 'sounddevice' package.[/warn] "
            "Install: [dim]pip install sounddevice[/dim]"
        )
        return None
    try:
        console.print("  [dim]🎤 recording — press Enter to stop[/dim]")
        pcm16 = cli_voice.capture_ptt_pcm16()
        if not pcm16:
            console.print("  [warn]No audio captured.[/warn]")
            return None
        with console.status("[dim]Transcribing...[/dim]", spinner="dots"):
            result = cli_voice.transcribe_over_ws(
                pcm16,
                cli_voice._ws_url_from_base(client.base_url),
                api_key=getattr(client, "api_key", ""),
            )
        if result.get("ok"):
            return str(result.get("text", "")).strip() or None
        console.print(f"  [danger]Voice error:[/danger] {result.get('code')}")
        return None
    except Exception as e:
        console.print(f"  [danger]Voice capture failed:[/danger] {e}")
        return None


def main() -> None:
    args = _parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(name)s: %(message)s")
    else:
        logging.basicConfig(level=logging.WARNING)

    console = Console(theme=UMH_THEME)
    client = UMHClient(base_url=args.url, api_key=args.api_key)

    connected = False
    try:
        client.ping()
        connected = True
    except Exception:
        pass

    _print_banner(console, client.base_url, connected)

    if not connected:
        console.print("  [warn]Warning:[/warn] Could not reach API. Commands will fail.")
        console.print(f"  [dim]Check that the API is running at {client.base_url}[/dim]")
        console.print()

    session: PromptSession[str] = PromptSession(history=InMemoryHistory())

    # Files queued via /attach, sent as `media` on the next message so the
    # assistant understands them (same seam as browser/desktop/mobile).
    _pending_media: list[dict] = []

    while True:
        try:
            user_input = session.prompt("  > ").strip()
        except KeyboardInterrupt:
            console.print()
            continue
        except EOFError:
            console.print("\n  [dim]Goodbye.[/dim]")
            break

        if not user_input:
            continue

        # /voice — Claude-Code-style push-to-talk. Capture locally, stream to the
        # ONE governed voice WS, and use the returned transcript as the prompt.
        if user_input == "/voice":
            transcript = _run_voice_capture(console, client)
            if not transcript:
                console.print()
                continue
            console.print(f"  [dim]heard:[/dim] {transcript}")
            user_input = transcript  # fall through to the converse path

        # /attach <path> — upload a local file (image/video/audio/pdf/…) so the
        # assistant understands it on the NEXT message. Same seam as browser/mobile.
        elif user_input.startswith("/attach"):
            parts = user_input.split(maxsplit=1)
            if len(parts) < 2:
                console.print("  [dim]usage: /attach <path-to-file>[/dim]")
                console.print()
                continue
            uploaded = client.upload_media(parts[1].strip())
            if uploaded:
                _pending_media.append(uploaded)
                console.print(
                    f"  [dim]attached:[/dim] {uploaded.get('filename')} "
                    f"({uploaded.get('media_type')}) — send a message to have it understood"
                )
            else:
                console.print(f"  [danger]Could not attach:[/danger] {parts[1].strip()}")
            console.print()
            continue

        elif user_input.startswith("/"):
            should_exit = handle_command(user_input, console, client)
            if should_exit:
                console.print("  [dim]Goodbye.[/dim]")
                break
            console.print()
            continue

        try:
            _media = _pending_media[:] if _pending_media else None
            _pending_media.clear()
            with console.status("[dim]Thinking...[/dim]", spinner="dots"):
                response = client.converse(user_input, media=_media)

            if "error" in response:
                console.print(f"  [danger]Error:[/danger] {response['error']}")
            else:
                display.render_ai_response(console, response)
        except APIError as e:
            console.print(f"  [danger]Error:[/danger] {e.detail}")
        except Exception as e:
            logger.debug("Unexpected error in converse", exc_info=True)
            console.print(f"  [danger]Error:[/danger] {e}")

        console.print()

    client.close()


if __name__ == "__main__":
    main()
