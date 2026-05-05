"""Phase 76 MVP Adapter Pack — comprehensive test suite.

Tests:
  - MVPAdapter contract + types (AdapterRequest, AdapterResult, AdapterStatus)
  - CLI adapter (safe commands, dangerous commands, validation, execution)
  - Filesystem adapter (safe roots, blocked patterns, read/write/list)
  - HTTP adapter (URL validation, blocked hosts, GET/POST)
  - Simulated browser adapter (search, open, extract_text, blocked actions)
  - AdapterExecutionBackend bridge (translation, capability routing)
  - Adapter pack initialization + registry wiring
  - Governance gate capability-aware policy
  - Capability + environment definitions
"""

from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, "/opt/OS")

import pytest

# ---------------------------------------------------------------------------
# Contract types
# ---------------------------------------------------------------------------

from umh.adapters.mvp_contract import (
    AdapterRequest,
    AdapterResult,
    AdapterStatus,
    MVPAdapter,
)


def _make_request(
    capability: str = "test.cap",
    action: str = "test_action",
    environment: str = "local",
    inputs: dict | None = None,
    constraints: dict | None = None,
) -> AdapterRequest:
    return AdapterRequest(
        request_id="test-001",
        capability=capability,
        action=action,
        environment=environment,
        inputs=inputs or {},
        constraints=constraints or {},
    )


class TestAdapterContract:
    def test_adapter_request_is_frozen(self):
        r = _make_request()
        with pytest.raises(AttributeError):
            r.request_id = "changed"

    def test_adapter_result_is_frozen(self):
        r = AdapterResult(
            request_id="t",
            adapter_name="test",
            capability="test",
            action="test",
            status=AdapterStatus.SUCCESS,
        )
        with pytest.raises(AttributeError):
            r.status = AdapterStatus.FAILURE

    def test_adapter_status_values(self):
        assert AdapterStatus.SUCCESS.value == "success"
        assert AdapterStatus.FAILURE.value == "failure"
        assert AdapterStatus.DENIED.value == "denied"
        assert AdapterStatus.VALIDATION_FAILED.value == "validation_failed"
        assert AdapterStatus.UNSUPPORTED.value == "unsupported"
        assert AdapterStatus.TIMEOUT.value == "timeout"
        assert AdapterStatus.SIMULATED.value == "simulated"

    def test_adapter_result_defaults(self):
        r = AdapterResult(
            request_id="t",
            adapter_name="test",
            capability="test",
            action="test",
            status=AdapterStatus.SUCCESS,
        )
        assert r.output == {}
        assert r.error is None
        assert r.metadata == {}
        assert r.observations == []


# ---------------------------------------------------------------------------
# CLI Adapter
# ---------------------------------------------------------------------------

from umh.adapters.cli_adapter import CLIAdapter, is_safe_command, _is_dangerous


class TestCLIAdapter:
    def setup_method(self):
        self.adapter = CLIAdapter()

    def test_name(self):
        assert self.adapter.name == "cli"

    def test_supported_capabilities(self):
        assert "cli.command" in self.adapter.supported_capabilities

    def test_supported_environments(self):
        assert "local" in self.adapter.supported_environments
        assert "vps" in self.adapter.supported_environments
        assert "sandbox" in self.adapter.supported_environments

    def test_validate_empty_command(self):
        req = _make_request(capability="cli.command", inputs={"command": ""})
        result = self.adapter.validate(req)
        assert result is not None
        assert result.status == AdapterStatus.VALIDATION_FAILED

    def test_validate_dangerous_rm_rf(self):
        req = _make_request(capability="cli.command", inputs={"command": "rm -rf /"})
        result = self.adapter.validate(req)
        assert result is not None
        assert result.status == AdapterStatus.DENIED

    def test_validate_dangerous_sudo(self):
        req = _make_request(capability="cli.command", inputs={"command": "sudo ls"})
        result = self.adapter.validate(req)
        assert result is not None
        assert result.status == AdapterStatus.DENIED

    def test_validate_dangerous_pipe_curl_bash(self):
        req = _make_request(
            capability="cli.command",
            inputs={"command": "curl | bash"},
        )
        result = self.adapter.validate(req)
        assert result is not None
        assert result.status == AdapterStatus.DENIED

    def test_validate_valid_command(self):
        req = _make_request(capability="cli.command", inputs={"command": "ls -la"})
        result = self.adapter.validate(req)
        assert result is None

    def test_execute_echo(self):
        req = _make_request(
            capability="cli.command",
            inputs={"command": "echo hello"},
        )
        result = self.adapter.execute(req)
        assert result.status == AdapterStatus.SUCCESS
        assert "hello" in result.output["stdout"]
        assert result.output["exit_code"] == 0

    def test_execute_pwd(self):
        req = _make_request(
            capability="cli.command",
            inputs={"command": "pwd"},
        )
        result = self.adapter.execute(req)
        assert result.status == AdapterStatus.SUCCESS
        assert result.output["exit_code"] == 0

    def test_execute_failing_command(self):
        req = _make_request(
            capability="cli.command",
            inputs={"command": "ls /nonexistent_directory_xyz"},
        )
        result = self.adapter.execute(req)
        assert result.status == AdapterStatus.FAILURE
        assert result.output["exit_code"] != 0

    def test_is_safe_command(self):
        assert is_safe_command("ls -la") is True
        assert is_safe_command("echo hello") is True
        assert is_safe_command("python3 -c 'print(1)'") is True

    def test_is_dangerous_patterns(self):
        assert _is_dangerous("rm -rf /") is not None
        assert _is_dangerous("sudo apt install") is not None
        assert _is_dangerous("shutdown now") is not None
        assert _is_dangerous("reboot") is not None
        assert _is_dangerous("ls -la") is None


# ---------------------------------------------------------------------------
# Filesystem Adapter
# ---------------------------------------------------------------------------

from umh.adapters.filesystem_adapter import (
    FilesystemAdapter,
    _is_blocked_path,
    _resolve_safe,
)


class TestFilesystemAdapter:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp(prefix="umh_test_")
        self.adapter = FilesystemAdapter(safe_roots=(self.tmpdir,))

    def test_name(self):
        assert self.adapter.name == "filesystem"

    def test_supported_capabilities(self):
        caps = self.adapter.supported_capabilities
        assert "filesystem.read" in caps
        assert "filesystem.write" in caps
        assert "filesystem.list" in caps

    def test_validate_no_path(self):
        req = _make_request(capability="filesystem.read", inputs={})
        result = self.adapter.validate(req)
        assert result is not None
        assert result.status == AdapterStatus.VALIDATION_FAILED

    def test_validate_outside_safe_roots(self):
        req = _make_request(
            capability="filesystem.read",
            inputs={"path": "/etc/hosts"},
        )
        result = self.adapter.validate(req)
        assert result is not None
        assert result.status == AdapterStatus.DENIED

    def test_validate_blocked_pattern_env(self):
        req = _make_request(
            capability="filesystem.read",
            inputs={"path": os.path.join(self.tmpdir, ".env")},
        )
        result = self.adapter.validate(req)
        assert result is not None
        assert result.status == AdapterStatus.DENIED

    def test_validate_blocked_pattern_ssh(self):
        req = _make_request(
            capability="filesystem.read",
            inputs={"path": os.path.join(self.tmpdir, ".ssh")},
        )
        result = self.adapter.validate(req)
        assert result is not None
        assert result.status == AdapterStatus.DENIED

    def test_validate_write_no_content(self):
        req = _make_request(
            capability="filesystem.write",
            inputs={"path": os.path.join(self.tmpdir, "test.txt")},
        )
        result = self.adapter.validate(req)
        assert result is not None
        assert result.status == AdapterStatus.VALIDATION_FAILED

    def test_write_and_read(self):
        path = os.path.join(self.tmpdir, "test_rw.txt")
        write_req = _make_request(
            capability="filesystem.write",
            inputs={"path": path, "content": "hello phase 76"},
        )
        assert self.adapter.validate(write_req) is None
        write_result = self.adapter.execute(write_req)
        assert write_result.status == AdapterStatus.SUCCESS
        assert write_result.output["bytes_written"] == 14

        read_req = _make_request(
            capability="filesystem.read",
            inputs={"path": path},
        )
        read_result = self.adapter.execute(read_req)
        assert read_result.status == AdapterStatus.SUCCESS
        assert read_result.output["content"] == "hello phase 76"

    def test_read_nonexistent(self):
        req = _make_request(
            capability="filesystem.read",
            inputs={"path": os.path.join(self.tmpdir, "does_not_exist.txt")},
        )
        result = self.adapter.execute(req)
        assert result.status == AdapterStatus.FAILURE

    def test_list_directory(self):
        for name in ["a.txt", "b.txt", "c.txt"]:
            open(os.path.join(self.tmpdir, name), "w").close()
        req = _make_request(
            capability="filesystem.list",
            inputs={"path": self.tmpdir},
        )
        result = self.adapter.execute(req)
        assert result.status == AdapterStatus.SUCCESS
        names = [e["name"] for e in result.output["entries"]]
        assert "a.txt" in names
        assert "b.txt" in names
        assert "c.txt" in names

    def test_list_not_a_directory(self):
        path = os.path.join(self.tmpdir, "file.txt")
        open(path, "w").close()
        req = _make_request(
            capability="filesystem.list",
            inputs={"path": path},
        )
        result = self.adapter.execute(req)
        assert result.status == AdapterStatus.FAILURE

    def test_resolve_safe_blocks_traversal(self):
        assert _resolve_safe("/etc/passwd", (self.tmpdir,)) is None
        assert _resolve_safe(os.path.join(self.tmpdir, "../../etc/passwd"), (self.tmpdir,)) is None

    def test_resolve_safe_allows_within_root(self):
        valid = _resolve_safe(os.path.join(self.tmpdir, "sub/file.txt"), (self.tmpdir,))
        assert valid is not None
        assert valid.startswith(self.tmpdir)

    def test_blocked_path_patterns(self):
        assert _is_blocked_path("/opt/OS/.env") is not None
        assert _is_blocked_path("/opt/OS/id_rsa") is not None
        assert _is_blocked_path("/proc/1/status") is not None
        assert _is_blocked_path("/opt/OS/main.py") is None


# ---------------------------------------------------------------------------
# HTTP Adapter
# ---------------------------------------------------------------------------

from umh.adapters.http_adapter import HTTPAdapter, _validate_url


class TestHTTPAdapter:
    def setup_method(self):
        self.adapter = HTTPAdapter()

    def test_name(self):
        assert self.adapter.name == "http"

    def test_supported_capabilities(self):
        assert "http.get" in self.adapter.supported_capabilities
        assert "http.post" in self.adapter.supported_capabilities

    def test_validate_empty_url(self):
        req = _make_request(capability="http.get", inputs={"url": ""})
        result = self.adapter.validate(req)
        assert result is not None
        assert result.status == AdapterStatus.VALIDATION_FAILED

    def test_validate_blocked_localhost(self):
        req = _make_request(
            capability="http.get",
            inputs={"url": "http://localhost/secret"},
        )
        result = self.adapter.validate(req)
        assert result is not None
        assert result.status == AdapterStatus.VALIDATION_FAILED

    def test_validate_blocked_metadata(self):
        req = _make_request(
            capability="http.get",
            inputs={"url": "http://169.254.169.254/latest/meta-data"},
        )
        result = self.adapter.validate(req)
        assert result is not None
        assert result.status == AdapterStatus.VALIDATION_FAILED

    def test_validate_blocked_scheme_file(self):
        req = _make_request(
            capability="http.get",
            inputs={"url": "file:///etc/passwd"},
        )
        result = self.adapter.validate(req)
        assert result is not None
        assert result.status == AdapterStatus.VALIDATION_FAILED

    def test_validate_blocked_internal_host(self):
        req = _make_request(
            capability="http.get",
            inputs={"url": "http://metadata.google.internal/compute"},
        )
        result = self.adapter.validate(req)
        assert result is not None
        assert result.status == AdapterStatus.VALIDATION_FAILED

    def test_validate_post_no_body(self):
        req = _make_request(
            capability="http.post",
            inputs={"url": "https://example.com/api"},
        )
        result = self.adapter.validate(req)
        assert result is not None
        assert result.status == AdapterStatus.VALIDATION_FAILED

    def test_validate_valid_https(self):
        req = _make_request(
            capability="http.get",
            inputs={"url": "https://example.com"},
        )
        result = self.adapter.validate(req)
        assert result is None

    def test_validate_valid_post(self):
        req = _make_request(
            capability="http.post",
            inputs={"url": "https://example.com/api", "body": {"key": "value"}},
        )
        result = self.adapter.validate(req)
        assert result is None

    def test_url_validation_function(self):
        assert _validate_url("") is not None
        assert _validate_url("ftp://files.example.com") is not None
        assert _validate_url("http://127.0.0.1") is not None
        assert _validate_url("http://0.0.0.0") is not None
        assert _validate_url("http://[::1]/path") is not None
        assert _validate_url("http://host.local/api") is not None
        assert _validate_url("https://example.com/page") is None
        assert _validate_url("http://example.com/page") is None


# ---------------------------------------------------------------------------
# Simulated Browser Adapter
# ---------------------------------------------------------------------------

from umh.adapters.simulated_browser import SimulatedBrowserAdapter


class TestSimulatedBrowserAdapter:
    def setup_method(self):
        self.adapter = SimulatedBrowserAdapter()

    def test_name(self):
        assert self.adapter.name == "browser"

    def test_supported_capabilities(self):
        caps = self.adapter.supported_capabilities
        assert "browser.search" in caps
        assert "browser.open" in caps
        assert "browser.extract_text" in caps

    def test_validate_blocked_action(self):
        req = _make_request(
            capability="browser.search",
            inputs={"query": "test", "action": "login"},
        )
        result = self.adapter.validate(req)
        assert result is not None
        assert result.status == AdapterStatus.DENIED

    def test_validate_empty_search_query(self):
        req = _make_request(capability="browser.search", inputs={"query": ""})
        result = self.adapter.validate(req)
        assert result is not None
        assert result.status == AdapterStatus.VALIDATION_FAILED

    def test_validate_empty_url_open(self):
        req = _make_request(capability="browser.open", inputs={"url": ""})
        result = self.adapter.validate(req)
        assert result is not None
        assert result.status == AdapterStatus.VALIDATION_FAILED

    def test_validate_valid_search(self):
        req = _make_request(
            capability="browser.search",
            inputs={"query": "python testing"},
        )
        result = self.adapter.validate(req)
        assert result is None

    def test_search_returns_simulated(self):
        req = _make_request(
            capability="browser.search",
            inputs={"query": "python testing"},
        )
        result = self.adapter.execute(req)
        assert result.status == AdapterStatus.SIMULATED
        assert result.output["simulated"] is True
        assert len(result.output["results"]) > 0

    def test_search_deterministic(self):
        req = _make_request(
            capability="browser.search",
            inputs={"query": "deterministic query"},
        )
        r1 = self.adapter.execute(req)
        r2 = self.adapter.execute(req)
        assert r1.output["results"] == r2.output["results"]

    def test_open_returns_simulated(self):
        req = _make_request(
            capability="browser.open",
            inputs={"url": "https://example.com"},
        )
        result = self.adapter.execute(req)
        assert result.status == AdapterStatus.SIMULATED
        assert result.output["simulated"] is True
        assert result.output["status_code"] == 200

    def test_extract_text_returns_simulated(self):
        req = _make_request(
            capability="browser.extract_text",
            inputs={"url": "https://example.com"},
        )
        result = self.adapter.execute(req)
        assert result.status == AdapterStatus.SIMULATED
        assert len(result.output["text"]) > 0

    def test_blocked_actions_comprehensive(self):
        for action in ["login", "submit_form", "purchase", "payment", "oauth"]:
            req = _make_request(
                capability="browser.search",
                inputs={"query": "test", "action": action},
            )
            result = self.adapter.validate(req)
            assert result is not None, f"Action '{action}' should be blocked"
            assert result.status == AdapterStatus.DENIED


# ---------------------------------------------------------------------------
# AdapterExecutionBackend Bridge
# ---------------------------------------------------------------------------

from umh.adapters.adapter_backend import AdapterExecutionBackend
from umh.execution.contract import (
    ExecutionClass,
    ExecutionConstraints,
    ExecutionContext,
    ExecutionRequest,
    ExecutionStatus,
    ExecutionTarget,
)


def _make_exec_request(
    operation: str = "test_op",
    capability: str = "cli.command",
    inputs: dict | None = None,
) -> ExecutionRequest:
    base_inputs = {"capability": capability}
    if inputs:
        base_inputs.update(inputs)
    return ExecutionRequest(
        execution_id="exec_test_001",
        correlation_id="corr_test",
        causal_event_id="",
        session_id="",
        operation=operation,
        inputs=base_inputs,
        execution_class=ExecutionClass.SIDE_EFFECT,
        constraints=ExecutionConstraints(timeout_s=10),
        target=ExecutionTarget(node_id="local", transport="adapter"),
        context=ExecutionContext(),
        issued_at="2026-01-01T00:00:00Z",
        issued_by="test",
        idempotency_key="",
    )


class TestAdapterExecutionBackend:
    def setup_method(self):
        self.backend = AdapterExecutionBackend()
        self.backend.register_adapter(CLIAdapter())

    def test_can_handle_registered(self):
        assert self.backend.can_handle("cli.command") is True

    def test_can_handle_unregistered(self):
        assert self.backend.can_handle("nonexistent.cap") is False

    def test_registered_capabilities(self):
        assert "cli.command" in self.backend.registered_capabilities

    def test_execute_cli_echo(self):
        req = _make_exec_request(
            capability="cli.command",
            inputs={"command": "echo bridge_test"},
        )
        result = self.backend.execute(req)
        assert result.status == ExecutionStatus.SUCCEEDED
        assert "bridge_test" in result.outputs["stdout"]

    def test_execute_unknown_capability(self):
        req = _make_exec_request(capability="unknown.cap")
        result = self.backend.execute(req)
        assert result.status == ExecutionStatus.REJECTED

    def test_execute_validation_failure(self):
        req = _make_exec_request(
            capability="cli.command",
            inputs={"command": ""},
        )
        result = self.backend.execute(req)
        assert result.status == ExecutionStatus.REJECTED

    def test_execute_dangerous_denied(self):
        req = _make_exec_request(
            capability="cli.command",
            inputs={"command": "sudo rm -rf /"},
        )
        result = self.backend.execute(req)
        assert result.status == ExecutionStatus.REJECTED

    def test_multiple_adapters(self):
        self.backend.register_adapter(SimulatedBrowserAdapter())
        assert self.backend.can_handle("browser.search") is True
        assert self.backend.can_handle("cli.command") is True

        req = _make_exec_request(
            capability="browser.search",
            inputs={"query": "test"},
        )
        result = self.backend.execute(req)
        assert result.status == ExecutionStatus.SUCCEEDED
        assert result.outputs.get("_simulated") is True


# ---------------------------------------------------------------------------
# Adapter Pack Initialization
# ---------------------------------------------------------------------------

from umh.adapters.adapter_pack import (
    create_adapter_backend,
    get_adapter_pack_status,
    initialize_adapter_pack,
)
from umh.execution.backend_registry import ExecutionBackendRegistry


class TestAdapterPack:
    def test_create_backend_has_all_capabilities(self):
        backend = create_adapter_backend()
        expected = {
            "cli.command",
            "filesystem.read",
            "filesystem.write",
            "filesystem.list",
            "http.get",
            "http.post",
            "browser.search",
            "browser.open",
            "browser.extract_text",
        }
        assert backend.registered_capabilities == frozenset(expected)

    def test_initialize_registers_environments(self):
        registry = ExecutionBackendRegistry()
        initialize_adapter_pack(registry=registry, force=True)
        envs = registry.list_environments()
        for env in ["local", "vps", "filesystem", "http", "browser", "sandbox", "simulation"]:
            assert env in envs, f"Environment '{env}' not registered"

    def test_status_reports_initialized(self):
        registry = ExecutionBackendRegistry()
        initialize_adapter_pack(registry=registry, force=True)
        status = get_adapter_pack_status()
        assert status["initialized"] is True


# ---------------------------------------------------------------------------
# Governance Gate — Capability-Aware Policy
# ---------------------------------------------------------------------------

from umh.execution.governance_gate import (
    ExecutionDirective,
    GateOutcome,
    evaluate,
)
from umh.governance.authority import AuthorityLevel


class TestGovernanceCapabilityPolicy:
    def test_allow_read_in_local(self):
        d = ExecutionDirective(
            operation="filesystem.read",
            environment="local",
            capability="filesystem.read",
            authority=AuthorityLevel.ANALYZE,
        )
        gate = evaluate(d)
        assert gate.outcome in (GateOutcome.ALLOW, GateOutcome.NOTIFY)

    def test_deny_cli_in_http_env(self):
        d = ExecutionDirective(
            operation="cli.command",
            environment="http",
            capability="cli.command",
            authority=AuthorityLevel.EXECUTE,
        )
        gate = evaluate(d)
        assert gate.outcome == GateOutcome.DENY

    def test_deny_filesystem_in_browser_env(self):
        d = ExecutionDirective(
            operation="filesystem.write",
            environment="browser",
            capability="filesystem.write",
            authority=AuthorityLevel.ACT,
        )
        gate = evaluate(d)
        assert gate.outcome == GateOutcome.DENY

    def test_approve_required_http_post_insufficient_authority(self):
        d = ExecutionDirective(
            operation="http.post",
            environment="local",
            capability="http.post",
            authority=AuthorityLevel.ANALYZE,
        )
        gate = evaluate(d)
        assert gate.outcome == GateOutcome.APPROVE_REQUIRED

    def test_allow_http_post_with_act_authority(self):
        d = ExecutionDirective(
            operation="http.post",
            environment="local",
            capability="http.post",
            authority=AuthorityLevel.ACT,
        )
        gate = evaluate(d)
        assert gate.outcome in (GateOutcome.ALLOW, GateOutcome.NOTIFY)

    def test_deny_unknown_environment(self):
        d = ExecutionDirective(
            operation="cli.command",
            environment="nonexistent_env",
            capability="cli.command",
            authority=AuthorityLevel.ACT,
        )
        gate = evaluate(d)
        assert gate.outcome == GateOutcome.DENY

    def test_legacy_operations_pass_through(self):
        d = ExecutionDirective(
            operation="answer_query",
            environment="local",
            authority=AuthorityLevel.OBSERVE,
        )
        gate = evaluate(d)
        assert gate.outcome in (GateOutcome.ALLOW, GateOutcome.NOTIFY)

    def test_deny_empty_operation(self):
        d = ExecutionDirective(
            operation="",
            environment="local",
        )
        gate = evaluate(d)
        assert gate.outcome == GateOutcome.DENY

    def test_deny_no_environment(self):
        d = ExecutionDirective(
            operation="test_op",
            environment="",
        )
        gate = evaluate(d)
        assert gate.outcome == GateOutcome.DENY

    def test_browser_search_in_simulation(self):
        d = ExecutionDirective(
            operation="browser.search",
            environment="simulation",
            capability="browser.search",
            authority=AuthorityLevel.ANALYZE,
        )
        gate = evaluate(d)
        assert gate.outcome in (GateOutcome.ALLOW, GateOutcome.NOTIFY)

    def test_cli_command_requires_approval_with_analyze(self):
        d = ExecutionDirective(
            operation="cli.command",
            environment="local",
            capability="cli.command",
            authority=AuthorityLevel.ANALYZE,
        )
        gate = evaluate(d)
        assert gate.outcome == GateOutcome.APPROVE_REQUIRED


# ---------------------------------------------------------------------------
# Capability + Environment Definitions
# ---------------------------------------------------------------------------

from umh.capabilities.definitions import (
    MVP_CAPABILITIES,
    get_capability,
    list_capabilities,
)
from umh.capabilities.spec import RiskLevel
from umh.environments.definitions import (
    MVP_ENVIRONMENTS,
    get_environment,
    list_environments,
)


class TestCapabilityDefinitions:
    def test_nine_capabilities_defined(self):
        assert len(MVP_CAPABILITIES) == 9

    def test_all_capabilities_have_risk_levels(self):
        for cap in MVP_CAPABILITIES.values():
            assert isinstance(cap.risk_level, RiskLevel)

    def test_all_capabilities_have_authority(self):
        for cap in MVP_CAPABILITIES.values():
            assert isinstance(cap.authority_required, AuthorityLevel)

    def test_get_capability(self):
        cap = get_capability("cli.command")
        assert cap is not None
        assert cap.risk_level == RiskLevel.HIGH

    def test_get_capability_missing(self):
        assert get_capability("nonexistent") is None

    def test_list_capabilities(self):
        caps = list_capabilities()
        assert len(caps) == 9

    def test_cli_requires_approval(self):
        cap = get_capability("cli.command")
        assert cap.requires_approval is True

    def test_filesystem_read_no_approval(self):
        cap = get_capability("filesystem.read")
        assert cap.requires_approval is False

    def test_http_post_requires_approval(self):
        cap = get_capability("http.post")
        assert cap.requires_approval is True


class TestEnvironmentDefinitions:
    def test_seven_environments_defined(self):
        assert len(MVP_ENVIRONMENTS) == 7

    def test_local_has_all_capabilities(self):
        local = get_environment("local")
        assert local is not None
        assert "cli.command" in local.capabilities
        assert "filesystem.read" in local.capabilities
        assert "http.get" in local.capabilities
        assert "browser.search" in local.capabilities

    def test_sandbox_cli_only(self):
        sandbox = get_environment("sandbox")
        assert sandbox is not None
        assert sandbox.capabilities == frozenset({"cli.command"})

    def test_http_env_network_only(self):
        http_env = get_environment("http")
        assert http_env is not None
        assert http_env.capabilities == frozenset({"http.get", "http.post"})
        assert http_env.network_policy == "allow_https"

    def test_filesystem_env_no_network(self):
        fs_env = get_environment("filesystem")
        assert fs_env is not None
        assert fs_env.network_policy == "deny"

    def test_get_environment_missing(self):
        assert get_environment("nonexistent") is None

    def test_list_environments(self):
        envs = list_environments()
        assert len(envs) == 7

    def test_to_dict(self):
        local = get_environment("local")
        d = local.to_dict()
        assert d["environment_id"] == "local"
        assert isinstance(d["capabilities"], list)
        assert d["available"] is True


# ---------------------------------------------------------------------------
# Run all tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
