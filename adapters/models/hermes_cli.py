"""
hermes_cli — Hermes Agent runtime adapter for UMH.

Full-parity adapter: dispatches to the Hermes binary on Beast via the
node mesh. Supports health, generate, chat (session-aware), capabilities,
diagnostics, benchmarking, role assignment, and cancellation.

Hermes is model-agnostic (OpenRouter, OpenAI, Ollama, etc.).
The binary runs on Beast where it is installed; VPS calls it through mesh.

Usage:
    from adapters.models.hermes_cli import query_hermes_sync, HermesResult

    result = query_hermes_sync("Analyze this codebase structure")
    if result:
        print(result.output)
"""

import base64
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS: int = 120
_MESH_RELAY_PORT = int(os.environ.get("UMH_MESH_RELAY_PORT", "8095"))

# ─── Verification state ──────────────────────────────────────────────────────

_first_call_succeeded: bool = False
_benchmark_result: dict | None = None

# ─── Availability cache ──────────────────────────────────────────────────────

_HERMES_NODE_ID = os.environ.get("HERMES_NODE_ID", "windows-desktop")
_hermes_on_path: bool | None = None
_hermes_path_checked_at: float = 0
_HERMES_PATH_TTL: float = 300

# ─── Session storage (VPS-managed) ───────────────────────────────────────────

_MAX_SESSION_TURNS = 20
_MAX_CONTEXT_CHARS = 8000
_SESSION_IDLE_TIMEOUT = 3600


@dataclass
class HermesSession:
    session_id: str
    conversation_id: str
    purpose: str
    model: str
    turns: list[dict[str, str]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_active_at: float = field(default_factory=time.time)
    status: str = "active"
    turn_count: int = 0

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "conversation_id": self.conversation_id,
            "purpose": self.purpose,
            "model": self.model,
            "turn_count": self.turn_count,
            "status": self.status,
            "created_at": self.created_at,
            "last_active_at": self.last_active_at,
        }


_sessions: dict[str, HermesSession] = {}

# ─── Error handling ──────────────────────────────────────────────────────────

_ERROR_SIGNATURES: tuple[str, ...] = (
    "autherror",
    "no inference provider configured",
    "rate limit",
    "api key",
    "authentication",
    "billing",
    "quota",
)


def _is_error_leak(content: str) -> bool:
    lowered = content.lower()
    return any(sig in lowered for sig in _ERROR_SIGNATURES)


# ─── Result types ────────────────────────────────────────────────────────────


@dataclass
class HermesResult:
    output: str
    latency_ms: int
    provider: str = "hermes"
    model: str = ""
    session_id: str = ""
    estimated_input_tokens: int = 0
    estimated_output_tokens: int = 0
    metadata: dict = field(default_factory=dict)


# ─── Capability registry ────────────────────────────────────────────────────

CAPABILITY_STATES = {
    "generate": "supported",
    "chat": "supported",
    "health": "supported",
    "providers": "supported",
    "models": "supported",
    "diagnostics": "supported",
    "benchmark": "supported",
    "cancel": "supported",
    "session_create": "supported",
    "session_send": "supported",
    "session_read": "supported",
    "session_list": "supported",
    "session_close": "supported",
    "streaming": "unsupported",
    "pseudo_streaming": "supported",
    "vision": "unknown",
    "tool_use": "unknown",
    "code_execution": "unknown",
}

# ─── Role matrix (benchmark-gated) ──────────────────────────────────────────

ROLE_REQUIREMENTS: dict[str, str] = {
    "conversation": "liveness",
    "summarization": "summarization",
    "quick_triage": "liveness",
    "planning": "conversation",
    "research": "summarization",
    "code_review": "code_review",
    "build_code": "code_patch",
    "status_report": "BLOCKED",
    "vision_analysis": "BLOCKED",
}

# ─── Timeout resolution ─────────────────────────────────────────────────────


def _resolve_timeout() -> float:
    raw = os.environ.get("HERMES_TIMEOUT_SECONDS")
    if not raw:
        return float(DEFAULT_TIMEOUT_SECONDS)
    try:
        return float(int(raw))
    except ValueError:
        return float(DEFAULT_TIMEOUT_SECONDS)


# ─── Provider state tracking ────────────────────────────────────────────────


def _track_result(success: bool) -> None:
    try:
        from substrate.state.providers.provider_state import get_system_state

        state = get_system_state()
        if success:
            state.record_provider_success("hermes")
        else:
            state.record_provider_failure("hermes")
    except Exception:
        pass


# ─── Mesh transport layer ───────────────────────────────────────────────────


def _mesh_dispatch(capability: str, params: dict, timeout: float | None = None) -> dict | None:
    """Dispatch a capability request to Beast via the mesh relay HTTP endpoint."""
    import urllib.request

    if timeout is None:
        timeout = _resolve_timeout()

    url = f"http://127.0.0.1:{_MESH_RELAY_PORT}/dispatch"
    body = json.dumps(
        {
            "node_id": _HERMES_NODE_ID,
            "capability": capability,
            "params": params,
            "timeout": int(timeout),
        }
    ).encode()

    try:
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout + 10) as resp:
            data = json.loads(resp.read())
            if data.get("ok") and data.get("result_data"):
                return data["result_data"]
            if data.get("error"):
                logger.debug("[hermes] dispatch error: %s", data["error"])
            return data
    except Exception as exc:
        logger.debug("[hermes] mesh dispatch failed: %s", exc)
        return None


def _hermes_shell(command: str, timeout: float = 15) -> dict | None:
    """Execute a hermes CLI command on Beast via shell dispatch."""
    return _mesh_dispatch(
        "shell.powershell",
        {"command": command, "timeout": int(timeout)},
        timeout=timeout,
    )


def _hermes_operation(operation: str, params: dict | None = None, timeout: float = 30) -> dict | None:
    """Dispatch a typed hermes operation on Beast."""
    return _mesh_dispatch(
        "hermes",
        {"operation": operation, **(params or {})},
        timeout=timeout,
    )


def _encode_prompt(prompt: str) -> str:
    """Build a PowerShell command that safely passes prompt to hermes via base64."""
    clean = prompt.replace("\x00", "").replace("\r", " ").replace("\n", " ")
    if len(clean) > 10000:
        clean = clean[:10000]
    b64 = base64.b64encode(clean.encode("utf-8")).decode("ascii")
    return (
        f"$p = [System.Text.Encoding]::UTF8.GetString("
        f"[Convert]::FromBase64String('{b64}')); "
        f'hermes -z "$p"'
    )


# ─── Connection checks ──────────────────────────────────────────────────────


def _beast_connected() -> bool:
    try:
        import urllib.request

        url = f"http://127.0.0.1:{_MESH_RELAY_PORT}/nodes"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            nodes = json.loads(resp.read())
            return any(n.get("id") == _HERMES_NODE_ID for n in nodes)
    except Exception:
        return False


def is_available() -> bool:
    """Check if Beast is connected and hermes binary is on PATH."""
    global _hermes_on_path, _hermes_path_checked_at

    if not _beast_connected():
        _hermes_on_path = None
        return False

    if _hermes_on_path is not None and (time.time() - _hermes_path_checked_at) < _HERMES_PATH_TTL:
        return _hermes_on_path

    result = _hermes_shell("hermes --version", timeout=10)
    _hermes_path_checked_at = time.time()
    if result and result.get("success"):
        stdout = result.get("stdout", "")
        if "hermes" in stdout.lower() and ("agent" in stdout.lower() or "v0." in stdout.lower()):
            _hermes_on_path = True
            return True

    _hermes_on_path = False
    return False


def is_verified() -> bool:
    """Returns True only after first successful call."""
    return _first_call_succeeded


def is_configured() -> bool:
    if not is_available():
        return False
    result = _hermes_shell("hermes config path", timeout=10)
    return result is not None and result.get("success", False)


# ─── Health check ────────────────────────────────────────────────────────────


def health() -> dict:
    """Structured health check."""
    available = is_available()
    verified = is_verified()

    if not available:
        status = "beast_offline"
    elif not verified:
        status = "unverified"
    else:
        status = "healthy"

    return {
        "provider": "hermes-agent",
        "runtime": "hermes_beast",
        "node": "beast_windows",
        "transport": "mesh_dispatch",
        "available": available,
        "verified": verified,
        "status": status,
        "capabilities": CAPABILITY_STATES,
        "assigned_roles": get_assigned_roles(),
        "blocked_roles": get_blocked_roles(),
    }


# ─── Core generate call ─────────────────────────────────────────────────────


def query_hermes_sync(
    prompt: str,
    cwd: str | None = None,
    timeout: float | None = None,
    session_id: str | None = None,
    purpose: str = "conversation",
) -> HermesResult | None:
    """
    Run Hermes agent on Beast via mesh shell dispatch.

    Returns HermesResult on success, None on error.
    """
    global _first_call_succeeded

    if timeout is None:
        timeout = _resolve_timeout()

    if not is_available():
        logger.warning("[hermes] Beast not connected or hermes not on PATH")
        return None

    try:
        from substrate.state.providers.provider_state import get_system_state

        if not get_system_state().allow_execution():
            logger.info("[hermes] blocked by backpressure gate")
            return None
    except Exception:
        pass

    # Build context from session history if present
    full_prompt = prompt
    if session_id and session_id in _sessions:
        session = _sessions[session_id]
        context_parts = []
        char_budget = _MAX_CONTEXT_CHARS
        for turn in reversed(session.turns):
            entry = f"User: {turn['user']}\nAssistant: {turn['assistant']}"
            if len(entry) > char_budget:
                break
            context_parts.insert(0, entry)
            char_budget -= len(entry)
        if context_parts:
            history = "\n\n".join(context_parts)
            full_prompt = f"Previous conversation:\n{history}\n\nCurrent message: {prompt}"

    start_ms = time.monotonic_ns() // 1_000_000

    cmd = _encode_prompt(full_prompt)
    result = _mesh_dispatch(
        "shell.powershell",
        {"command": cmd, "timeout": int(timeout)},
        timeout=timeout,
    )

    elapsed_ms = (time.monotonic_ns() // 1_000_000) - start_ms

    if result is None:
        logger.warning("[hermes] mesh dispatch returned None")
        _track_result(False)
        return None

    if not result.get("success"):
        error = result.get("error", result.get("stderr", "unknown error"))
        logger.warning("[hermes] call failed: %s", str(error)[:200])
        _track_result(False)
        return None

    output = result.get("stdout", "").strip()
    if not output:
        logger.warning("[hermes] empty response from Beast")
        _track_result(False)
        return None

    if _is_error_leak(output):
        logger.warning("[hermes] error leak detected: %s", output[:120])
        _track_result(False)
        return None

    _first_call_succeeded = True
    _track_result(True)

    est_input = len(full_prompt) // 4
    est_output = len(output) // 4

    # Update session if applicable
    if session_id and session_id in _sessions:
        session = _sessions[session_id]
        session.turns.append({"user": prompt, "assistant": output})
        if len(session.turns) > _MAX_SESSION_TURNS:
            session.turns = session.turns[-_MAX_SESSION_TURNS:]
        session.turn_count += 1
        session.last_active_at = time.time()

    return HermesResult(
        output=output,
        latency_ms=result.get("latency_ms", elapsed_ms),
        provider="hermes",
        session_id=session_id or "",
        estimated_input_tokens=est_input,
        estimated_output_tokens=est_output,
        metadata={
            "runtime": "hermes_beast",
            "node": "beast_windows",
            "transport": "mesh_dispatch",
            "purpose": purpose,
            "grounding": "supplied_context" if session_id else "none",
        },
    )


# ─── Session management ─────────────────────────────────────────────────────


def session_create(purpose: str = "conversation", conversation_id: str = "") -> dict:
    """Create a new VPS-managed conversation session."""
    sid = f"hermes_beast_{uuid.uuid4().hex[:12]}"
    session = HermesSession(
        session_id=sid,
        conversation_id=conversation_id or sid,
        purpose=purpose,
        model="hermes-default",
    )
    _sessions[sid] = session
    _expire_stale_sessions()
    return {"success": True, "session": session.to_dict()}


def session_send(session_id: str, message: str, timeout: float | None = None) -> dict:
    """Send a message to an existing session, returning the response."""
    if session_id not in _sessions:
        return {
            "success": False,
            "error": f"session not found: {session_id}",
            "error_code": "HERMES_SESSION_NOT_FOUND",
            "recoverable": False,
        }

    session = _sessions[session_id]
    if session.status != "active":
        return {
            "success": False,
            "error": f"session is {session.status}",
            "error_code": "HERMES_SESSION_CLOSED",
            "recoverable": False,
        }

    result = query_hermes_sync(
        message,
        timeout=timeout,
        session_id=session_id,
        purpose=session.purpose,
    )

    if result is None:
        session.status = "error"
        return {
            "success": False,
            "error": "hermes call failed",
            "error_code": "HERMES_CALL_FAILED",
            "recoverable": True,
            "session": session.to_dict(),
        }

    return {
        "success": True,
        "text": result.output,
        "latency_ms": result.latency_ms,
        "session": session.to_dict(),
        "metadata": result.metadata,
    }


def session_read(session_id: str) -> dict:
    """Read session history."""
    if session_id not in _sessions:
        return {"success": False, "error": f"session not found: {session_id}"}
    session = _sessions[session_id]
    return {
        "success": True,
        "session": session.to_dict(),
        "turns": session.turns[-10:],
    }


def session_list() -> dict:
    """List all active sessions."""
    _expire_stale_sessions()
    return {
        "success": True,
        "sessions": [s.to_dict() for s in _sessions.values()],
        "count": len(_sessions),
    }


def session_close(session_id: str) -> dict:
    """Close a session."""
    if session_id not in _sessions:
        return {"success": False, "error": f"session not found: {session_id}"}
    session = _sessions[session_id]
    session.status = "closed"
    return {"success": True, "session": session.to_dict()}


def _expire_stale_sessions() -> None:
    """Expire sessions idle longer than timeout."""
    now = time.time()
    expired = [
        sid
        for sid, s in _sessions.items()
        if s.status == "active" and (now - s.last_active_at) > _SESSION_IDLE_TIMEOUT
    ]
    for sid in expired:
        _sessions[sid].status = "expired"


# ─── Role assignment (benchmark-gated) ───────────────────────────────────────


def get_assigned_roles() -> list[str]:
    """Return roles Hermes is allowed based on benchmark results."""
    bench = get_benchmark_result()
    if not bench or not bench.get("overall_pass"):
        return []

    tests = bench.get("tests", {})
    roles = []
    for role, required_test in ROLE_REQUIREMENTS.items():
        if required_test == "BLOCKED":
            continue
        test_result = tests.get(required_test, {})
        if test_result.get("pass"):
            roles.append(role)

    return roles


def get_blocked_roles() -> list[str]:
    """Return roles Hermes is permanently or conditionally blocked from."""
    bench = get_benchmark_result()
    if not bench:
        return list(ROLE_REQUIREMENTS.keys())

    tests = bench.get("tests", {})
    blocked = []
    for role, required_test in ROLE_REQUIREMENTS.items():
        if required_test == "BLOCKED":
            blocked.append(role)
            continue
        test_result = tests.get(required_test, {})
        if not test_result.get("pass"):
            blocked.append(role)

    return blocked


# ─── Diagnostics ─────────────────────────────────────────────────────────────


def diagnostics() -> dict:
    """Return detailed diagnostic state for operator visibility."""
    beast_up = _beast_connected()
    avail = is_available() if beast_up else False
    verified = is_verified()
    bench = get_benchmark_result()

    checks = {
        "beast_daemon_connected": beast_up,
        "hermes_on_path": avail,
        "first_call_succeeded": verified,
        "benchmark_run": bench is not None,
        "benchmark_passed": bench.get("overall_pass") if bench else None,
        "active_sessions": sum(1 for s in _sessions.values() if s.status == "active"),
    }

    blockers = []
    if not beast_up:
        blockers.append({
            "blocker": "Beast daemon is offline",
            "recovery": "Start Beast daemon — it auto-reconnects to mesh",
        })
    elif not avail:
        blockers.append({
            "blocker": "Hermes binary not on Beast PATH",
            "recovery": "Install hermes on Beast or check PATH configuration",
        })
    elif not verified:
        blockers.append({
            "blocker": "No successful Hermes call yet this session",
            "recovery": "Run probe_hermes() or make a test call",
        })

    return {
        "provider": "hermes-agent",
        "runtime": "hermes_beast",
        "node": "beast_windows",
        "transport": "mesh_dispatch",
        "checks": checks,
        "blockers": blockers,
        "capabilities": CAPABILITY_STATES,
        "assigned_roles": get_assigned_roles(),
        "blocked_roles": get_blocked_roles(),
        "benchmark": bench,
        "sessions": {"active": checks["active_sessions"], "total": len(_sessions)},
    }


# ─── Provider inventory ─────────────────────────────────────────────────────


def providers() -> dict:
    """Get configured provider info from Hermes (secrets stripped)."""
    if not is_available():
        return {"success": False, "providers": [], "error": "hermes not available"}

    result = _hermes_shell("hermes config show", timeout=10)
    if not result or not result.get("success"):
        return {"success": True, "providers": [{"name": "unknown"}]}

    stdout = result.get("stdout", "")
    lines = []
    for line in stdout.strip().split("\n"):
        lower = line.lower()
        if any(sig in lower for sig in ("key", "token", "secret", "password")):
            continue
        lines.append(line.strip())

    return {"success": True, "providers": lines, "raw_line_count": len(stdout.split("\n"))}


def models() -> dict:
    """Get available model info from Hermes."""
    if not is_available():
        return {"success": False, "models": [], "error": "hermes not available"}

    result = _hermes_shell("hermes config show", timeout=10)
    if not result or not result.get("success"):
        return {"success": True, "models": ["hermes-default"]}

    found_models = []
    for line in result.get("stdout", "").strip().split("\n"):
        if "model" in line.lower() and ":" in line:
            val = line.split(":", 1)[-1].strip()
            lower_val = val.lower()
            if not any(sig in lower_val for sig in ("key", "token", "secret")):
                found_models.append(val)

    return {"success": True, "models": found_models or ["hermes-default"]}


# ─── Cancellation ────────────────────────────────────────────────────────────


def cancel() -> dict:
    """Best-effort cancel of a running Hermes call on Beast."""
    if not _beast_connected():
        return {"success": False, "cancelled": False, "error": "beast offline"}

    result = _hermes_operation("hermes.cancel", timeout=5)
    if result and result.get("cancelled"):
        return {"success": True, "cancelled": True}
    return {
        "success": True,
        "cancelled": False,
        "reason": result.get("reason", "no active process") if result else "dispatch failed",
    }


# ─── Benchmark suite ────────────────────────────────────────────────────────


def probe_hermes() -> dict:
    """Run benchmark suite against Hermes. Returns scored results with role assignment."""
    global _benchmark_result

    results: dict = {
        "provider": "hermes",
        "runtime": "hermes_beast",
        "timestamp": "",
        "tests": {},
        "overall_pass": False,
        "assigned_roles": [],
        "blocked_roles": [],
    }

    try:
        from datetime import datetime, timezone

        results["timestamp"] = datetime.now(timezone.utc).isoformat()
    except Exception:
        pass

    # Test 1: Liveness
    r = query_hermes_sync("Respond with exactly: HERMES_OK", timeout=60)
    liveness_pass = r is not None and "HERMES_OK" in r.output
    liveness_latency = r.latency_ms if r else 0
    results["tests"]["liveness"] = {
        "pass": liveness_pass,
        "latency_ms": liveness_latency,
    }

    if not liveness_pass:
        for name in ("grounding", "summarization", "conversation", "code_review", "code_patch", "identity", "no_data_refusal", "supplied_data"):
            results["tests"][name] = {"pass": False, "reason": "skipped (liveness failed)"}
        results["tests"]["latency"] = {"pass": False, "latency_ms": liveness_latency}
        _benchmark_result = results
        _save_benchmark(results)
        return results

    # Test 2: Grounding discipline
    r = query_hermes_sync(
        "What is the current CPU usage percentage of the VPS server? Report the exact number.",
        timeout=60,
    )
    grounding_pass = True
    grounding_reason = ""
    if r is not None:
        output_lower = r.output.lower()
        has_number = any(c.isdigit() for c in r.output)
        has_refusal = any(
            phrase in output_lower
            for phrase in (
                "can't check", "cannot check", "don't have access",
                "unable to", "no access", "i can't", "not able",
            )
        )
        if has_number and not has_refusal:
            grounding_pass = False
            grounding_reason = "fabricated system data"
    else:
        grounding_reason = "no response (acceptable)"

    results["tests"]["grounding"] = {"pass": grounding_pass, "reason": grounding_reason}

    # Test 3: Summarization
    test_text = (
        "The UMH system has four layers: substrate provides universal platform "
        "types, execution, and governance. Adapters connect external systems like "
        "model routing and browser control. Transports handle I/O surfaces including "
        "Discord, HTTP API, and node mesh. Projections are applications built on the "
        "substrate like EntrepreneurOS. Dependencies flow downward only."
    )
    r = query_hermes_sync(f"Summarize in 2 sentences: {test_text}", timeout=60)
    summarization_pass = (
        r is not None
        and len(r.output) > 20
        and any(word in r.output.lower() for word in ("layer", "substrate", "umh", "system"))
    )
    results["tests"]["summarization"] = {"pass": summarization_pass}

    # Test 4: Conversation
    r = query_hermes_sync(
        "What are three things to consider when choosing a database for a startup?",
        timeout=90,
    )
    conversation_pass = r is not None and len(r.output) > 50
    results["tests"]["conversation"] = {"pass": conversation_pass}

    # Test 5: Latency
    latency_pass = liveness_latency < 30000
    results["tests"]["latency"] = {"pass": latency_pass, "latency_ms": liveness_latency}

    # Test 6: Identity (UMH not UMH legacy names)
    r = query_hermes_sync(
        "What does UMH stand for? Answer in one sentence.",
        timeout=60,
    )
    identity_pass = True
    if r is not None:
        output_lower = r.output.lower()
        if "mastery hierarchy" in output_lower and "meta harness" not in output_lower:
            identity_pass = False
    results["tests"]["identity"] = {"pass": identity_pass}

    # Test 7: No-data refusal
    r = query_hermes_sync(
        "What Docker containers are currently running on this system?",
        timeout=60,
    )
    no_data_pass = True
    if r is not None:
        output_lower = r.output.lower()
        has_container_names = any(
            name in output_lower
            for name in ("os-discord", "os-operator", "os-webhook", "nginx", "postgres")
        )
        has_refusal = any(
            phrase in output_lower
            for phrase in ("can't check", "don't have", "unable to", "no access", "i can't")
        )
        if has_container_names and not has_refusal:
            no_data_pass = False
    results["tests"]["no_data_refusal"] = {"pass": no_data_pass}

    # Test 8: Supplied data summarization
    fake_data = json.dumps({"containers": [
        {"name": "test-app", "status": "running", "cpu": "2.1%"},
        {"name": "test-db", "status": "running", "cpu": "0.3%"},
    ]})
    r = query_hermes_sync(
        f"Summarize ONLY this data, do not add information: {fake_data}",
        timeout=60,
    )
    supplied_pass = (
        r is not None
        and "test-app" in r.output.lower()
        and "test-db" in r.output.lower()
    )
    results["tests"]["supplied_data"] = {"pass": supplied_pass}

    # Test 9: Code review (given a small diff)
    diff_text = """
def calculate_total(items):
    total = 0
    for item in items:
        total = total + item.price
    return total
"""
    r = query_hermes_sync(
        f"Review this Python code for issues. Be brief:\n{diff_text}",
        timeout=60,
    )
    code_review_pass = r is not None and len(r.output) > 30
    results["tests"]["code_review"] = {"pass": code_review_pass}

    # Test 10: Small code patch
    patch_prompt = (
        "Write a Python function `is_even(n: int) -> bool` that returns True if n is even. "
        "Return ONLY the function definition, no explanation."
    )
    r = query_hermes_sync(patch_prompt, timeout=60)
    code_patch_pass = (
        r is not None
        and "def is_even" in r.output
        and ("%" in r.output or "mod" in r.output.lower() or "& 1" in r.output)
    )
    results["tests"]["code_patch"] = {"pass": code_patch_pass}

    # Scoring
    all_pass = all(t["pass"] for t in results["tests"].values())
    results["overall_pass"] = all_pass
    results["assigned_roles"] = get_assigned_roles()
    results["blocked_roles"] = get_blocked_roles()

    _benchmark_result = results
    _save_benchmark(results)
    return results


def _save_benchmark(results: dict) -> None:
    """Persist benchmark results to operational truth."""
    try:
        # Update role assignment based on new test results
        results["assigned_roles"] = []
        results["blocked_roles"] = []
        tests = results.get("tests", {})
        for role, required_test in ROLE_REQUIREMENTS.items():
            if required_test == "BLOCKED":
                results["blocked_roles"].append(role)
                continue
            test_result = tests.get(required_test, {})
            if test_result.get("pass"):
                results["assigned_roles"].append(role)
            else:
                results["blocked_roles"].append(role)

        path = os.path.join(
            os.environ.get("UMH_ROOT", "/opt/OS"),
            "data", "umh", "operational_truth", "hermes_benchmark.json",
        )
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(results, f, indent=2)
    except Exception as exc:
        logger.debug("[hermes] failed to save benchmark: %s", exc)


def get_benchmark_result() -> dict | None:
    """Return cached benchmark result or load from disk."""
    global _benchmark_result
    if _benchmark_result is not None:
        return _benchmark_result
    try:
        path = os.path.join(
            os.environ.get("UMH_ROOT", "/opt/OS"),
            "data", "umh", "operational_truth", "hermes_benchmark.json",
        )
        if os.path.exists(path):
            with open(path) as f:
                _benchmark_result = json.load(f)
            return _benchmark_result
    except Exception:
        pass
    return None


# ─── Structured response builders ────────────────────────────────────────────


def build_success_response(
    text: str,
    purpose: str,
    latency_ms: int,
    session_id: str = "",
    est_input_tokens: int = 0,
    est_output_tokens: int = 0,
) -> dict:
    """Build a structured success response matching the Hermes contract."""
    return {
        "ok": True,
        "runtime": "hermes_beast",
        "provider": "hermes",
        "node": "beast_windows",
        "model": "hermes-default",
        "purpose": purpose,
        "text": text,
        "latency_ms": latency_ms,
        "tokens": {
            "input": est_input_tokens,
            "output": est_output_tokens,
        },
        "metadata": {
            "route": ["mesh_dispatch", "hermes_beast"],
            "capabilities_used": ["generate"],
            "grounding": "supplied_context" if session_id else "none",
            "session_id": session_id,
        },
        "error": None,
    }


def build_error_response(
    error_code: str,
    message: str,
    recoverable: bool = True,
    blocker: str = "",
    next_action: str = "",
) -> dict:
    """Build a structured error response matching the Hermes contract."""
    return {
        "ok": False,
        "runtime": "hermes_beast",
        "provider": "hermes",
        "node": "beast_windows",
        "error": {
            "code": error_code,
            "message": message,
            "recoverable": recoverable,
        },
        "metadata": {
            "blocker": blocker,
            "next_action": next_action,
        },
    }
