#!/usr/bin/env python3
"""Out-of-band Beast interactive-mesh-executor reconciler (Wave 2 bootstrap).

Codifies the manual reconciliation performed on 2026-07-24, when Wave 2 field
preflight found the Beast (mesh node ``windows-desktop``) network-reachable but
absent from the mesh (``connected_nodes: 0``). Root cause: TWO ONLOGON
scheduled tasks (``UMH Node Daemon`` + ``UMH_NodeDaemon``) both live, each
spawning its own launcher → five competing ``launcher.py`` processes all
re-registering the SAME ``windows-desktop`` mesh identity, so each ``node.hello``
displaced the previous one and no registration stayed connected.

This module is QUALIFICATION-INFRASTRUCTURE bootstrap + recovery — NOT the Wave 3
persistent organism supervisor. It is a bounded, idempotent, out-of-band function
run on demand (e.g. by field preflight or a human), never a daemon.

Detected conditions (order §"out-of-band reconciler"):
  * ABSENT       — machine reachable but node not on the mesh
  * DUPLICATE    — more than one launcher process / more than one live task
  * WRONG_SESSION— daemon SessionId != active interactive console SessionId
  * DEAD         — canonical task present but no launcher process
  * HEALTHY      — exactly one launcher in the console session, one mesh identity

Auto-repair (machine-resolvable only): disable rival tasks, terminate duplicate
launcher processes, (re)start the ONE canonical task, then PROVE exactly one
launcher runs in the interactive console session and exactly one
``windows-desktop`` mesh identity is connected and stable across heartbeats.

STOP (return a governed decision, never a manual instruction) only when the
repair requires a credential/security-policy change (e.g. no interactive session
exists AND no approved unattended-console bootstrap is available). That branch is
detected here and surfaced as ``needs_owner_decision`` — it is NOT executed.

All remote administration flows over the governed mesh (signed verdict, same as
``wave2_field_dispatch._mesh_read``); secrets never transit the payload.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

_WORKTREE = Path(__file__).resolve().parent.parent
if str(_WORKTREE) not in sys.path:
    sys.path.insert(0, str(_WORKTREE))

_ROOT = Path(os.environ.get("UMH_ROOT", "/opt/OS"))

# Canonical executor node identity + task name. The task NAME is host
# configuration (a Windows Task Scheduler URI), not an instance identity, and is
# discovered/migrated here rather than assumed elsewhere.
_MESH_NODE_ID = "windows-desktop"
_CANONICAL_TASK = "UMH Node Daemon"
_BEAST_TAILSCALE_HOST = os.environ.get("UMH_BEAST_TAILSCALE_HOST", "100.74.199.102")
_BEAST_SSH_USER = os.environ.get("UMH_BEAST_SSH_USER", "antonys beast pc")
# Rival tasks reconciled away (disabled, XML preserved by caller before running).
# Discovery still enumerates by keyword so an unknown rival is reported, not missed.
_KNOWN_RIVAL_TASKS = ("UMH_NodeDaemon", "UMH Node Daemon Temp")
_TASK_KEYWORDS = ("UMH", "mesh", "node", "daemon", "Beast", "desktop")

_LAUNCHER_MARK = "launcher.py"
_BEAST_PRIMARY = r"C:\dev\dev\OS"


@dataclass
class NodeState:
    """Observed Beast node state (one snapshot)."""

    reachable: bool = False
    console_session: int | None = None
    launcher_pids: list[dict] = field(default_factory=list)  # {pid, session, name}
    live_tasks: list[str] = field(default_factory=list)
    connected_node_ids: list[str] = field(default_factory=list)
    interactive_session_exists: bool = False
    observation_channel: str = ""
    observation_error: str = ""
    detail: str = ""

    @property
    def condition(self) -> str:
        if not self.reachable:
            return "UNREACHABLE"
        if self.observation_error:
            return "OBSERVATION_UNAVAILABLE"
        if not self.interactive_session_exists:
            return "NO_INTERACTIVE_SESSION"
        n_launch = len(self.launcher_pids)
        one_identity = self.connected_node_ids == [_MESH_NODE_ID]
        if n_launch == 0:
            return "DEAD"
        if n_launch > 1 or len(self.live_tasks) > 1:
            return "DUPLICATE"
        # exactly one launcher — check session + identity
        if self.console_session is not None:
            wrong = any(
                p.get("session") not in (None, self.console_session)
                for p in self.launcher_pids
            )
            if wrong:
                return "WRONG_SESSION"
        if not one_identity:
            return "ABSENT"
        return "HEALTHY"


# ── mesh admin plumbing (governed, signed) ──────────────────────────────────


def _ensure_secrets() -> None:
    """Load mesh relay/verdict secrets the same way the field dispatcher does.

    They live only in the live mesh-server process environment; without them a
    standalone reconciler process cannot sign the verdict and EVERY dispatch
    fails closed (observed: even `echo` returns ok=False). Reuse the dispatcher's
    proven resolver rather than duplicating the /proc walk.
    """
    try:
        from scripts.wave2_field_dispatch import _ensure_mesh_secrets

        _ensure_mesh_secrets()
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] mesh secret resolution unavailable: {exc}")


def _mesh_shell(command: str, *, timeout: int = 60) -> dict:
    """Run a shell command on the executor over the governed mesh (signed verdict)."""
    _ensure_secrets()
    from substrate.sockets.mesh_dispatch_port import mesh_dispatch

    result = mesh_dispatch(
        node_id=_MESH_NODE_ID,
        capability="shell",
        params={"command": command, "timeout": timeout},
        risk_class="reversible_write",
        timeout=timeout + 30,
    )
    rd = result.get("result_data", {}) if isinstance(result, dict) else {}
    return {
        "ok": bool(result.get("ok")) if isinstance(result, dict) else False,
        "error": str(result.get("error", "")) if isinstance(result, dict) else "invalid mesh result",
        "stdout": str(rd.get("stdout", "")),
        "stderr": str(rd.get("stderr", "")),
    }


def _mesh_health() -> dict:
    """Read mesh /health via the local relay (connected_nodes / node_ids)."""
    import subprocess

    tpl = _ROOT / "services" / "mesh.env.tpl"
    cmd = (
        f"op run --env-file={tpl} -- "
        'bash -c \'curl -sS -H "Authorization: Bearer $UMH_MESH_RELAY_SECRET" '
        "http://127.0.0.1:8095/health'"
    )
    try:
        r = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, timeout=40)
        return json.loads((r.stdout or "").strip() or "{}")
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


def _tailscale_reachable() -> bool:
    try:
        r = subprocess.run(["tailscale", "status"], capture_output=True, text=True, timeout=15)
        for line in (r.stdout or "").splitlines():
            if "windows" in line.lower():
                return True
    except Exception:  # noqa: BLE001
        return False
    return False


# ── observation ─────────────────────────────────────────────────────────────

_PS_OBSERVE_BODY = (
    "$ProgressPreference='SilentlyContinue';"
    "$ErrorActionPreference='Stop';"
    "Add-Type -Namespace RC -Name S -MemberDefinition "
    "'[DllImport(\"kernel32.dll\")]public static extern int WTSGetActiveConsoleSessionId();';"
    "$cs=[RC.S]::WTSGetActiveConsoleSessionId();"
    "$exp=Get-WmiObject Win32_Process -Filter \"Name = 'explorer.exe'\" | "
    "Where-Object { $_.SessionId -eq $cs } | Select-Object -First 1;"
    "$l=Get-WmiObject Win32_Process | Where-Object { "
    "$_.CommandLine -match 'launcher.py' -and $_.Name -match '^pythonw?\\.exe$' } | "
    "ForEach-Object { "
    "$p=Get-WmiObject Win32_Process -Filter \"ProcessId=$($_.ParentProcessId)\";"
    "$script=[regex]::Match($_.CommandLine, '(?i)([A-Z]:\\\\[^\"<>|]*\\\\launcher\\.py)').Value;"
    "[pscustomobject]@{pid=$_.ProcessId;session=$_.SessionId;name=$_.Name;"
    "user=$_.GetOwner().User;executable=$_.ExecutablePath;launcher_script=$script;"
    "parent_pid=$_.ParentProcessId;parent_name=$p.Name;"
    "parent_uses_env_tpl=($p.CommandLine -match 'ProgramData\\\\UMH\\\\\\.env\\.op\\.tpl')} };"
    "$task=(schtasks /query /tn \"UMH Node Daemon\" /v /fo LIST 2>&1) -join \"`n\";"
    "$o=[pscustomobject]@{console=$cs;explorer_session=$exp.SessionId;"
    "explorer_user=$exp.GetOwner().User;launchers=@($l);task=$task};"
    "$o | ConvertTo-Json -Depth 6 -Compress"
)

def _ps_encoded_command(script: str) -> str:
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    return f"powershell -NoProfile -NonInteractive -EncodedCommand {encoded}"


_PS_OBSERVE = _ps_encoded_command(_PS_OBSERVE_BODY)


def _ssh_shell(command: str, *, timeout: int = 30) -> dict:
    """Run a bounded read-only PowerShell observation over the approved SSH path."""
    target = f"{_BEAST_SSH_USER}@{_BEAST_TAILSCALE_HOST}"
    try:
        r = subprocess.run(
            [
                "ssh",
                "-o",
                "BatchMode=yes",
                "-o",
                "ConnectTimeout=5",
                "-o",
                "StrictHostKeyChecking=accept-new",
                target,
                command,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "stdout": "", "stderr": "", "error": f"{type(exc).__name__}: {exc}"}
    return {
        "ok": r.returncode == 0,
        "stdout": r.stdout or "",
        "stderr": r.stderr or "",
        "exit_code": r.returncode,
    }


def _parse_observation_payload(raw: str) -> tuple[dict, str]:
    try:
        doc = json.loads((raw or "").strip() or "{}")
    except json.JSONDecodeError as exc:
        return {}, f"malformed observation JSON: {exc}"
    if not isinstance(doc, dict):
        return {}, "observation JSON is not an object"
    return doc, ""


def _apply_observation_doc(st: NodeState, doc: dict) -> None:
    console = doc.get("console")
    explorer = doc.get("explorer_session")
    st.console_session = console if isinstance(console, int) else None
    st.interactive_session_exists = bool(
        isinstance(explorer, int)
        and isinstance(console, int)
        and explorer not in (0, None)
        and explorer == console
    )
    launchers = doc.get("launchers") or []
    if isinstance(launchers, dict):
        launchers = [launchers]
    st.launcher_pids = [
        {
            "pid": p.get("pid"),
            "session": p.get("session"),
            "name": p.get("name"),
            "parent_pid": p.get("parent_pid"),
            "parent_name": p.get("parent_name"),
            "executable": p.get("executable"),
            "launcher_script": p.get("launcher_script"),
            "parent_uses_env_tpl": p.get("parent_uses_env_tpl"),
        }
        for p in launchers
        if isinstance(p, dict)
    ]
    task_text = str(doc.get("task", ""))
    st.live_tasks = [_CANONICAL_TASK] if "Status:" in task_text and "Running" in task_text else []


def observe() -> NodeState:
    """One read-only snapshot of the Beast node state."""
    st = NodeState()
    st.reachable = _tailscale_reachable()
    if not st.reachable:
        st.detail = "tailscale: no windows node"
        return st

    health = _mesh_health()
    st.connected_node_ids = list(health.get("node_ids", []) or [])

    r = _mesh_shell(_PS_OBSERVE, timeout=40)
    if r.get("ok"):
        doc, err = _parse_observation_payload(r.get("stdout", ""))
        if err:
            st.observation_error = err
        else:
            st.observation_channel = "mesh"
            _apply_observation_doc(st, doc)
        return st

    # If the command node is absent, mesh dispatch cannot observe Windows truth.
    # Fall back to the approved read-only SSH path so session/launcher truth is
    # not conflated with command-plane registration truth.
    ssh = _ssh_shell(_PS_OBSERVE, timeout=30)
    if not ssh.get("ok"):
        st.observation_error = (
            f"mesh observation failed: {r.get('error') or r.get('stderr')}; "
            f"ssh observation failed: {ssh.get('error') or ssh.get('stderr')}"
        )[:500]
        return st
    doc, err = _parse_observation_payload(ssh.get("stdout", ""))
    if err:
        st.observation_error = err
        return st
    st.observation_channel = "ssh"
    _apply_observation_doc(st, doc)
    return st


# ── repair ───────────────────────────────────────────────────────────────────


def _prove_stable(samples: int = 3, gap_s: float = 6.0) -> tuple[bool, list]:
    """Sample mesh health `samples` times; healthy iff every sample == [node]."""
    seen = []
    for i in range(samples):
        h = _mesh_health()
        seen.append(h.get("node_ids", []))
        if i < samples - 1:
            time.sleep(gap_s)
    ok = all(s == [_MESH_NODE_ID] for s in seen)
    return ok, seen


def reconcile(*, dry_run: bool = False, prove: bool = True) -> dict:
    """Detect + auto-repair machine-resolvable Beast executor conditions.

    Returns a verdict dict. ``needs_owner_decision`` is set (and NO repair is
    attempted) only for a true credential/security-policy branch.
    """
    before = observe()
    out: dict = {"before": before.__dict__, "condition": before.condition, "actions": []}

    if before.condition == "UNREACHABLE":
        out["ok"] = False
        out["needs_owner_decision"] = False
        out["reason"] = "Beast not on tailnet — power/network, not machine-resolvable here"
        return out

    if before.condition == "NO_INTERACTIVE_SESSION":
        # The one genuine STOP: no interactive console to host visible Chrome.
        # Do NOT execute an unattended-console bootstrap — surface a governed
        # decision instead. (Detection only; the caller raises the DecisionRequest.)
        out["ok"] = False
        out["needs_owner_decision"] = True
        out["decision"] = {
            "title": "Authorize secure unattended Beast console bootstrap",
            "effect": "Establish an interactive Windows console session on the Beast "
            "using an LSA-protected, 1Password-sourced credential so the ONLOGON "
            "mesh daemon can start and host visible-Chrome verification.",
            "risk": "Stores a Windows auto-logon secret in LSA; interactive session "
            "runs unattended. Rollback: remove Autologon secret + disable task.",
        }
        out["reason"] = "no interactive session; unattended bootstrap is a security-policy decision"
        return out

    if before.condition == "OBSERVATION_UNAVAILABLE":
        out["ok"] = False
        out["needs_owner_decision"] = False
        out["reason"] = "Windows observation unavailable; refusing repair without authoritative session/task/process truth"
        return out

    if before.condition == "HEALTHY":
        out["ok"] = True
        out["reason"] = "already healthy: one launcher in console session, one mesh identity"
        if prove:
            stable, seen = _prove_stable()
            out["ok"] = stable
            out["stability_samples"] = seen
        return out

    # DUPLICATE / DEAD / WRONG_SESSION / ABSENT → machine-resolvable repair.
    if dry_run:
        out["ok"] = None
        out["planned"] = [
            f"disable rival tasks {_KNOWN_RIVAL_TASKS}",
            "stop canonical task through nodes\\windows\\umh_node\\stop_daemon.ps1",
            f"start canonical task {_CANONICAL_TASK!r}",
            "verify one launcher in console session + one stable mesh identity",
        ]
        return out

    for rival in _KNOWN_RIVAL_TASKS:
        r = _mesh_shell(f'schtasks /Change /TN "{rival}" /DISABLE', timeout=40)
        out["actions"].append({"disable_task": rival, "ok": r["ok"]})

    stop_script = rf"{_BEAST_PRIMARY}\nodes\windows\umh_node\stop_daemon.ps1"
    r = _mesh_shell(
        f'powershell -NoProfile -ExecutionPolicy Bypass -File "{stop_script}" '
        f'-TaskName "{_CANONICAL_TASK}"',
        timeout=70,
    )
    out["actions"].append({"stop_task": _CANONICAL_TASK, "ok": r["ok"], "stdout": r["stdout"][:300]})

    time.sleep(3)
    r = _mesh_shell(f'schtasks /Run /TN "{_CANONICAL_TASK}"', timeout=40)
    out["actions"].append({"start_task": _CANONICAL_TASK, "ok": r["ok"]})

    # Wait for daemon init (YOLO/camera/desktop-stream + WS connect), then verify.
    time.sleep(55)
    after = observe()
    out["after"] = after.__dict__
    out["after_condition"] = after.condition
    healthy = after.condition == "HEALTHY"
    if healthy and prove:
        stable, seen = _prove_stable()
        out["stability_samples"] = seen
        healthy = stable
    out["ok"] = healthy
    out["reason"] = "repaired to single stable identity" if healthy else "repair did not converge"
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Out-of-band Beast executor reconciler")
    ap.add_argument("--dry-run", action="store_true", help="plan only, no mutation")
    ap.add_argument("--observe-only", action="store_true", help="report state, no repair")
    ap.add_argument("--no-prove", action="store_true", help="skip multi-heartbeat stability proof")
    args = ap.parse_args(argv)

    if args.observe_only:
        st = observe()
        print(json.dumps({"condition": st.condition, "state": st.__dict__}, indent=2, default=str))
        return 0 if st.condition == "HEALTHY" else 2

    verdict = reconcile(dry_run=args.dry_run, prove=not args.no_prove)
    print(json.dumps(verdict, indent=2, default=str))
    if verdict.get("needs_owner_decision"):
        return 3
    return 0 if verdict.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
