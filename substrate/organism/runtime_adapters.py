"""Concrete RuntimeAdapter implementations for UMH runtimes.

Each adapter wraps an existing CLI or API provider into the
RuntimeAdapter protocol so the RuntimeGraph can route to it.
Adapters are thin — they delegate to the existing adapter modules
in adapters/models/ and only add the protocol surface.

UMH substrate subsystem.
"""

from __future__ import annotations
from substrate.execution.cpu_gate import gated_subprocess_run, gated_popen

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
        from substrate.sockets.intelligence_port import get_cli_query

        query_cc_sync = get_cli_query("cc_sdk")

        result = query_cc_sync(
            prompt,
            task_type=kwargs.get("task_type", "analyze"),
            agent_id=kwargs.get("agent_id", "organism"),
        )
        if result is None:
            return None
        return RuntimeResult(
            output=result.output,
            runtime_id=self.runtime_id,
            latency_ms=result.latency_ms,
            metadata={"provider": "cc_sdk", "session_id": result.session_id, "model": result.model},
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
        from substrate.sockets.intelligence_port import cli_is_available

        return cli_is_available("codex")

    def execute(self, prompt: str, **kwargs: Any) -> RuntimeResult | None:
        from substrate.sockets.intelligence_port import get_cli_query

        query_codex_sync = get_cli_query("codex")

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
        from substrate.sockets.intelligence_port import cli_is_available

        return cli_is_available("hermes")

    def execute(self, prompt: str, **kwargs: Any) -> RuntimeResult | None:
        from substrate.sockets.intelligence_port import get_cli_query

        query_hermes_sync = get_cli_query("hermes")

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
        from substrate.sockets.intelligence_port import cli_is_available

        return cli_is_available("opencode")

    def execute(self, prompt: str, **kwargs: Any) -> RuntimeResult | None:
        from substrate.sockets.intelligence_port import get_cli_query

        query_opencode_sync = get_cli_query("opencode")

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
            from substrate.sockets.intelligence_port import get_router, get_model_registry
            from substrate.contracts.agent_types import ModelProvider

            MODEL_REGISTRY = get_model_registry()

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
            result = gated_subprocess_run(
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
            result = gated_subprocess_run(
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
            result = gated_subprocess_run(
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
            result = gated_subprocess_run(
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


_NODE_CAP_TO_RUNTIME_CAP: dict[str, set[RuntimeCapability]] = {
    "shell": {RuntimeCapability.SHELL, RuntimeCapability.CODE_EXECUTE},
    "filesystem": {RuntimeCapability.FILE_OPS},
    "desktop": {RuntimeCapability.BROWSER},
    "clipboard": {RuntimeCapability.FILE_OPS},
    "gpu": {RuntimeCapability.GPU_COMPUTE},
}


class MeshNodeRuntimeAdapter:
    """Mesh-connected node — proxies execution via the HTTP relay on :8095."""

    def __init__(
        self,
        node_id: str,
        node_capabilities: list[str],
        relay_port: int = 8095,
    ) -> None:
        self._node_id = node_id
        host = os.environ.get("UMH_MESH_RELAY_HOST") or (
            "host.docker.internal" if os.path.exists("/.dockerenv") else "localhost"
        )
        self._relay_url = f"http://{host}:{relay_port}"
        caps: set[RuntimeCapability] = set()
        for cap_name in node_capabilities:
            caps.update(_NODE_CAP_TO_RUNTIME_CAP.get(cap_name, set()))
        if not caps:
            caps.add(RuntimeCapability.SHELL)
        self._capabilities = frozenset(caps)

    @property
    def runtime_id(self) -> str:
        return f"mesh:{self._node_id}"

    @property
    def runtime_class(self) -> RuntimeClass:
        return RuntimeClass.REMOTE_NODE

    @property
    def capabilities(self) -> frozenset[RuntimeCapability]:
        return self._capabilities

    def check_available(self) -> bool:
        try:
            import json
            import os as _os
            import urllib.request

            relay_secret = _os.environ.get("UMH_MESH_RELAY_SECRET", "")
            if not relay_secret:
                # /nodes now requires relay auth (fail-closed) — no secret, no read.
                return False
            req = urllib.request.Request(
                f"{self._relay_url}/nodes",
                method="GET",
                headers={"Authorization": f"Bearer {relay_secret}"},
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                nodes = json.loads(resp.read().decode())
            return any(n.get("id") == self._node_id for n in nodes)
        except Exception:
            return False

    def execute(self, prompt: str, **kwargs: Any) -> RuntimeResult | None:
        import json
        import time

        from substrate.sockets.mesh_dispatch_port import mesh_dispatch

        cap_name = kwargs.get("capability_name", "shell")
        params = kwargs.get("params", {"command": prompt})
        if isinstance(params, str):
            params = {"command": params}

        # Routes through the governed mesh dispatch port: signs a verdict and
        # authenticates to the relay. No raw ungoverned relay POST here.
        start_ms = time.monotonic_ns() // 1_000_000
        data = mesh_dispatch(
            node_id=self._node_id,
            capability=f"{cap_name}.execute",
            params=params,
            risk_class="reversible_write",
            timeout=kwargs.get("timeout", 30),
        )

        elapsed = (time.monotonic_ns() // 1_000_000) - start_ms

        if data.get("ok") or data.get("success"):
            result_data = data.get("result_data", data.get("result", {}))
            output = result_data if isinstance(result_data, str) else json.dumps(result_data)
            return RuntimeResult(
                output=output,
                runtime_id=self.runtime_id,
                latency_ms=elapsed,
                metadata={"provider": "mesh", "node_id": self._node_id},
            )
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
            result = gated_subprocess_run(
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
            result = gated_subprocess_run(
                [
                    "ssh",
                    "-o",
                    "ConnectTimeout=5",
                    f"{os.environ.get('UMH_BEAST_SSH_USER', 'user')}@{self._host}",
                    cmd,
                ],
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


class OperatorAPIAdapter:
    """Operator API — the FastAPI backend itself, always running when queried."""

    @property
    def runtime_id(self) -> str:
        return "operator_api"

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
        return True

    def execute(self, prompt: str, **kwargs: Any) -> RuntimeResult | None:
        return RuntimeResult(
            output="operator_api is the current process",
            runtime_id=self.runtime_id,
            metadata={"provider": "operator_api"},
        )


def _discover_docker_containers() -> list[DockerAdapter]:
    """Discover all running Docker containers and return an adapter per container."""
    if not shutil.which("docker"):
        return []
    import subprocess

    try:
        result = gated_subprocess_run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return []
        names = [n.strip() for n in result.stdout.strip().split("\n") if n.strip()]
        return [DockerAdapter(container_name=n) for n in names]
    except Exception as exc:
        logger.debug("docker discovery failed: %s", exc)
        return []


def _discover_tmux_sessions() -> list[TmuxAdapter]:
    """Discover all active tmux sessions and return an adapter per session."""
    if not shutil.which("tmux"):
        return []
    import subprocess

    try:
        result = gated_subprocess_run(
            ["tmux", "list-sessions", "-F", "#{session_name}"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode != 0:
            return []
        names = [n.strip() for n in result.stdout.strip().split("\n") if n.strip()]
        return [TmuxAdapter(session_name=n) for n in names]
    except Exception as exc:
        logger.debug("tmux discovery failed: %s", exc)
        return []


def build_default_graph() -> "RuntimeGraph":
    """Construct a RuntimeGraph pre-loaded with all known runtimes.

    Discovers real environment state: all Docker containers, all tmux
    sessions, AI CLI tools, model APIs, and remote nodes.
    """
    from substrate.organism.runtime_graph import (
        CostProfile,
        RuntimeGraph,
    )

    graph = RuntimeGraph()

    # ── AI CLI runtimes (VPS-local) ──
    cc = CCSDKAdapter()
    graph.register(
        cc.runtime_id,
        cc.runtime_class,
        cc.capabilities,
        cost=CostProfile(is_subscription=True),
        adapter=cc,
        metadata={"device_id": "vps"},
    )

    codex = CodexAdapter()
    graph.register(
        codex.runtime_id,
        codex.runtime_class,
        codex.capabilities,
        cost=CostProfile(is_subscription=True),
        adapter=codex,
        metadata={"device_id": "vps"},
    )

    hermes = HermesAdapter()
    graph.register(
        hermes.runtime_id,
        hermes.runtime_class,
        hermes.capabilities,
        cost=CostProfile(cost_per_1k_input=0.001, cost_per_1k_output=0.002),
        adapter=hermes,
        metadata={"device_id": "vps"},
    )

    opencode = OpenCodeAdapter()
    graph.register(
        opencode.runtime_id,
        opencode.runtime_class,
        opencode.capabilities,
        cost=CostProfile(cost_per_1k_input=0.003, cost_per_1k_output=0.015),
        adapter=opencode,
        metadata={"device_id": "vps"},
    )

    # ── AI API runtimes (VPS-local) ──
    gemini = GeminiAdapter()
    graph.register(
        gemini.runtime_id,
        gemini.runtime_class,
        gemini.capabilities,
        cost=CostProfile(cost_per_1k_input=0.0005, cost_per_1k_output=0.001),
        adapter=gemini,
        metadata={"device_id": "vps"},
    )

    # ── Local model runtimes (VPS-local) ──
    ollama = OllamaAdapter()
    graph.register(
        ollama.runtime_id,
        ollama.runtime_class,
        ollama.capabilities,
        cost=CostProfile(is_subscription=False, cost_per_1k_input=0.0),
        adapter=ollama,
        metadata={"device_id": "vps"},
    )

    # ── Remote nodes (Beast via SSH fallback) ──
    beast = BeastNodeAdapter()
    graph.register(
        beast.runtime_id,
        beast.runtime_class,
        beast.capabilities,
        cost=CostProfile(is_subscription=False, cost_per_1k_input=0.0),
        adapter=beast,
        metadata={"device_id": "windows_beast"},
    )

    # ── Operator API (self, VPS-local) ──
    op = OperatorAPIAdapter()
    graph.register(
        op.runtime_id,
        op.runtime_class,
        op.capabilities,
        cost=CostProfile(),
        adapter=op,
        metadata={"device_id": "vps"},
    )

    # ── Dynamic discovery: Docker containers ──
    for docker_adapter in _discover_docker_containers():
        if graph.get(docker_adapter.runtime_id) is None:
            graph.register(
                docker_adapter.runtime_id,
                docker_adapter.runtime_class,
                docker_adapter.capabilities,
                cost=CostProfile(),
                adapter=docker_adapter,
            )

    # ── Dynamic discovery: tmux sessions ──
    for tmux_adapter in _discover_tmux_sessions():
        if graph.get(tmux_adapter.runtime_id) is None:
            graph.register(
                tmux_adapter.runtime_id,
                tmux_adapter.runtime_class,
                tmux_adapter.capabilities,
                cost=CostProfile(),
                adapter=tmux_adapter,
            )

    logger.info(
        "built runtime graph: %d runtimes (%d docker, %d tmux)",
        graph.node_count,
        sum(1 for n in graph.all_nodes() if n.runtime_id.startswith("docker:")),
        sum(1 for n in graph.all_nodes() if n.runtime_id.startswith("tmux:")),
    )

    return graph
