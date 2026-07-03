"""WorldView design tokens for terminal — matches cockpit/src/renderer/styles/tokens.css."""

from __future__ import annotations

from rich.theme import Theme

CYAN = "#00E5FF"
OK = "#00FF88"
WARN = "#FFB800"
DANGER = "#FF3D3D"
VIOLET = "#A855F7"
SURFACE = "#111111"
SURFACE_RAISED = "#1A1A1A"
TEXT_PRIMARY = "#E0E0E0"
TEXT_SECONDARY = "#888888"
TEXT_TERTIARY = "#555555"

RUNTIME_COLORS = {
    "claude": "#D4A017",
    "codex": "#00FF88",
    "hermes": "#A855F7",
    "shell": TEXT_SECONDARY,
    "browser": "#60A5FA",
    "local-model": "#FF6B6B",
}

UMH_THEME = Theme({
    "cyan": f"bold {CYAN}",
    "ok": OK,
    "warn": WARN,
    "danger": DANGER,
    "label": f"bold {TEXT_TERTIARY}",
    "dim": TEXT_TERTIARY,
    "secondary": TEXT_SECONDARY,
    "header": f"bold {CYAN}",
    "operator": TEXT_PRIMARY,
    "ai": TEXT_SECONDARY,
    "dot.ok": f"bold {OK}",
    "dot.warn": f"bold {WARN}",
    "dot.danger": f"bold {DANGER}",
})


def status_dot(status: str) -> str:
    """Return a colored dot for a connection/health status."""
    color_map = {
        "connected": "[dot.ok]●[/dot.ok]",
        "ok": "[dot.ok]●[/dot.ok]",
        "running": "[dot.ok]●[/dot.ok]",
        "healthy": "[dot.ok]●[/dot.ok]",
        "connecting": "[dot.warn]●[/dot.warn]",
        "warning": "[dot.warn]●[/dot.warn]",
        "paused": "[dot.warn]●[/dot.warn]",
        "disconnected": "[dot.danger]●[/dot.danger]",
        "error": "[dot.danger]●[/dot.danger]",
        "stopped": "[dot.danger]●[/dot.danger]",
    }
    return color_map.get(status, "[dim]●[/dim]")


VERSION = "1.0.0"
BANNER_LINE = f"UMH v{VERSION}"
