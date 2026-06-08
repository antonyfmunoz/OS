"""VPS control catalog — governed command execution on the VPS node.

Every VPS command must resolve through this catalog. No raw shell injection.
Commands are declarative templates with risk classification, approval gates,
and proof collection. Natural language maps to catalog entries via
deterministic keyword matching.
"""

from __future__ import annotations

import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

_UMH_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


class VpsRisk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    BLOCKED = "blocked"


@dataclass
class CatalogEntry:
    action: str
    display_name: str
    command_template: str
    risk: VpsRisk
    requires_approval: bool
    read_only: bool
    proof_fields: list[str] = field(default_factory=lambda: ["stdout"])
    max_output_bytes: int = 8192
    description: str = ""


@dataclass
class VpsCommandResult:
    action: str
    display_name: str
    status: str  # executed | blocked | needs_approval | unsupported | error
    risk: str
    output: str = ""
    error: str = ""
    requires_approval: bool = False
    blocked_reason: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


VPS_CATALOG: dict[str, CatalogEntry] = {
    "vps_status": CatalogEntry(
        action="vps_status",
        display_name="VPS Status",
        command_template="uptime && free -h | head -3 && df -h / | tail -1",
        risk=VpsRisk.LOW,
        requires_approval=False,
        read_only=True,
        description="CPU load, memory, and disk usage",
    ),
    "cpu_usage": CatalogEntry(
        action="cpu_usage",
        display_name="CPU Usage",
        command_template="uptime",
        risk=VpsRisk.LOW,
        requires_approval=False,
        read_only=True,
    ),
    "memory_usage": CatalogEntry(
        action="memory_usage",
        display_name="Memory Usage",
        command_template="free -h",
        risk=VpsRisk.LOW,
        requires_approval=False,
        read_only=True,
    ),
    "disk_usage": CatalogEntry(
        action="disk_usage",
        display_name="Disk Usage",
        command_template="df -h / /opt",
        risk=VpsRisk.LOW,
        requires_approval=False,
        read_only=True,
    ),
    "docker_ps": CatalogEntry(
        action="docker_ps",
        display_name="Docker Containers",
        command_template='docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"',
        risk=VpsRisk.LOW,
        requires_approval=False,
        read_only=True,
    ),
    "docker_logs_operator": CatalogEntry(
        action="docker_logs_operator",
        display_name="Operator Logs",
        command_template="docker logs os-operator --tail 50 2>&1",
        risk=VpsRisk.LOW,
        requires_approval=False,
        read_only=True,
        max_output_bytes=16384,
    ),
    "docker_logs_discord": CatalogEntry(
        action="docker_logs_discord",
        display_name="Discord Bot Logs",
        command_template="docker logs os-discord --tail 50 2>&1",
        risk=VpsRisk.LOW,
        requires_approval=False,
        read_only=True,
        max_output_bytes=16384,
    ),
    "docker_restart_operator": CatalogEntry(
        action="docker_restart_operator",
        display_name="Restart Operator",
        command_template="docker restart os-operator",
        risk=VpsRisk.MEDIUM,
        requires_approval=True,
        read_only=False,
    ),
    "docker_restart_discord": CatalogEntry(
        action="docker_restart_discord",
        display_name="Restart Discord Bot",
        command_template="docker restart os-discord",
        risk=VpsRisk.MEDIUM,
        requires_approval=True,
        read_only=False,
    ),
    "provider_health": CatalogEntry(
        action="provider_health",
        display_name="Provider Health",
        command_template="__internal_provider_health__",
        risk=VpsRisk.LOW,
        requires_approval=False,
        read_only=True,
        description="LLM provider availability from model_router",
    ),
    "voice_health": CatalogEntry(
        action="voice_health",
        display_name="Voice Health",
        command_template="__internal_voice_health__",
        risk=VpsRisk.LOW,
        requires_approval=False,
        read_only=True,
        description="STT/TTS provider status",
    ),
    "git_status": CatalogEntry(
        action="git_status",
        display_name="Git Status",
        command_template=f"cd {_UMH_ROOT} && git status --short && git log --oneline -5",
        risk=VpsRisk.LOW,
        requires_approval=False,
        read_only=True,
    ),
    "tmux_list": CatalogEntry(
        action="tmux_list",
        display_name="Tmux Sessions",
        command_template="tmux list-sessions 2>&1 || echo 'no tmux sessions'",
        risk=VpsRisk.LOW,
        requires_approval=False,
        read_only=True,
    ),
    "tmux_capture": CatalogEntry(
        action="tmux_capture",
        display_name="Capture Tmux Pane",
        command_template="tmux capture-pane -p -t $(tmux list-sessions -F '#{session_name}' | head -1) 2>&1 | tail -80",
        risk=VpsRisk.LOW,
        requires_approval=False,
        read_only=True,
        max_output_bytes=16384,
    ),
    "service_status": CatalogEntry(
        action="service_status",
        display_name="Service Status",
        command_template='docker ps --format "{{.Names}}: {{.Status}}" 2>&1',
        risk=VpsRisk.LOW,
        requires_approval=False,
        read_only=True,
    ),
    "cockpit_typecheck": CatalogEntry(
        action="cockpit_typecheck",
        display_name="Cockpit TypeCheck",
        command_template=f"cd {_UMH_ROOT}/cockpit && npx tsc --noEmit 2>&1 | tail -30",
        risk=VpsRisk.MEDIUM,
        requires_approval=True,
        read_only=True,
        max_output_bytes=16384,
        description="Run TypeScript type checking on cockpit",
    ),
    "cockpit_build": CatalogEntry(
        action="cockpit_build",
        display_name="Cockpit Build",
        command_template=f"cd {_UMH_ROOT}/cockpit && npm run build 2>&1 | tail -30",
        risk=VpsRisk.MEDIUM,
        requires_approval=True,
        read_only=True,
        max_output_bytes=16384,
        description="Build the cockpit frontend",
    ),
    "python_compile_core": CatalogEntry(
        action="python_compile_core",
        display_name="Python Compile Check",
        command_template=(
            f"python3 -m py_compile {_UMH_ROOT}/substrate/organism/advisor_conversation.py && "
            f"python3 -m py_compile {_UMH_ROOT}/substrate/workstation/command_router.py && "
            f"python3 -m py_compile {_UMH_ROOT}/transports/api/cockpit.py && "
            "echo 'All core files compile OK'"
        ),
        risk=VpsRisk.LOW,
        requires_approval=False,
        read_only=True,
    ),
}

_BLOCKED_PATTERNS = [
    "cat .env",
    "cat *.env",
    "echo $",
    "printenv",
    "env | ",
    "env |",
    "set |",
    "export",
    "credentials",
    "api_key",
    "api key",
    "secret",
    "token",
    "password",
    "rm -rf",
    "rm -r /",
    "rm -f /",
    "chmod -R",
    "chown -R",
    "iptables",
    "ufw disable",
    "ufw allow",
    "firewall",
    "disable cpu gate",
    "disable governance",
    "disable gate",
    "kill -9",
    "pkill",
    "killall",
    "dd if=",
    "mkfs",
    "fdisk",
    "> /dev/",
    "wget http",
    "curl http",
    "bash -c",
    "sh -c",
    "eval ",
    "exec ",
]

_VPS_KEYWORD_MAP: list[tuple[list[str], str]] = [
    (["vps status", "server status", "show vps", "vps health"], "vps_status"),
    (["cpu usage", "cpu load", "show cpu", "how is the cpu"], "cpu_usage"),
    (["memory usage", "ram usage", "show memory", "how much memory", "show ram"], "memory_usage"),
    (["disk usage", "disk space", "show disk", "how much disk", "storage"], "disk_usage"),
    (["docker containers", "show containers", "list containers", "docker ps", "running containers"], "docker_ps"),
    (["operator logs", "show operator logs", "operator log", "latest operator"], "docker_logs_operator"),
    (["discord logs", "show discord logs", "discord log", "discord bot logs"], "docker_logs_discord"),
    (["restart operator", "restart the operator", "restart os-operator"], "docker_restart_operator"),
    (["restart discord", "restart the discord", "restart os-discord", "restart the bot"], "docker_restart_discord"),
    (["provider health", "check provider", "provider status", "llm health", "model health"], "provider_health"),
    (["voice health", "voice status", "stt status", "tts status"], "voice_health"),
    (["git status", "show git", "what branch", "git log"], "git_status"),
    (["tmux sessions", "tmux list", "list tmux", "show tmux"], "tmux_list"),
    (["capture tmux", "tmux capture", "capture the claude", "capture session", "capture the session", "capture claude code"], "tmux_capture"),
    (["service status", "show services", "what services", "running services"], "service_status"),
    (["cockpit typecheck", "typecheck cockpit", "type check", "tsc"], "cockpit_typecheck"),
    (["cockpit build", "build cockpit", "run the cockpit build", "build the cockpit", "npm build"], "cockpit_build"),
    (["python compile", "compile check", "py_compile", "compile core"], "python_compile_core"),
]


def is_vps_command(text: str) -> bool:
    """Check if text is a VPS-targeted command."""
    t = text.lower().strip()
    for keywords, _ in _VPS_KEYWORD_MAP:
        for kw in keywords:
            if kw in t:
                return True
    return _is_blocked_pattern(t)


def resolve_vps_action(text: str) -> str:
    """Map natural language to a catalog action key. Returns '' if no match."""
    t = text.lower().strip()
    for keywords, action in _VPS_KEYWORD_MAP:
        for kw in keywords:
            if kw in t:
                return action
    return ""


def _is_blocked_pattern(text: str) -> bool:
    t = text.lower()
    return any(pattern in t for pattern in _BLOCKED_PATTERNS)


def check_blocked(text: str) -> str:
    """Return a block reason if the text matches a blocked pattern, else ''."""
    t = text.lower()
    if any(p in t for p in ["environment variable", "env var", "show env", ".env", "printenv"]):
        return "Secret exposure risk — environment variables may contain API keys and credentials."
    if any(p in t for p in ["delete", "remove", "rm -", "wipe"]):
        return "Destructive file operation — requires explicit approval with exact scope."
    if any(p in t for p in ["public port", "expose", "ufw", "firewall", "iptables"]):
        return "Network exposure risk — cannot open ports or modify firewall without explicit approval."
    if any(p in t for p in ["public port", "publicly", "expose port", "open port"]):
        return "Network exposure risk — cannot open ports or modify firewall without explicit approval."
    if any(p in t for p in ["disable cpu", "disable gate", "disable governance", "disable the cpu", "disable the gate"]):
        return "Safety system cannot be disabled through voice/text commands."
    if any(p in t for p in ["secret", "credential", "password", "api key", "api_key", "token"]):
        return "Secret exposure risk — credentials cannot be displayed."
    if any(p in t for p in ["kill", "pkill", "killall"]):
        return "Process termination requires explicit target and approval."
    for pattern in _BLOCKED_PATTERNS:
        if pattern in t:
            return f"Blocked — command matches unsafe pattern."
    return ""


def execute_catalog_action(
    action: str,
    approval_override: bool = False,
) -> VpsCommandResult:
    """Execute a catalog action with full governance.

    Returns VpsCommandResult with status, output, and proof.
    Uses gated_subprocess_run for all shell commands.
    """
    entry = VPS_CATALOG.get(action)
    if not entry:
        return VpsCommandResult(
            action=action,
            display_name=action,
            status="unsupported",
            risk="unknown",
            error=f"Unknown VPS action: {action}. Available: {', '.join(sorted(VPS_CATALOG.keys()))}",
        )

    if entry.requires_approval and not approval_override:
        return VpsCommandResult(
            action=entry.action,
            display_name=entry.display_name,
            status="needs_approval",
            risk=entry.risk.value,
            requires_approval=True,
            output=f"{entry.display_name} requires operator approval (risk: {entry.risk.value}).",
        )

    if entry.command_template == "__internal_provider_health__":
        return _execute_provider_health(entry)

    if entry.command_template == "__internal_voice_health__":
        return _execute_voice_health(entry)

    return _execute_shell_command(entry)


def _execute_shell_command(entry: CatalogEntry) -> VpsCommandResult:
    """Execute a shell command through the CPU gate."""
    try:
        from substrate.execution.cpu_gate import gated_subprocess_run
    except ImportError:
        return VpsCommandResult(
            action=entry.action,
            display_name=entry.display_name,
            status="error",
            risk=entry.risk.value,
            error="CPU gate module unavailable.",
        )

    result = gated_subprocess_run(
        ["bash", "-c", entry.command_template],
        caller=f"vps_catalog:{entry.action}",
    )

    if result is None:
        return VpsCommandResult(
            action=entry.action,
            display_name=entry.display_name,
            status="blocked",
            risk=entry.risk.value,
            blocked_reason="CPU gate blocked execution — system load too high.",
        )

    stdout = result.stdout or ""
    stderr = result.stderr or ""
    if isinstance(stdout, bytes):
        stdout = stdout.decode("utf-8", errors="replace")
    if isinstance(stderr, bytes):
        stderr = stderr.decode("utf-8", errors="replace")

    output = stdout[:entry.max_output_bytes]
    if result.returncode != 0 and stderr:
        output += f"\n[stderr]: {stderr[:1024]}"

    return VpsCommandResult(
        action=entry.action,
        display_name=entry.display_name,
        status="executed",
        risk=entry.risk.value,
        output=output.strip(),
    )


def _execute_provider_health(entry: CatalogEntry) -> VpsCommandResult:
    """Read provider health from model_router without shell."""
    try:
        from adapters.models.model_router import MODEL_REGISTRY, refresh_provider_health

        try:
            refresh_provider_health()
        except Exception:
            pass

        lines = []
        for name, config in MODEL_REGISTRY.items():
            status = "healthy" if config.available else "unavailable"
            model = getattr(config, "model", "")
            lines.append(f"  {name}: {status}" + (f" ({model})" if model else ""))

        healthy_count = sum(1 for c in MODEL_REGISTRY.values() if c.available)
        total = len(MODEL_REGISTRY)
        header = f"Providers: {healthy_count}/{total} healthy"

        return VpsCommandResult(
            action=entry.action,
            display_name=entry.display_name,
            status="executed",
            risk=entry.risk.value,
            output=f"{header}\n" + "\n".join(lines),
        )
    except Exception as exc:
        return VpsCommandResult(
            action=entry.action,
            display_name=entry.display_name,
            status="error",
            risk=entry.risk.value,
            error=f"Provider health check failed: {exc}",
        )


def _execute_voice_health(entry: CatalogEntry) -> VpsCommandResult:
    """Check voice subsystem health without shell."""
    status_parts = []

    stt_provider = os.environ.get("UMH_STT_PROVIDER", "browser_native")
    tts_provider = os.environ.get("UMH_TTS_PROVIDER", "kokoro")
    tts_host = os.environ.get("KOKORO_TTS_HOST", "")

    status_parts.append(f"STT provider: {stt_provider}")
    status_parts.append(f"TTS provider: {tts_provider}")

    if tts_host:
        try:
            import urllib.request
            req = urllib.request.Request(f"http://{tts_host}/health", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                status_parts.append(f"TTS server ({tts_host}): reachable")
        except Exception:
            status_parts.append(f"TTS server ({tts_host}): unreachable")
    else:
        status_parts.append("TTS server: not configured (KOKORO_TTS_HOST unset)")

    ws_port = os.environ.get("UMH_VOICE_WS_PORT", "8095")
    status_parts.append(f"Voice WebSocket port: {ws_port}")

    return VpsCommandResult(
        action=entry.action,
        display_name=entry.display_name,
        status="executed",
        risk=entry.risk.value,
        output="\n".join(status_parts),
    )
