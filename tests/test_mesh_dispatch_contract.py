"""C40A Phase 2 — Mesh Dispatch Contract Tests.

Verifies payload shape at every hop in the mesh dispatch chain.
Tests both command (string) and argv (list) paths.
"""

from __future__ import annotations

import json
import sys

sys.path.insert(0, "/opt/OS")



class TestSerializationChain:
    """Verify JSON serialization preserves params at every boundary."""

    def _simulate_chain(self, params: dict) -> dict:
        """Simulate the full serialization chain and return what the adapter sees."""
        # Step 1: HTTP body construction (browser_evidence_collector or _mesh_dispatch)
        http_body = {
            "node_id": "windows-desktop",
            "capability": "shell",
            "params": params,
            "timeout": 30,
        }

        # Step 2: JSON encode/decode (HTTP transport)
        encoded = json.dumps(http_body)
        decoded = json.loads(encoded)

        # Step 3: Relay extracts params (server.py:979)
        relay_params = decoded.get("params", {})
        relay_capability = decoded.get("capability", "")

        # Step 4: Relay wraps in JSON-RPC (server.py:1000-1012)
        rpc_msg = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "capability.execute",
                "params": {
                    "request_id": "test-id",
                    "capability_name": relay_capability,
                    "params": relay_params,
                    "timeout_seconds": 30,
                },
                "id": "test-id",
            }
        )
        rpc_decoded = json.loads(rpc_msg)

        # Step 5: Client extracts (client.py:454-457)
        msg_params = rpc_decoded.get("params", {})
        cap_name = msg_params.get("capability_name", "")
        cap_params = msg_params.get("params", {})

        return {
            "cap_name": cap_name,
            "cap_params": cap_params,
            "has_command": bool(cap_params.get("command", "")),
            "has_argv": bool(cap_params.get("argv") and isinstance(cap_params.get("argv"), list)),
        }

    def test_command_path_preserves_command(self):
        result = self._simulate_chain({"command": "echo test", "timeout": 30})
        assert result["has_command"]
        assert result["cap_params"]["command"] == "echo test"

    def test_argv_path_preserves_argv(self):
        result = self._simulate_chain({"argv": ["echo", "test"], "cwd": "/tmp"})
        assert result["has_argv"]
        assert result["cap_params"]["argv"] == ["echo", "test"]

    def test_complex_command_preserves_quotes(self):
        cmd = "python3 -c \"import json; print(json.dumps({'ok': True}))\""
        result = self._simulate_chain({"command": cmd, "timeout": 60})
        assert result["has_command"]
        assert result["cap_params"]["command"] == cmd

    def test_empty_params_fails_adapter_check(self):
        result = self._simulate_chain({})
        assert not result["has_command"]
        assert not result["has_argv"]

    def test_capability_name_is_shell(self):
        result = self._simulate_chain({"command": "echo test"})
        assert result["cap_name"] == "shell"

    def test_nested_json_in_command(self):
        cmd = 'echo \'{"key": "value"}\''
        result = self._simulate_chain({"command": cmd, "timeout": 30})
        assert result["has_command"]
        assert result["cap_params"]["command"] == cmd


class TestShellAdapterContract:
    """Verify ShellAdapter accepts both command and argv."""

    def setup_method(self):
        from nodes.windows.umh_node.adapters.shell import ShellAdapter

        self.adapter = ShellAdapter()

    def test_command_path_succeeds(self):
        result = self.adapter.execute("shell", {"command": "echo test_contract", "timeout": 5})
        assert result["success"]
        assert "test_contract" in result["stdout"]

    def test_argv_path_succeeds(self):
        result = self.adapter.execute("shell", {"argv": ["echo", "test_argv"], "timeout": 5})
        assert result["success"]
        assert "test_argv" in result["stdout"]

    def test_empty_params_returns_error(self):
        result = self.adapter.execute("shell", {})
        assert not result["success"]
        assert "no command or argv provided" in result["error"]

    def test_timeout_only_returns_error(self):
        result = self.adapter.execute("shell", {"timeout": 5})
        assert not result["success"]
        assert "no command or argv provided" in result["error"]

    def test_command_with_cwd(self):
        result = self.adapter.execute(
            "shell", {"command": "echo cwd_test", "timeout": 5, "cwd": "/tmp"}
        )
        assert result["success"]

    def test_timeout_respected(self):
        if sys.platform == "win32":
            cmd = "ping -n 10 127.0.0.1"
        else:
            cmd = "sleep 10"
        result = self.adapter.execute("shell", {"command": cmd, "timeout": 1})
        assert not result["success"]
        assert "timed out" in result.get("error", "")


class TestGovernanceCapabilityName:
    """Verify governance handles dotted capability names correctly."""

    def test_shell_passes_governance(self):
        from nodes.windows.umh_node.config import CapabilityConfig
        from nodes.windows.umh_node.governance import validate_request

        config = CapabilityConfig()
        allowed, reason = validate_request(
            "shell", {"command": "echo test"}, "REVERSIBLE_WRITE", config
        )
        assert allowed

    def test_shell_execute_passes_governance(self):
        from nodes.windows.umh_node.config import CapabilityConfig
        from nodes.windows.umh_node.governance import validate_request

        config = CapabilityConfig()
        allowed, reason = validate_request(
            "shell.execute", {"command": "echo test"}, "REVERSIBLE_WRITE", config
        )
        assert allowed

    def test_no_config_denies(self):
        from nodes.windows.umh_node.governance import validate_request

        allowed, reason = validate_request(
            "shell", {"command": "echo test"}, "REVERSIBLE_WRITE", None
        )
        assert not allowed

    def test_disabled_capability_denies(self):
        from nodes.windows.umh_node.config import CapabilityConfig
        from nodes.windows.umh_node.governance import validate_request

        config = CapabilityConfig(enabled=False)
        allowed, reason = validate_request(
            "shell", {"command": "echo test"}, "REVERSIBLE_WRITE", config
        )
        assert not allowed

    # ── Wave 0 Amendment G: full-path allowed_commands regression ──────────
    # C40A adjudication: the retired TestRuntimeBoundaryAudit governance test
    # is replaced by these live full-path assertions. The latent hazard was a
    # DIRECT call to validate_request("shell.execute", ...) skipping the node
    # client's adapter-key normalization — the exact-match check then let
    # allowed_commands go unenforced. The hardened validate_request now binds
    # base-adapter policy to the dotted form and denies unknown operations.

    def test_shell_execute_inherits_allowed_commands_restriction(self):
        """A disallowed command carried under shell.execute must be DENIED —
        the dotted operation never loosens the base-adapter restriction."""
        from nodes.windows.umh_node.config import CapabilityConfig
        from nodes.windows.umh_node.governance import validate_request

        config = CapabilityConfig(allowed_commands=["echo", "dir"])
        allowed, reason = validate_request(
            "shell.execute", {"command": "del C:\\important"}, "REVERSIBLE_WRITE", config
        )
        assert not allowed
        assert "allowed_commands" in reason
        # and an allowed command under the same dotted name passes
        allowed, _ = validate_request(
            "shell.execute", {"command": "echo hi"}, "REVERSIBLE_WRITE", config
        )
        assert allowed

    def test_unknown_dotted_operation_denied_never_stripped(self):
        """Only the canonical .execute operation is recognized; arbitrary
        suffixes are denied, never silently normalized."""
        from nodes.windows.umh_node.config import CapabilityConfig
        from nodes.windows.umh_node.governance import validate_request

        config = CapabilityConfig(allowed_commands=["echo"])
        for bogus in ("shell.rm", "shell.execute.now", "shell.bypass"):
            allowed, reason = validate_request(
                bogus, {"command": "echo hi"}, "REVERSIBLE_WRITE", config
            )
            assert not allowed, bogus
            assert "unknown capability operation" in reason

    def test_full_path_adapter_emitted_name_through_client_policy(self):
        """Full-path contract: the exact capability string the VPS runtime
        adapter emits ("<adapter>.execute"), pushed through the node client's
        adapter-key derivation and into the hardened validate_request, still
        enforces allowed_commands. Verdict binding stays on the dotted name."""
        import inspect

        from nodes.windows.umh_node.config import CapabilityConfig
        from nodes.windows.umh_node.governance import validate_request
        from substrate.organism.runtime_adapters import MeshNodeRuntimeAdapter

        # 1. the adapter emits the dotted form — the contract this test pins
        src = inspect.getsource(MeshNodeRuntimeAdapter)
        assert 'f"{cap_name}.execute"' in src, (
            "MeshNodeRuntimeAdapter no longer emits '<adapter>.execute' — "
            "update the capability-name contract and this test together"
        )
        cap_name = "shell.execute"

        # 2. node client derivation (nodes/windows/umh_node/client.py) — the
        #    adapter key is for config/adapter lookup only
        adapter_key = cap_name.split(".")[0] if "." in cap_name else cap_name
        assert adapter_key == "shell"
        capabilities = {"shell": CapabilityConfig(allowed_commands=["echo"])}
        cap_config = capabilities.get(adapter_key)

        # 3. policy receives the ORIGINAL dotted name (client passes cap_name)
        allowed, reason = validate_request(
            cap_name, {"command": "powershell -c evil"}, "REVERSIBLE_WRITE", cap_config
        )
        assert not allowed
        assert "allowed_commands" in reason
        allowed, _ = validate_request(
            cap_name, {"command": "echo ok"}, "REVERSIBLE_WRITE", cap_config
        )
        assert allowed

    def test_client_passes_original_dotted_name_to_policy(self):
        """The node client must hand validate_request the original dotted
        capability, not the pre-normalized adapter key — otherwise the
        unknown-operation deny can never fire."""
        import inspect

        from nodes.windows.umh_node import client as node_client

        src = inspect.getsource(node_client)
        assert "validate_request(cap_name, cap_params, risk_class, cap_config)" in src, (
            "node client no longer passes the original capability name into "
            "validate_request — unknown-operation denial is dead code"
        )


class TestRelayPassthrough:
    """Verify relay HTTP handler extracts and forwards correctly."""

    def test_params_extraction(self):
        body = {
            "node_id": "windows-desktop",
            "capability": "shell",
            "params": {"command": "echo test", "timeout": 30},
            "timeout": 30,
        }
        params = body.get("params", {})
        assert "command" in params
        assert params["command"] == "echo test"

    def test_jsonrpc_wrapping(self):
        params = {"command": "echo test", "timeout": 30}
        capability = "shell"
        rpc = {
            "jsonrpc": "2.0",
            "method": "capability.execute",
            "params": {
                "request_id": "test",
                "capability_name": capability,
                "params": params,
                "timeout_seconds": 30,
            },
            "id": "test",
        }
        encoded = json.dumps(rpc)
        decoded = json.loads(encoded)
        inner = decoded["params"]["params"]
        assert inner["command"] == "echo test"

    def test_double_serialization_preserves(self):
        """Ensure double JSON encode/decode doesn't mangle params."""
        original_params = {"command": 'python3 -c "print(1)"', "timeout": 30}
        once = json.loads(json.dumps(original_params))
        twice = json.loads(json.dumps(once))
        assert twice == original_params
