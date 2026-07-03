"""Slash command dispatch for UMH CLI."""

from __future__ import annotations

from rich.console import Console

from transports.cli import display
from transports.cli.client import APIError, UMHClient


def _api_call(console: Console, label: str, fn):
    """Wrap an API call with spinner + error handling. Returns result or None."""
    try:
        with console.status(f"[dim]{label}[/dim]", spinner="dots"):
            return fn()
    except APIError as e:
        console.print(f"  [danger]Error:[/danger] {e.detail}")
        return None
    except Exception as e:
        console.print(f"  [danger]Error:[/danger] {e}")
        return None


def handle_command(cmd: str, console: Console, client: UMHClient) -> bool:
    """Dispatch a slash command. Returns True if the REPL should exit."""
    cmd = cmd.strip().lower()

    if cmd in ("/exit", "/quit"):
        return True

    if cmd == "/clear":
        console.clear()
        return False

    if cmd == "/help":
        display.render_help(console)
        return False

    if cmd == "/status":
        pulse = _api_call(console, "Fetching status...", client.ping)
        if pulse is None:
            return False
        providers = _api_call(console, "Fetching providers...", client.providers_health)
        display.render_status(console, pulse, providers or {})
        return False

    if cmd == "/agents":
        agents = _api_call(console, "Fetching agents...", client.agents)
        if agents is not None:
            display.render_agents(console, agents)
        return False

    if cmd == "/loops":
        loops = _api_call(console, "Fetching loops...", client.loops)
        if loops is not None:
            display.render_loops(console, loops)
        return False

    if cmd == "/approvals":
        approvals = _api_call(console, "Fetching approvals...", client.approvals)
        if approvals is not None:
            display.render_approvals(console, approvals)
        return False

    if cmd == "/nodes":
        nodes = _api_call(console, "Fetching nodes...", client.nodes)
        if nodes is not None:
            display.render_nodes(console, nodes)
        return False

    if cmd == "/history":
        messages = _api_call(console, "Fetching history...", client.history)
        if messages is not None:
            display.render_history(console, messages)
        return False

    console.print(f"  [warn]Unknown command:[/warn] {cmd}")
    console.print("  [dim]Type /help for available commands[/dim]")
    return False
