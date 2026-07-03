#!/usr/bin/env python3
"""UMH CLI — operator terminal interface.

Entry point. REPL loop using prompt_toolkit for input (history,
Ctrl+C handling) and Rich for output.
"""

from __future__ import annotations

import argparse
import logging
import sys

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

        if user_input.startswith("/"):
            should_exit = handle_command(user_input, console, client)
            if should_exit:
                console.print("  [dim]Goodbye.[/dim]")
                break
            console.print()
            continue

        try:
            with console.status("[dim]Thinking...[/dim]", spinner="dots"):
                response = client.converse(user_input)

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
