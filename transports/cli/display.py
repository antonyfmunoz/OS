"""Rich display formatters for UMH CLI output."""

from __future__ import annotations

from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from transports.cli.theme import status_dot


def render_ai_response(console: Console, data: dict) -> None:
    """Render advisor response with markdown."""
    text = data.get("text") or data.get("response") or ""
    intent = data.get("intent", "")
    model_tier = (data.get("metadata") or {}).get("model_tier", "")

    header_parts = []
    if intent:
        header_parts.append(f"[label]{intent.upper()}[/label]")
    if model_tier:
        header_parts.append(f"[dim]{model_tier}[/dim]")
    if header_parts:
        console.print("  " + " · ".join(header_parts))

    if text:
        md = Markdown(text)
        console.print(md, style="ai", width=min(console.width - 4, 100))

    actions = data.get("suggested_actions") or []
    if actions:
        action_text = " ".join(f"[cyan][{a['label']}][/cyan]" for a in actions)
        console.print(f"  {action_text}")


def render_status(console: Console, pulse: dict, providers: dict) -> None:
    """Render /status output — system health table."""
    console.print("[header]SYSTEM STATUS[/header]")
    console.print("[dim]─────────────[/dim]")

    uptime = pulse.get("uptime_seconds", 0)
    hrs, rem = divmod(int(uptime), 3600)
    mins = rem // 60

    rows = [
        ("UPTIME", f"{hrs}h {mins}m"),
        ("CPU", f"{pulse.get('cpu_percent', '?')}%"),
        ("MEMORY", f"{pulse.get('memory_mb', '?')} MB"),
        ("AGENTS", str(pulse.get("agent_count", 0))),
        ("APPROVALS", str(pulse.get("pending_approvals", 0))),
        ("TRACES", f"{pulse.get('trace_rate', 0)}/min"),
    ]
    for label, value in rows:
        console.print(f"  [label]{label:<12}[/label] {value}")

    portfolio = providers.get("portfolio") or []
    if portfolio:
        console.print()
        console.print("[header]PROVIDERS[/header]")
        console.print("[dim]─────────[/dim]")
        for p in portfolio:
            name = p.get("name", "?")
            health = p.get("health", "unknown")
            dot = status_dot(health)
            role = p.get("role", "")
            console.print(f"  {dot} [label]{name:<16}[/label] {role}")


def render_agents(console: Console, agents: list[dict]) -> None:
    """Render /agents output."""
    console.print("[header]AGENTS[/header]")
    console.print("[dim]──────[/dim]")
    if not agents:
        console.print("  [dim]No agents registered[/dim]")
        return
    table = Table(show_header=True, show_edge=False, pad_edge=False, box=None)
    table.add_column("", width=2)
    table.add_column("NAME", style="cyan")
    table.add_column("STATUS", style="dim")
    table.add_column("ROLE", style="secondary")
    for a in agents:
        name = a.get("name", a.get("agent_id", "?"))
        st = a.get("status", "unknown")
        role = a.get("role", "")
        dot = status_dot(st)
        table.add_row(dot, name, st, role)
    console.print(table)


def render_loops(console: Console, loops: list[dict]) -> None:
    """Render /loops output."""
    console.print("[header]LOOPS[/header]")
    console.print("[dim]─────[/dim]")
    if not loops:
        console.print("  [dim]No loops registered[/dim]")
        return
    for loop in loops:
        name = loop.get("name", "?")
        state = loop.get("state", "unknown")
        dot = status_dot(state)
        interval = loop.get("interval_seconds", "?")
        last_run = loop.get("last_run", "never")
        console.print(f"  {dot} [cyan]{name}[/cyan]  interval:{interval}s  last:{last_run}")


def render_approvals(console: Console, approvals: list[dict]) -> None:
    """Render /approvals output."""
    console.print("[header]PENDING APPROVALS[/header]")
    console.print("[dim]─────────────────[/dim]")
    if not approvals:
        console.print("  [dim]No pending approvals[/dim]")
        return
    for a in approvals:
        aid = a.get("id", "?")[:8]
        intent = a.get("intent", "?")
        risk = a.get("risk_class", "?")
        console.print(f"  [warn]▸[/warn] [{aid}] {intent} [dim]({risk})[/dim]")


def render_nodes(console: Console, nodes: list[dict]) -> None:
    """Render /nodes output."""
    console.print("[header]MESH NODES[/header]")
    console.print("[dim]──────────[/dim]")
    if not nodes:
        console.print("  [dim]No nodes connected[/dim]")
        return
    for n in nodes:
        name = n.get("hostname", n.get("node_id", "?"))
        role = n.get("role", "?")
        st = n.get("status", "unknown")
        dot = status_dot(st)
        console.print(f"  {dot} [cyan]{name}[/cyan]  [dim]{role}[/dim]")


def _ai_label() -> str:
    """Instance AI name for the assistant's history label — from BIS at runtime.

    Never hardcode the AI name (instance context). Falls back to a neutral
    "AI" label when BIS/env is unset (e.g. bare CLI with no context loaded).
    """
    try:
        from substrate.state.business.business_instance import get_ai_name

        return (get_ai_name() or "AI").upper()
    except Exception:
        return "AI"


def render_history(console: Console, messages: list[dict]) -> None:
    """Render /history output."""
    console.print("[header]CHAT HISTORY[/header]")
    console.print("[dim]────────────[/dim]")
    if not messages:
        console.print("  [dim]No messages[/dim]")
        return
    ai_label = _ai_label()
    for m in messages:
        sender = m.get("sender", "?")
        content = m.get("content", "")[:120]
        ts = m.get("timestamp", "")[:19]
        if sender == "operator":
            console.print(f"  [dim]{ts}[/dim] [operator]YOU:[/operator] {content}")
        else:
            console.print(f"  [dim]{ts}[/dim] [ai]{ai_label}:[/ai] {content}")


def render_help(console: Console) -> None:
    """Render /help output."""
    console.print("[header]COMMANDS[/header]")
    console.print("[dim]────────[/dim]")
    cmds = [
        ("/status", "System health, providers, metrics"),
        ("/agents", "Agent list with status"),
        ("/loops", "Loop status (persistent + lifecycle)"),
        ("/approvals", "Pending approvals"),
        ("/nodes", "Mesh node list"),
        ("/history", "Recent chat messages"),
        ("/voice", "Push-to-talk: speak, then send the transcript"),
        ("/attach <path>", "Attach an image/video/audio/pdf/file for the assistant to understand"),
        ("/clear", "Clear screen"),
        ("/help", "This help"),
        ("/exit", "Quit"),
    ]
    for cmd, desc in cmds:
        console.print(f"  [cyan]{cmd:<14}[/cyan] [dim]{desc}[/dim]")
    console.print()
    console.print("  [dim]Type anything else to chat with the advisor.[/dim]")
