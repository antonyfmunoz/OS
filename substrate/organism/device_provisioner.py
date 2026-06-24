"""Device Provisioner — multi-OS diagnosis + role-based provisioning.

Deterministic engine. No LLM. Handles the full device onboarding
lifecycle: diagnose hardware → recommend role → provision based on role.

Controller provisioning: registry write only.
Compute node provisioning: SSH + daemon install + mesh token + verify.

The provisioner writes TOML directly to data/umh/mesh/ and signals
mesh server reload via HTTP POST (same bridge pattern as MeshReconciler).
It NEVER imports from transports/.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from adapters.ssh.ssh_utils import ssh_reachable, ssh_run, scp_to

logger = logging.getLogger(__name__)

_ROOT = os.environ.get("UMH_ROOT") or "/opt/OS"

import re

_SAFE_KEY_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

# ── Diagnosis Types ───────────────────────────────────────────────────


@dataclass
class DeviceDiagnosis:
    """Hardware diagnosis result for a discovered device."""

    hostname: str = ""
    dns_name: str = ""
    os: str = ""
    tailscale_ip: str = ""
    cpu_cores: int = 0
    ram_mb: int = 0
    gpu: str = ""
    vram_mb: int = 0
    disk_gb: int = 0
    ssh_reachable: bool = False
    recommended_role: str = "controller"
    recommended_type: str = "unknown"
    confidence: str = "low"
    raw_probes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "hostname": self.hostname,
            "dns_name": self.dns_name,
            "os": self.os,
            "tailscale_ip": self.tailscale_ip,
            "cpu_cores": self.cpu_cores,
            "ram_mb": self.ram_mb,
            "gpu": self.gpu,
            "vram_mb": self.vram_mb,
            "disk_gb": self.disk_gb,
            "ssh_reachable": self.ssh_reachable,
            "recommended_role": self.recommended_role,
            "recommended_type": self.recommended_type,
            "confidence": self.confidence,
            "raw_probes": self.raw_probes,
        }


# ── Provision Types ───────────────────────────────────────────────────


@dataclass
class ProvisionStep:
    """A single provisioning step with status tracking."""

    name: str = ""
    status: str = "pending"
    output: str = ""
    duration_ms: float = 0.0


@dataclass
class ProvisionResult:
    """Full provisioning result."""

    success: bool = False
    device_id: str = ""
    role: str = ""
    steps: list[ProvisionStep] = field(default_factory=list)
    mesh_connected: bool = False
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "device_id": self.device_id,
            "role": self.role,
            "steps": [
                {"name": s.name, "status": s.status,
                 "output": s.output, "duration_ms": s.duration_ms}
                for s in self.steps
            ],
            "mesh_connected": self.mesh_connected,
            "error": self.error,
        }


# ── Hardware Probes ───────────────────────────────────────────────────

_PROBES_LINUX = {
    "cpu_cores": "nproc",
    "ram_mb": "free -m | awk '/Mem/{print $2}'",
    "gpu": "nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null || echo ''",
    "disk_gb": "df -BG / | awk 'NR==2{gsub(/G/,\"\",$2); print $2}'",
}

_PROBES_MACOS = {
    "cpu_cores": "sysctl -n hw.ncpu",
    "ram_mb": "echo $(( $(sysctl -n hw.memsize) / 1048576 ))",
    "gpu": "system_profiler SPDisplaysDataType 2>/dev/null | grep 'Chipset Model' | head -1 | sed 's/.*: //'",
    "disk_gb": "df -g / | awk 'NR==2{print $2}'",
}

_PROBES_WINDOWS = {
    "cpu_cores": 'powershell -c "(Get-CimInstance Win32_Processor).NumberOfCores"',
    "ram_mb": 'powershell -c "[math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1MB)"',
    "gpu": 'powershell -c "(Get-CimInstance Win32_VideoController).Name"',
    "disk_gb": 'powershell -c "[math]::Round((Get-CimInstance Win32_LogicalDisk -Filter \'DeviceID=\"C:\"\').Size / 1GB)"',
}


def _detect_os_via_ssh(host: str, user: str = "root") -> str:
    """Detect remote OS via SSH. Returns 'linux', 'macos', or 'windows'."""
    ok, output = ssh_run(host, "uname -s", timeout=10, user=user)
    if ok:
        s = output.strip().lower()
        if s == "darwin":
            return "macos"
        if s == "linux":
            return "linux"
    ok2, _ = ssh_run(host, "powershell -c echo ok", timeout=10, user=user)
    if ok2:
        return "windows"
    return "unknown"


def _get_probes(os_name: str) -> dict[str, str]:
    if os_name == "linux":
        return _PROBES_LINUX
    if os_name == "macos":
        return _PROBES_MACOS
    if os_name == "windows":
        return _PROBES_WINDOWS
    return {}


def _safe_int(val: str) -> int:
    try:
        return int(val.strip().split("\n")[0].strip())
    except (ValueError, IndexError):
        return 0


# ── Diagnosis ─────────────────────────────────────────────────────────


def diagnose_device(
    hostname: str,
    tailscale_ip: str,
    os_hint: str = "",
    dns_name: str = "",
    user: str = "root",
) -> DeviceDiagnosis:
    """Diagnose a device's hardware and recommend a role."""
    diag = DeviceDiagnosis(
        hostname=hostname,
        dns_name=dns_name,
        tailscale_ip=tailscale_ip,
        os=os_hint.lower(),
    )

    if diag.os in ("ios", "ipados"):
        diag.recommended_role = "controller"
        diag.recommended_type = "mobile" if "iphone" in hostname.lower() else "tablet"
        diag.confidence = "high"
        return diag

    reachable = ssh_reachable(tailscale_ip, timeout=10, user=user)
    diag.ssh_reachable = reachable

    if not reachable:
        diag.recommended_role = "controller"
        diag.recommended_type = "unknown"
        diag.confidence = "low"
        return diag

    if not diag.os or diag.os == "unknown":
        diag.os = _detect_os_via_ssh(tailscale_ip, user=user)

    probes = _get_probes(diag.os)
    raw: dict[str, str] = {}

    for key, cmd in probes.items():
        ok, output = ssh_run(tailscale_ip, cmd, timeout=15, user=user)
        raw[key] = output if ok else ""

    diag.raw_probes = raw
    diag.cpu_cores = _safe_int(raw.get("cpu_cores", ""))
    diag.ram_mb = _safe_int(raw.get("ram_mb", ""))
    diag.gpu = raw.get("gpu", "").strip()
    diag.disk_gb = _safe_int(raw.get("disk_gb", ""))

    if diag.gpu and diag.ram_mb >= 8192:
        diag.recommended_role = "executor"
        diag.recommended_type = "pc" if diag.os == "windows" else "server"
        diag.confidence = "high"
    elif diag.ram_mb >= 4096:
        diag.recommended_role = "executor"
        diag.recommended_type = "laptop" if "macbook" in hostname.lower() else "server"
        diag.confidence = "medium"
    else:
        diag.recommended_role = "controller"
        diag.recommended_type = "laptop" if "macbook" in hostname.lower() else "unknown"
        diag.confidence = "medium"

    return diag


# ── Mesh Token (TOML Write — no transports/ import) ──────────────────


def _generate_mesh_token() -> str:
    """Generate a cryptographically random mesh auth token."""
    return base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode()


def _read_mesh_toml() -> dict[str, Any]:
    """Read the mesh config TOML."""
    path = os.path.join(_ROOT, "data", "umh", "mesh", "node_mesh_config.toml")
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib  # type: ignore[no-redef]
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        return {}
    except tomllib.TOMLDecodeError as exc:
        logger.error("corrupt mesh TOML at %s: %s", path, exc)
        return {}


def _sanitize_toml_str(val: str) -> str:
    """Escape control characters and backslashes/quotes for TOML basic strings."""
    return val.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")


def _write_mesh_toml(data: dict[str, Any]) -> None:
    """Write mesh config TOML atomically. Validates all keys against safe regex."""
    path = os.path.join(_ROOT, "data", "umh", "mesh", "node_mesh_config.toml")
    lines: list[str] = []

    server = data.get("server", {})
    if server:
        lines.append("[server]")
        for k, v in server.items():
            if not _SAFE_KEY_RE.match(str(k)):
                raise ValueError(f"Invalid TOML key: {k!r}")
            if isinstance(v, str):
                lines.append(f'{k} = "{_sanitize_toml_str(v)}"')
            elif isinstance(v, (int, float, bool)):
                lines.append(f"{k} = {v}")
        lines.append("")

    nodes = data.get("nodes", {})
    for node_id, node_data in nodes.items():
        if not _SAFE_KEY_RE.match(str(node_id)):
            raise ValueError(f"Invalid node_id: {node_id!r}")
        if isinstance(node_data, dict):
            lines.append(f"[nodes.{node_id}]")
            for k, v in node_data.items():
                if not _SAFE_KEY_RE.match(str(k)):
                    raise ValueError(f"Invalid TOML key: {k!r}")
                if isinstance(v, str):
                    lines.append(f'{k} = "{_sanitize_toml_str(v)}"')
                elif isinstance(v, (int, float, bool)):
                    lines.append(f"{k} = {v}")
            lines.append("")

    content = "\n".join(lines) + "\n"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(content)
    os.replace(tmp, path)


def _add_mesh_token(node_id: str, display_name: str) -> str:
    """Add a mesh token for a node. Returns the token."""
    data = _read_mesh_toml()
    token = _generate_mesh_token()
    if "nodes" not in data:
        data["nodes"] = {}
    if "server" not in data:
        data["server"] = {"port": 8094}
    data["nodes"][node_id] = {
        "token": token,
        "display_name": display_name,
    }
    _write_mesh_toml(data)
    return token


def remove_mesh_token(node_id: str) -> bool:
    """Remove a mesh token for a node."""
    data = _read_mesh_toml()
    nodes = data.get("nodes", {})
    if node_id not in nodes:
        return False
    del nodes[node_id]
    _write_mesh_toml(data)
    return True


def signal_mesh_reload() -> bool:
    """Signal the mesh relay to reload its config via HTTP POST."""
    relay_port = int(os.environ.get("UMH_MESH_RELAY_PORT", "8095"))
    url = f"http://127.0.0.1:{relay_port}/reload"
    try:
        req = urllib.request.Request(url, method="POST", data=b"")
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read().decode())
            return result.get("ok", False)
    except Exception as exc:
        logger.debug("Mesh reload signal failed: %s", exc)
        return False


# ── Provisioning ──────────────────────────────────────────────────────


def provision_controller(
    device_id: str,
    entry: dict[str, Any],
    registry_path: str | None = None,
) -> ProvisionResult:
    """Provision a controller device — registry write only."""
    from substrate.organism.device_registry_writer import add_device

    result = ProvisionResult(device_id=device_id, role="controller")
    step = ProvisionStep(name="registry_write")
    start = time.monotonic()

    try:
        add_device(entry, registry_path=registry_path)
        step.status = "completed"
        step.output = f"Registered {device_id}"
        result.success = True
    except Exception as exc:
        step.status = "failed"
        step.output = str(exc)
        result.error = str(exc)

    step.duration_ms = (time.monotonic() - start) * 1000
    result.steps.append(step)
    return result


def provision_compute_node(
    device_id: str,
    entry: dict[str, Any],
    tailscale_ip: str,
    os_name: str,
    user: str = "root",
    registry_path: str | None = None,
) -> ProvisionResult:
    """Provision a compute node — SSH + daemon + mesh token + verify."""
    from substrate.organism.device_registry_writer import add_device

    result = ProvisionResult(device_id=device_id, role=entry.get("role", "executor"))
    display_name = entry.get("display_name", device_id)
    mesh_node_id = entry.get("mesh_node_id", device_id)

    # Step 1: Verify SSH
    step_ssh = ProvisionStep(name="ssh_verify")
    start = time.monotonic()
    if ssh_reachable(tailscale_ip, timeout=10, user=user):
        step_ssh.status = "completed"
        step_ssh.output = "SSH reachable"
    else:
        step_ssh.status = "failed"
        step_ssh.output = "SSH unreachable"
        step_ssh.duration_ms = (time.monotonic() - start) * 1000
        result.steps.append(step_ssh)
        result.error = "SSH unreachable"
        return result
    step_ssh.duration_ms = (time.monotonic() - start) * 1000
    result.steps.append(step_ssh)

    # Step 2: Generate mesh token
    step_token = ProvisionStep(name="mesh_token")
    start = time.monotonic()
    try:
        token = _add_mesh_token(mesh_node_id, display_name)
        step_token.status = "completed"
        step_token.output = "Token generated and written to TOML"
    except Exception as exc:
        step_token.status = "failed"
        step_token.output = str(exc)
        step_token.duration_ms = (time.monotonic() - start) * 1000
        result.steps.append(step_token)
        result.error = f"Token generation failed: {exc}"
        return result
    step_token.duration_ms = (time.monotonic() - start) * 1000
    result.steps.append(step_token)

    # Step 3: Signal mesh reload
    step_reload = ProvisionStep(name="mesh_reload")
    start = time.monotonic()
    if signal_mesh_reload():
        step_reload.status = "completed"
        step_reload.output = "Mesh server reloaded"
    else:
        step_reload.status = "completed"
        step_reload.output = "Mesh reload signal failed (non-blocking)"
    step_reload.duration_ms = (time.monotonic() - start) * 1000
    result.steps.append(step_reload)

    # Step 4: Write registry
    step_reg = ProvisionStep(name="registry_write")
    start = time.monotonic()
    entry["mesh_node_id"] = mesh_node_id
    try:
        add_device(entry, registry_path=registry_path)
        step_reg.status = "completed"
        step_reg.output = f"Registered {device_id}"
    except Exception as exc:
        step_reg.status = "failed"
        step_reg.output = str(exc)
        step_reg.duration_ms = (time.monotonic() - start) * 1000
        result.steps.append(step_reg)
        result.error = str(exc)
        return result
    step_reg.duration_ms = (time.monotonic() - start) * 1000
    result.steps.append(step_reg)

    result.success = True
    return result
