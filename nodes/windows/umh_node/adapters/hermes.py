"""Hermes adapter — wraps Hermes CLI on the Beast machine.

Hermes is a model-agnostic agent that routes to whatever provider
is configured inside it (OpenRouter, OpenAI, Ollama, etc.).
This adapter runs on Beast where the hermes binary actually exists.

Operations:
  hermes.generate     — single-shot prompt → response
  hermes.health       — liveness probe
  hermes.providers    — configured provider info (secrets stripped)
  hermes.models       — available model info
  hermes.capabilities — what this adapter can do
  hermes.diagnostics  — detailed health/config/error state
  hermes.benchmark    — run benchmark suite
  hermes.cancel       — best-effort cancel of running process
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import threading
import time
from typing import Any

from nodes.windows.umh_node.subprocess_utils import no_window_kwargs

logger = logging.getLogger(__name__)

_ERROR_SIGNATURES = (
    "autherror",
    "no inference provider configured",
    "rate limit",
    "api key",
    "authentication",
    "billing",
    "quota",
)

_SECRET_INDICATORS = ("key", "token", "secret", "password", "credential")

_OPERATION_MAP = {
    "hermes.generate",
    "hermes.health",
    "hermes.providers",
    "hermes.models",
    "hermes.capabilities",
    "hermes.diagnostics",
    "hermes.benchmark",
    "hermes.cancel",
    "hermes.probe",
    "hermes.info",
}

_MAX_PROMPT_CHARS = 10_000
_MAX_OUTPUT_CHARS = 20_000


def _is_error_leak(content: str) -> bool:
    lowered = content.lower()
    return any(sig in lowered for sig in _ERROR_SIGNATURES)


def _redact_secrets(text: str) -> str:
    for sig in _SECRET_INDICATORS:
        if sig in text.lower():
            return "redacted"
    return text


class HermesAdapter:
    """Executes Hermes CLI commands on Beast."""

    def __init__(self) -> None:
        self._available = shutil.which("hermes") is not None
        self._active_process: subprocess.Popen[str] | None = None
        self._process_lock = threading.Lock()
        self._last_error: str = ""
        self._last_success_at: float = 0
        self._call_count: int = 0

    def execute(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self._available:
            return {
                "success": False,
                "error": "hermes binary not found on PATH",
                "error_code": "HERMES_UNAVAILABLE",
                "recoverable": False,
            }

        if operation not in _OPERATION_MAP:
            return {
                "success": False,
                "error": f"unknown operation: {operation}",
                "error_code": "HERMES_UNSUPPORTED_OPERATION",
                "recoverable": False,
                "supported_operations": sorted(_OPERATION_MAP),
            }

        dispatch = {
            "hermes.generate": self._generate,
            "hermes.health": self._health,
            "hermes.probe": self._health,
            "hermes.providers": self._providers,
            "hermes.models": self._models,
            "hermes.info": self._info,
            "hermes.capabilities": self._capabilities,
            "hermes.diagnostics": self._diagnostics,
            "hermes.benchmark": self._benchmark,
            "hermes.cancel": self._cancel,
        }
        handler = dispatch.get(operation)
        if handler is None:
            return {"success": False, "error": f"no handler for {operation}"}
        return handler(params)

    def _generate(self, params: dict[str, Any]) -> dict[str, Any]:
        prompt = params.get("prompt", "")
        timeout = min(params.get("timeout", 120), 300)

        if not prompt:
            return {
                "success": False,
                "error": "no prompt provided",
                "error_code": "HERMES_INVALID_INPUT",
                "recoverable": False,
            }

        if len(prompt) > _MAX_PROMPT_CHARS:
            prompt = prompt[:_MAX_PROMPT_CHARS]

        start = time.monotonic()
        self._call_count += 1
        try:
            proc = subprocess.Popen(
                ["hermes", "-z", prompt],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                **no_window_kwargs(),
            )
            with self._process_lock:
                self._active_process = proc

            try:
                stdout, stderr = proc.communicate(timeout=timeout)
            finally:
                with self._process_lock:
                    self._active_process = None

            elapsed_ms = int((time.monotonic() - start) * 1000)
            output = (stdout or "").strip()

            if proc.returncode != 0:
                self._last_error = (stderr or "").strip()[:500]
                return {
                    "success": False,
                    "error": f"hermes exited {proc.returncode}: {self._last_error}",
                    "error_code": "HERMES_PROCESS_ERROR",
                    "recoverable": True,
                    "latency_ms": elapsed_ms,
                }

            if not output or _is_error_leak(output):
                self._last_error = "error leak or empty output"
                return {
                    "success": False,
                    "error": "hermes returned error or empty output",
                    "error_code": "HERMES_ERROR_LEAK",
                    "recoverable": True,
                    "latency_ms": elapsed_ms,
                }

            self._last_success_at = time.time()
            self._last_error = ""
            return {
                "success": True,
                "output": output[:_MAX_OUTPUT_CHARS],
                "latency_ms": elapsed_ms,
                "provider": "hermes",
                "char_count": len(output),
                "estimated_tokens": len(output) // 4,
            }
        except subprocess.TimeoutExpired:
            with self._process_lock:
                if self._active_process and self._active_process.poll() is None:
                    self._active_process.kill()
                self._active_process = None
            elapsed_ms = int((time.monotonic() - start) * 1000)
            self._last_error = f"timeout after {timeout}s"
            return {
                "success": False,
                "error": f"hermes timed out after {timeout}s",
                "error_code": "HERMES_TIMEOUT",
                "recoverable": True,
                "latency_ms": elapsed_ms,
            }
        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            self._last_error = str(exc)
            return {
                "success": False,
                "error": f"{type(exc).__name__}: {exc}",
                "error_code": "HERMES_INTERNAL_ERROR",
                "recoverable": True,
                "latency_ms": elapsed_ms,
            }

    def _health(self, params: dict[str, Any]) -> dict[str, Any]:
        result = self._generate({"prompt": "Respond with exactly: HERMES_OK", "timeout": 30})
        healthy = result.get("success") and "HERMES_OK" in result.get("output", "")
        return {
            "success": True,
            "healthy": healthy,
            "available": self._available,
            "latency_ms": result.get("latency_ms", 0),
            "last_error": self._last_error if not healthy else "",
        }

    def _providers(self, params: dict[str, Any]) -> dict[str, Any]:
        try:
            result = subprocess.run(
                ["hermes", "config", "show"],
                capture_output=True,
                text=True,
                timeout=10,
                **no_window_kwargs(),
            )
            if result.returncode != 0:
                return {"success": True, "providers": [{"name": "unknown"}]}

            lines = result.stdout.strip().split("\n")
            providers = []
            for line in lines:
                lower = line.lower()
                if any(sig in lower for sig in _SECRET_INDICATORS):
                    continue
                if "provider" in lower or "model" in lower:
                    providers.append(line.strip())

            return {"success": True, "providers": providers, "raw_line_count": len(lines)}
        except Exception:
            return {"success": True, "providers": [{"name": "unknown"}]}

    def _models(self, params: dict[str, Any]) -> dict[str, Any]:
        try:
            result = subprocess.run(
                ["hermes", "config", "show"],
                capture_output=True,
                text=True,
                timeout=10,
                **no_window_kwargs(),
            )
            if result.returncode != 0:
                return {"success": True, "models": ["hermes-default"]}

            stdout = result.stdout.lower()
            models = []
            for line in result.stdout.strip().split("\n"):
                if "model" in line.lower():
                    val = line.split(":", 1)[-1].strip() if ":" in line else line.strip()
                    val = _redact_secrets(val)
                    if val != "redacted":
                        models.append(val)

            return {"success": True, "models": models or ["hermes-default"]}
        except Exception:
            return {"success": True, "models": ["hermes-default"]}

    def _info(self, params: dict[str, Any]) -> dict[str, Any]:
        try:
            result = subprocess.run(
                ["hermes", "config", "get", "provider"],
                capture_output=True,
                text=True,
                timeout=10,
                **no_window_kwargs(),
            )
            provider = result.stdout.strip() if result.returncode == 0 else "unknown"
            provider = _redact_secrets(provider)
            return {"success": True, "provider": provider}
        except Exception:
            return {"success": True, "provider": "unknown"}

    def _capabilities(self, params: dict[str, Any]) -> dict[str, Any]:
        return {
            "success": True,
            "capabilities": {
                "generate": "supported",
                "chat": "supported",
                "health": "supported",
                "providers": "supported",
                "models": "supported",
                "diagnostics": "supported",
                "benchmark": "supported",
                "cancel": "supported",
                "streaming": "unsupported",
                "session_native": "unsupported",
                "session_managed": "supported",
                "vision": "unknown",
                "tool_use": "unknown",
                "code_execution": "unknown",
            },
            "notes": {
                "streaming": "Hermes CLI is synchronous; pseudo-streaming via heartbeat on VPS side",
                "session_managed": "VPS manages conversation history; prepended to each call",
                "cancel": "Best-effort process kill",
            },
        }

    def _diagnostics(self, params: dict[str, Any]) -> dict[str, Any]:
        binary_path = shutil.which("hermes") or "not found"

        version = "unknown"
        try:
            result = subprocess.run(
                ["hermes", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                **no_window_kwargs(),
            )
            if result.returncode == 0:
                version = result.stdout.strip()
        except Exception:
            pass

        config_readable = False
        try:
            result = subprocess.run(
                ["hermes", "config", "path"],
                capture_output=True,
                text=True,
                timeout=5,
                **no_window_kwargs(),
            )
            config_readable = result.returncode == 0
        except Exception:
            pass

        return {
            "success": True,
            "binary_path": binary_path,
            "version": version,
            "config_readable": config_readable,
            "available": self._available,
            "last_error": self._last_error,
            "last_success_at": self._last_success_at,
            "call_count": self._call_count,
            "platform": sys.platform,
            "python_version": sys.version.split()[0],
        }

    def _benchmark(self, params: dict[str, Any]) -> dict[str, Any]:
        tests: dict[str, dict[str, Any]] = {}

        r = self._generate({"prompt": "Respond with exactly: HERMES_OK", "timeout": 30})
        liveness_pass = r.get("success") and "HERMES_OK" in r.get("output", "")
        tests["liveness"] = {
            "pass": liveness_pass,
            "latency_ms": r.get("latency_ms", 0),
        }

        if not liveness_pass:
            for name in ("grounding", "summarization", "conversation"):
                tests[name] = {"pass": False, "reason": "skipped (liveness failed)"}
            return {
                "success": True,
                "tests": tests,
                "overall_pass": False,
            }

        r = self._generate({
            "prompt": "What is the current CPU usage percentage of the VPS server? Report the exact number.",
            "timeout": 60,
        })
        grounding_pass = True
        if r.get("success"):
            output = r.get("output", "").lower()
            has_number = any(c.isdigit() for c in r.get("output", ""))
            has_refusal = any(
                phrase in output
                for phrase in ("can't check", "cannot check", "don't have access",
                               "unable to", "no access", "i can't", "not able")
            )
            if has_number and not has_refusal:
                grounding_pass = False
        tests["grounding"] = {"pass": grounding_pass}

        test_text = (
            "The UMH system has four layers: substrate provides universal platform "
            "types, execution, and governance. Adapters connect external systems. "
            "Transports handle I/O. Projections are applications built on substrate."
        )
        r = self._generate({"prompt": f"Summarize in 2 sentences: {test_text}", "timeout": 60})
        summarization_pass = (
            r.get("success")
            and len(r.get("output", "")) > 20
            and any(w in r.get("output", "").lower() for w in ("layer", "substrate", "system"))
        )
        tests["summarization"] = {"pass": summarization_pass}

        r = self._generate({
            "prompt": "What are three things to consider when choosing a database?",
            "timeout": 90,
        })
        conversation_pass = r.get("success") and len(r.get("output", "")) > 50
        tests["conversation"] = {"pass": conversation_pass}

        overall = all(t.get("pass") for t in tests.values())
        return {
            "success": True,
            "tests": tests,
            "overall_pass": overall,
        }

    def _cancel(self, params: dict[str, Any]) -> dict[str, Any]:
        with self._process_lock:
            proc = self._active_process
            if proc is None:
                return {"success": True, "cancelled": False, "reason": "no active process"}
            try:
                proc.kill()
                self._active_process = None
                return {"success": True, "cancelled": True}
            except Exception as exc:
                return {"success": False, "cancelled": False, "error": str(exc)}
