"""Concrete RuntimeAdapter implementations for UMH runtimes.

Each adapter wraps an existing CLI or API provider into the
RuntimeAdapter protocol so the RuntimeGraph can route to it.
Adapters are thin — they delegate to the existing adapter modules
in adapters/models/ and only add the protocol surface.

UMH substrate subsystem.
"""

from __future__ import annotations

import logging
import os
import shutil
from typing import Any

from substrate.organism.runtime_graph import (
    RuntimeAdapter,
    RuntimeCapability,
    RuntimeClass,
    RuntimeResult,
)

logger = logging.getLogger(__name__)


class CCSDKAdapter:
    """Claude Code SDK — Opus via Max subscription, no API cost."""

    @property
    def runtime_id(self) -> str:
        return "cc_sdk"

    @property
    def runtime_class(self) -> RuntimeClass:
        return RuntimeClass.AI_CLI

    @property
    def capabilities(self) -> frozenset[RuntimeCapability]:
        return frozenset(
            {
                RuntimeCapability.CODE_WRITE,
                RuntimeCapability.CODE_REVIEW,
                RuntimeCapability.CODE_EXECUTE,
                RuntimeCapability.REASON,
                RuntimeCapability.AUTONOMOUS,
            }
        )

    def check_available(self) -> bool:
        return shutil.which("claude") is not None

    def execute(self, prompt: str, **kwargs: Any) -> RuntimeResult | None:
        from adapters.models.cc_sdk import query_cc_sync

        result = query_cc_sync(
            prompt,
            task_type=kwargs.get("task_type", "analyze"),
            agent_id=kwargs.get("agent_id", "organism"),
        )
        if result is None:
            return None
        return RuntimeResult(
            output=result,
            runtime_id=self.runtime_id,
            latency_ms=0,
            metadata={"provider": "cc_sdk"},
        )


class CodexAdapter:
    """Codex CLI — gpt-5.5 via ChatGPT subscription."""

    @property
    def runtime_id(self) -> str:
        return "codex"

    @property
    def runtime_class(self) -> RuntimeClass:
        return RuntimeClass.AI_CLI

    @property
    def capabilities(self) -> frozenset[RuntimeCapability]:
        return frozenset(
            {
                RuntimeCapability.CODE_WRITE,
                RuntimeCapability.CODE_REVIEW,
                RuntimeCapability.CODE_EXECUTE,
                RuntimeCapability.REASON,
            }
        )

    def check_available(self) -> bool:
        from adapters.models.codex_cli import is_available

        return is_available()

    def execute(self, prompt: str, **kwargs: Any) -> RuntimeResult | None:
        from adapters.models.codex_cli import query_codex_sync

        result = query_codex_sync(
            prompt,
            model=kwargs.get("model"),
            sandbox=kwargs.get("sandbox", "read-only"),
            cwd=kwargs.get("cwd"),
            timeout=kwargs.get("timeout"),
        )
        if result is None:
            return None
        return RuntimeResult(
            output=result.output,
            runtime_id=self.runtime_id,
            latency_ms=result.latency_ms,
            metadata={
                "provider": "codex",
                "thread_id": result.thread_id,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
            },
        )


class HermesAdapter:
    """Hermes CLI — model-agnostic agent via OpenRouter/OpenAI/Ollama."""

    @property
    def runtime_id(self) -> str:
        return "hermes"

    @property
    def runtime_class(self) -> RuntimeClass:
        return RuntimeClass.AI_CLI

    @property
    def capabilities(self) -> frozenset[RuntimeCapability]:
        return frozenset(
            {
                RuntimeCapability.CODE_WRITE,
                RuntimeCapability.REASON,
                RuntimeCapability.RESEARCH,
                RuntimeCapability.AUTONOMOUS,
            }
        )

    def check_available(self) -> bool:
        from adapters.models.hermes_cli import is_available

        return is_available()

    def execute(self, prompt: str, **kwargs: Any) -> RuntimeResult | None:
        from adapters.models.hermes_cli import query_hermes_sync

        result = query_hermes_sync(
            prompt,
            cwd=kwargs.get("cwd"),
            timeout=kwargs.get("timeout"),
        )
        if result is None:
            return None
        return RuntimeResult(
            output=result.output,
            runtime_id=self.runtime_id,
            latency_ms=result.latency_ms,
            metadata={"provider": "hermes"},
        )


class OpenCodeAdapter:
    """OpenCode CLI — 75+ LLM provider support."""

    @property
    def runtime_id(self) -> str:
        return "opencode"

    @property
    def runtime_class(self) -> RuntimeClass:
        return RuntimeClass.AI_CLI

    @property
    def capabilities(self) -> frozenset[RuntimeCapability]:
        return frozenset(
            {
                RuntimeCapability.CODE_WRITE,
                RuntimeCapability.REASON,
                RuntimeCapability.RESEARCH,
            }
        )

    def check_available(self) -> bool:
        from adapters.models.opencode_cli import is_available

        return is_available()

    def execute(self, prompt: str, **kwargs: Any) -> RuntimeResult | None:
        from adapters.models.opencode_cli import query_opencode_sync

        result = query_opencode_sync(
            prompt,
            model=kwargs.get("model"),
            cwd=kwargs.get("cwd"),
            timeout=kwargs.get("timeout"),
        )
        if result is None:
            return None
        return RuntimeResult(
            output=result.output,
            runtime_id=self.runtime_id,
            latency_ms=result.latency_ms,
            metadata={"provider": "opencode"},
        )


class GeminiAdapter:
    """Gemini API — Google's models via Python SDK."""

    @property
    def runtime_id(self) -> str:
        return "gemini"

    @property
    def runtime_class(self) -> RuntimeClass:
        return RuntimeClass.AI_API

    @property
    def capabilities(self) -> frozenset[RuntimeCapability]:
        return frozenset(
            {
                RuntimeCapability.REASON,
                RuntimeCapability.FAST_RESPONSE,
                RuntimeCapability.RESEARCH,
            }
        )

    def check_available(self) -> bool:
        return bool(os.environ.get("GEMINI_API_KEY"))

    def execute(self, prompt: str, **kwargs: Any) -> RuntimeResult | None:
        try:
            from adapters.models.model_router import (
                get_router,
                ModelProvider,
                MODEL_REGISTRY,
            )

            router = get_router()
            configs = [
                c
                for c in MODEL_REGISTRY.values()
                if c.provider == ModelProvider.GEMINI and c.available
            ]
            if not configs:
                return None
            output = router.call(
                configs[0],
                prompt,
                kwargs.get("system", ""),
                kwargs.get("max_tokens", 2000),
            )
            if not output:
                return None
            return RuntimeResult(
                output=output,
                runtime_id=self.runtime_id,
                metadata={"provider": "gemini"},
            )
        except Exception as e:
            logger.warning("gemini adapter failed: %s", e)
            return None


class OllamaAdapter:
    """Ollama — local model inference on VPS or Beast."""

    def __init__(self, host: str = "http://localhost:11434") -> None:
        self._host = host

    @property
    def runtime_id(self) -> str:
        return "ollama"

    @property
    def runtime_class(self) -> RuntimeClass:
        return RuntimeClass.LOCAL_MODEL

    @property
    def capabilities(self) -> frozenset[RuntimeCapability]:
        return frozenset(
            {
                RuntimeCapability.REASON,
                RuntimeCapability.FAST_RESPONSE,
            }
        )

    def check_available(self) -> bool:
        try:
            import urllib.request

            req = urllib.request.Request(f"{self._host}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status == 200
        except Exception:
            return False

    def execute(self, prompt: str, **kwargs: Any) -> RuntimeResult | None:
        try:
            import json
            import time
            import urllib.request

            model = kwargs.get("model", "gemma3:4b")
            payload = json.dumps(
                {
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                }
            ).encode()

            req = urllib.request.Request(
                f"{self._host}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            start_ms = time.monotonic_ns() // 1_000_000
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode())

            elapsed = (time.monotonic_ns() // 1_000_000) - start_ms
            output = data.get("response", "")
            if not output:
                return None

            return RuntimeResult(
                output=output,
                runtime_id=self.runtime_id,
                latency_ms=elapsed,
                metadata={
                    "provider": "ollama",
                    "model": model,
                    "eval_count": data.get("eval_count", 0),
                },
            )
        except Exception as e:
            logger.warning("ollama adapter failed: %s", e)
            return None


class DockerAdapter:
    """Docker container execution — runs commands in named containers."""

    def __init__(self, container_name: str = "os-discord") -> None:
        self._container = container_name

    @property
    def runtime_id(self) -> str:
        return f"docker:{self._container}"

    @property
    def runtime_class(self) -> RuntimeClass:
        return RuntimeClass.CONTAINER

    @property
    def capabilities(self) -> frozenset[RuntimeCapability]:
        return frozenset(
            {
                RuntimeCapability.SHELL,
                RuntimeCapability.CODE_EXECUTE,
                RuntimeCapability.FILE_OPS,
            }
        )

    def check_available(self) -> bool:
        if not shutil.which("docker"):
            return False
        import subprocess

        try:
            result = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Running}}", self._container],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.stdout.strip() == "true"
        except Exception:
            return False

    def execute(self, prompt: str, **kwargs: Any) -> RuntimeResult | None:
        import subprocess
        import time

        cmd = kwargs.get("command", prompt)
        start_ms = time.monotonic_ns() // 1_000_000
        try:
            result = subprocess.run(
                ["docker", "exec", self._container, "bash", "-c", cmd],
                capture_output=True,
                text=True,
                timeout=kwargs.get("timeout", 60),
            )
            elapsed = (time.monotonic_ns() // 1_000_000) - start_ms

            output = result.stdout.strip()
            if result.returncode != 0 and not output:
                output = result.stderr.strip()

            return RuntimeResult(
                output=output or f"exit code: {result.returncode}",
                runtime_id=self.runtime_id,
                latency_ms=elapsed,
                metadata={
                    "container": self._container,
                    "exit_code": result.returncode,
                },
            )
        except subprocess.TimeoutExpired:
            return None
        except Exception as e:
            logger.warning("docker adapter failed: %s", e)
            return None


class TmuxAdapter:
    """Tmux session execution — runs commands in named tmux sessions."""

    def __init__(self, session_name: str = "work") -> None:
        self._session = session_name

    @property
    def runtime_id(self) -> str:
        return f"tmux:{self._session}"

    @property
    def runtime_class(self) -> RuntimeClass:
        return RuntimeClass.PROCESS

    @property
    def capabilities(self) -> frozenset[RuntimeCapability]:
        return frozenset(
            {
                RuntimeCapability.SHELL,
                RuntimeCapability.CODE_EXECUTE,
                RuntimeCapability.FILE_OPS,
            }
        )

    def check_available(self) -> bool:
        if not shutil.which("tmux"):
            return False
        import subprocess

        try:
            result = subprocess.run(
                ["tmux", "has-session", "-t", self._session],
                capture_output=True,
                timeout=3,
            )
            return result.returncode == 0
        except Exception:
            return False

    def execute(self, prompt: str, **kwargs: Any) -> RuntimeResult | None:
        import subprocess
        import time

        cmd = kwargs.get("command", prompt)
        start_ms = time.monotonic_ns() // 1_000_000
        try:
            result = subprocess.run(
                ["tmux", "send-keys", "-t", self._session, cmd, "Enter"],
                capture_output=True,
                text=True,
                timeout=kwargs.get("timeout", 30),
            )
            elapsed = (time.monotonic_ns() // 1_000_000) - start_ms

            return RuntimeResult(
                output=f"sent to tmux:{self._session}",
                runtime_id=self.runtime_id,
                latency_ms=elapsed,
                metadata={
                    "session": self._session,
                    "exit_code": result.returncode,
                },
            )
        except Exception as e:
            logger.warning("tmux adapter failed: %s", e)
            return None


class BeastNodeAdapter:
    """Beast GPU node — remote execution via Tailscale SSH."""

    def __init__(self, host: str = "") -> None:
        self._host = host or os.environ.get("EOS_LOCAL_BRIDGE_IP", "")

    @property
    def runtime_id(self) -> str:
        return "beast_gpu"

    @property
    def runtime_class(self) -> RuntimeClass:
        return RuntimeClass.REMOTE_NODE

    @property
    def capabilities(self) -> frozenset[RuntimeCapability]:
        return frozenset(
            {
                RuntimeCapability.GPU_COMPUTE,
                RuntimeCapability.SHELL,
                RuntimeCapability.CODE_EXECUTE,
                RuntimeCapability.FILE_OPS,
                RuntimeCapability.BROWSER,
            }
        )

    def check_available(self) -> bool:
        import subprocess

        try:
            result = subprocess.run(
                [
                    "ssh",
                    "-o",
                    "ConnectTimeout=3",
                    "-o",
                    "BatchMode=yes",
                    f"{os.environ.get('UMH_BEAST_SSH_USER', 'user')}@{self._host}",
                    "echo ok",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.stdout.strip() == "ok"
        except Exception:
            return False

    def execute(self, prompt: str, **kwargs: Any) -> RuntimeResult | None:
        import subprocess
        import time

        cmd = kwargs.get("command", prompt)
        start_ms = time.monotonic_ns() // 1_000_000
        try:
            result = subprocess.run(
                ["ssh", "-o", "ConnectTimeout=5", f"{os.environ.get('UMH_BEAST_SSH_USER', 'user')}@{self._host}", cmd],
                capture_output=True,
                text=True,
                timeout=kwargs.get("timeout", 120),
            )
            elapsed = (time.monotonic_ns() // 1_000_000) - start_ms

            output = result.stdout.strip()
            if result.returncode != 0 and not output:
                output = result.stderr.strip()

            return RuntimeResult(
                output=output or f"exit code: {result.returncode}",
                runtime_id=self.runtime_id,
                latency_ms=elapsed,
                metadata={
                    "host": self._host,
                    "exit_code": result.returncode,
                },
            )
        except subprocess.TimeoutExpired:
            return None
        except Exception as e:
            logger.warning("beast node adapter failed: %s", e)
            return None


def build_default_graph() -> "RuntimeGraph":
    """Construct a RuntimeGraph pre-loaded with all known runtimes."""
    from substrate.organism.runtime_graph import (
        CostProfile,
        RuntimeGraph,
    )

    graph = RuntimeGraph()

    cc = CCSDKAdapter()
    graph.register(
        cc.runtime_id,
        cc.runtime_class,
        cc.capabilities,
        cost=CostProfile(is_subscription=True),
        adapter=cc,
    )

    codex = CodexAdapter()
    graph.register(
        codex.runtime_id,
        codex.runtime_class,
        codex.capabilities,
        cost=CostProfile(is_subscription=True),
        adapter=codex,
    )

    hermes = HermesAdapter()
    graph.register(
        hermes.runtime_id,
        hermes.runtime_class,
        hermes.capabilities,
        cost=CostProfile(cost_per_1k_input=0.001, cost_per_1k_output=0.002),
        adapter=hermes,
    )

    opencode = OpenCodeAdapter()
    graph.register(
        opencode.runtime_id,
        opencode.runtime_class,
        opencode.capabilities,
        cost=CostProfile(cost_per_1k_input=0.003, cost_per_1k_output=0.015),
        adapter=opencode,
    )

    gemini = GeminiAdapter()
    graph.register(
        gemini.runtime_id,
        gemini.runtime_class,
        gemini.capabilities,
        cost=CostProfile(cost_per_1k_input=0.0005, cost_per_1k_output=0.001),
        adapter=gemini,
    )

    ollama = OllamaAdapter()
    graph.register(
        ollama.runtime_id,
        ollama.runtime_class,
        ollama.capabilities,
        cost=CostProfile(is_subscription=False, cost_per_1k_input=0.0),
        adapter=ollama,
    )

    beast = BeastNodeAdapter()
    graph.register(
        beast.runtime_id,
        beast.runtime_class,
        beast.capabilities,
        cost=CostProfile(is_subscription=False, cost_per_1k_input=0.0),
        adapter=beast,
    )

    return graph
