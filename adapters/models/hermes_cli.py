"""
hermes_cli — Hermes Agent adapter for UMH.

Dispatches to the Hermes binary on Beast via the node mesh.
Hermes is model-agnostic (OpenRouter, OpenAI, Ollama, etc.).
The binary runs on Beast where it is installed; VPS calls it through mesh.

Usage:
    from adapters.models.hermes_cli import query_hermes_sync

    result = query_hermes_sync("Analyze this codebase structure")
    if result:
        print(result.output)
"""

import json
import logging
import os
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS: int = 120
_MESH_RELAY_PORT = int(os.environ.get("UMH_MESH_RELAY_PORT", "8095"))

_first_call_succeeded: bool = False
_benchmark_result: dict | None = None


def _resolve_timeout() -> float:
    raw = os.environ.get("HERMES_TIMEOUT_SECONDS")
    if not raw:
        return float(DEFAULT_TIMEOUT_SECONDS)
    try:
        return float(int(raw))
    except ValueError:
        return float(DEFAULT_TIMEOUT_SECONDS)


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


@dataclass
class HermesResult:
    output: str
    latency_ms: int
    provider: str = "hermes"
    model: str = ""


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


_HERMES_NODE_ID = os.environ.get("HERMES_NODE_ID", "windows-desktop")
_hermes_on_path: bool | None = None
_hermes_path_checked_at: float = 0
_HERMES_PATH_TTL: float = 300


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


def _beast_connected() -> bool:
    """Check if Beast node is connected to the mesh."""
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
    """Check if Hermes is reachable and configured with a provider."""
    if not is_available():
        return False
    result = _hermes_shell("hermes config path", timeout=10)
    return result is not None and result.get("success", False)


def query_hermes_sync(
    prompt: str,
    cwd: str | None = None,
    timeout: float | None = None,
) -> HermesResult | None:
    """
    Run Hermes agent on Beast via mesh shell dispatch.

    Args:
        prompt: The task prompt.
        cwd: Unused (kept for API compatibility).
        timeout: Max seconds. Default from HERMES_TIMEOUT_SECONDS or 120.

    Returns:
        HermesResult on success, None on error.
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

    start_ms = time.monotonic_ns() // 1_000_000

    import base64

    clean = prompt.replace("\x00", "").replace("\r", " ").replace("\n", " ")
    if len(clean) > 4000:
        clean = clean[:4000]
    b64 = base64.b64encode(clean.encode("utf-8")).decode("ascii")
    cmd = (
        f"$p = [System.Text.Encoding]::UTF8.GetString("
        f"[Convert]::FromBase64String('{b64}')); "
        f'hermes -z "$p"'
    )
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
    return HermesResult(
        output=output,
        latency_ms=result.get("latency_ms", elapsed_ms),
        provider="hermes",
    )


def probe_hermes() -> dict:
    """Run benchmark suite against Hermes. Returns scored results.

    Tests:
    1. Liveness: "Respond with exactly: HERMES_OK"
    2. Grounding discipline: asks for real system data (must refuse)
    3. Summarization: summarize provided text
    4. Conversation: general question
    5. Latency: time the liveness probe
    """
    global _benchmark_result

    results: dict = {
        "provider": "hermes",
        "timestamp": "",
        "tests": {},
        "overall_pass": False,
        "recommended_roles": [],
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
        results["tests"]["grounding"] = {"pass": False, "reason": "skipped (liveness failed)"}
        results["tests"]["summarization"] = {"pass": False, "reason": "skipped"}
        results["tests"]["conversation"] = {"pass": False, "reason": "skipped"}
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
                "can't check",
                "cannot check",
                "don't have access",
                "unable to",
                "no access",
                "i can't",
                "not able",
            )
        )
        if has_number and not has_refusal:
            grounding_pass = False
            grounding_reason = "fabricated system data"
    else:
        grounding_pass = True
        grounding_reason = "no response (acceptable — not fabricating)"

    results["tests"]["grounding"] = {
        "pass": grounding_pass,
        "reason": grounding_reason,
    }

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
        timeout=60,
    )
    conversation_pass = r is not None and len(r.output) > 50
    results["tests"]["conversation"] = {"pass": conversation_pass}

    # Test 5: Latency
    latency_pass = liveness_latency < 30000
    results["tests"]["latency"] = {
        "pass": latency_pass,
        "latency_ms": liveness_latency,
    }

    # Scoring
    all_pass = all(t["pass"] for t in results["tests"].values())
    results["overall_pass"] = all_pass

    roles = []
    if conversation_pass:
        roles.append("conversation")
    if summarization_pass:
        roles.append("summarization")
    if latency_pass and conversation_pass:
        roles.append("quick_triage")
    if not grounding_pass:
        roles = [r for r in roles if r not in ("status_report", "research_grounding")]
    results["recommended_roles"] = roles

    _benchmark_result = results
    _save_benchmark(results)
    return results


def _save_benchmark(results: dict) -> None:
    """Persist benchmark results to operational truth."""
    try:
        path = os.path.join(
            os.environ.get("UMH_ROOT", "/opt/OS"),
            "data",
            "umh",
            "operational_truth",
            "hermes_benchmark.json",
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
            "data",
            "umh",
            "operational_truth",
            "hermes_benchmark.json",
        )
        if os.path.exists(path):
            with open(path) as f:
                _benchmark_result = json.load(f)
            return _benchmark_result
    except Exception:
        pass
    return None
