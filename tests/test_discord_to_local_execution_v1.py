"""Tests for Phase 96.8AF — Real Discord to Local Execution.

Covers:
  - command registration and normalization
  - workpacket generation for spine-routed commands
  - dispatch routing through control plane
  - spine infrastructure composition
  - authority enforcement on spine commands
  - gate validation on spine commands
  - supervisor lifecycle through spine
  - proof generation and artifact types
  - replay reconstruction from ledger
  - forbidden action structural blocking
  - command contract validation
  - spine result formatting
  - end-to-end discord-to-spine execution
  - regression: existing commands unaffected
"""

import sys
import tempfile
import json

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"

import pytest
from pathlib import Path

from runtime.interfaces.discord_interface_adapter_v1 import (
    COMMAND_ACTION_MAP,
    COMMAND_CONTRACT,
    SPINE_ROUTED_COMMANDS,
    SUPPORTED_COMMANDS,
    build_work_packet,
    build_work_packet_for_router,
    format_router_result,
)
from runtime.interfaces.discord_spine_integration_v1 import (
    SpineExecutionConfig,
    SpineRoutedResult,
    build_spine_infrastructure,
    execute_spine_command,
    format_spine_result,
)
from control_plane.router.router_contracts import (
    ALLOWED_ACTION_TYPES,
    CapabilityType,
    RouterResult,
    RouterStatus,
    WorkPacket,
)
from control_plane.router.control_plane_router_v1 import (
    ACTION_CAPABILITY_MAP,
    ControlPlaneRouterV1,
)
from adapters.adapter_engine.adapter_registry_contracts import AdapterRegistry
from execution.runtime.live_local_runtime_execution_v1 import (
    ExecutionSpineOutcome,
    LiveLocalRuntimeExecution,
    SPINE_FORBIDDEN_ACTIONS,
)
from execution.runtime.local_runtime_supervisor_v1 import (
    SUPERVISOR_FORBIDDEN_ACTIONS,
)
from governance.policy.execution_authority_engine_v1 import (
    AuthorityClass,
    CapabilityAuthority,
    EnvironmentAuthority,
    ExecutionAuthorityEngine,
    RiskClass,
)
from execution.runtime.workpacket_execution_gate_v1 import (
    WorkPacketExecutionGate,
)
from execution.runtime.runtime_dispatch_queue_v1 import (
    DispatchRecord,
    RuntimeDispatchQueue,
)
from execution.runtime.runtime_execution_result_v1 import (
    ExecutionOutcome,
    ProofArtifactType,
)
from execution.runtime.runtime_recovery_v1 import (
    FailureType,
    RuntimeRecoveryEngine,
)
from execution.runtime.runtime_session_registry_v1 import (
    RuntimeSessionRegistry,
)
from execution.runtime.local_runtime_supervisor_v1 import (
    LocalRuntimeSupervisor,
)
from state.transformation_state_ledger import (
    TransformationStage,
    TransformationStateLedger,
)


# -- Fixtures --


def _make_spine(tmp: Path) -> LiveLocalRuntimeExecution:
    """Build a test spine with all infrastructure."""
    env_auth = EnvironmentAuthority(
        environment_type="local_windows_desktop",
        can_own_gui=True,
        can_own_local_shell=True,
        can_execute_browser=True,
        max_risk_class=RiskClass.MEDIUM,
    )
    cap_auth = CapabilityAuthority(
        adapter_id="windows_interactive_desktop_relay",
        capabilities=[
            "browser_execution",
            "chrome_launch",
            "chrome_open_google_drive",
            "open_application_url",
        ],
        is_configured=True,
        is_mature=True,
    )
    authority = ExecutionAuthorityEngine(
        environment_authorities=[env_auth],
        capability_authorities=[cap_auth],
    )
    ledger = TransformationStateLedger(tmp / "ledger")
    gate = WorkPacketExecutionGate(
        environment_authorities={"local_windows_desktop": env_auth},
        capability_authorities={"windows_interactive_desktop_relay": cap_auth},
        available_runtimes={"local-worker-01": True},
        ledger=ledger,
        proof_dir=tmp / "gate_proofs",
    )
    queue = RuntimeDispatchQueue(tmp / "queue")
    registry = RuntimeSessionRegistry()
    recovery = RuntimeRecoveryEngine(max_retries=3)
    supervisor = LocalRuntimeSupervisor(
        queue=queue,
        registry=registry,
        recovery=recovery,
        ledger=ledger,
        proof_dir=tmp / "exec_proofs",
        worker_id="local-worker-01",
        environment_id="local_windows_desktop",
    )
    supervisor.start()
    return LiveLocalRuntimeExecution(
        authority_engine=authority,
        gate=gate,
        queue=queue,
        supervisor=supervisor,
        ledger=ledger,
        proof_dir=tmp / "spine_proofs",
    )


def _make_test_registry(tmpdir: str) -> None:
    """Write a test adapter registry with chrome_open_google_drive capability."""
    reg_dir = Path(tmpdir) / "data" / "registries"
    reg_dir.mkdir(parents=True, exist_ok=True)
    registry = {
        "workers": {
            "windows_interactive_desktop_relay": {
                "environment_type": "local_windows_desktop",
                "authority_domains": ["local_gui"],
                "can_own_gui": True,
                "message_bus": "filesystem_json",
                "capabilities": ["ping", "open_application_url", "chrome_open_google_drive"],
            }
        },
        "adapters": {
            "windows_interactive_desktop_relay": {
                "adapter_type": "gui_actuator",
                "environment_type": "local_windows_desktop",
                "authority_domain": "local_gui",
                "message_bus": "filesystem_json",
                "capabilities": [
                    {
                        "capability_id": "ping",
                        "action_type": "ping",
                        "requires_gui": False,
                        "required_authority": "local_shell",
                    },
                    {
                        "capability_id": "open_application_url",
                        "action_type": "open_application_url",
                        "requires_gui": True,
                        "required_authority": "local_gui",
                    },
                    {
                        "capability_id": "chrome_open_google_drive",
                        "action_type": "chrome_open_google_drive",
                        "requires_gui": True,
                        "required_authority": "local_gui",
                    },
                ],
            }
        },
    }
    with open(reg_dir / "local_worker_adapter_registry_v1.json", "w") as f:
        json.dump(registry, f)


# ========================================================
# Test: Command Registration
# ========================================================


class TestCommandRegistration:
    def test_chrome_open_google_drive_in_supported(self):
        assert "!chrome-open-google-drive" in SUPPORTED_COMMANDS

    def test_chrome_open_google_drive_in_action_map(self):
        assert "!chrome-open-google-drive" in COMMAND_ACTION_MAP
        assert COMMAND_ACTION_MAP["!chrome-open-google-drive"] == "chrome_open_google_drive"

    def test_chrome_open_google_drive_is_spine_routed(self):
        assert "!chrome-open-google-drive" in SPINE_ROUTED_COMMANDS

    def test_existing_commands_still_supported(self):
        for cmd in ["!ping", "!chrome", "!doc", "!extract", "!status"]:
            assert cmd in SUPPORTED_COMMANDS

    def test_existing_commands_not_spine_routed(self):
        for cmd in ["!ping", "!chrome", "!doc", "!extract"]:
            assert cmd not in SPINE_ROUTED_COMMANDS


# ========================================================
# Test: Command Normalization
# ========================================================


class TestCommandNormalization:
    def test_action_type_is_chrome_open_google_drive(self):
        assert COMMAND_ACTION_MAP["!chrome-open-google-drive"] == "chrome_open_google_drive"

    def test_action_type_in_allowed_actions(self):
        assert "chrome_open_google_drive" in ALLOWED_ACTION_TYPES

    def test_capability_mapping_exists(self):
        assert "chrome_open_google_drive" in ACTION_CAPABILITY_MAP
        cap = ACTION_CAPABILITY_MAP["chrome_open_google_drive"]
        assert cap.capability_type == CapabilityType.WINDOWS_GUI_EXECUTION
        assert cap.requires_gui is True

    def test_command_contract_exists(self):
        assert "!chrome-open-google-drive" in COMMAND_CONTRACT
        contract = COMMAND_CONTRACT["!chrome-open-google-drive"]
        assert contract["capability"] == "WINDOWS_GUI_EXECUTION"
        assert contract["adapter"] == "windows_interactive_desktop_relay"
        assert contract["proof_required"] is True
        assert contract["mutation_allowed"] is False


# ========================================================
# Test: WorkPacket Generation
# ========================================================


class TestWorkPacketGeneration:
    def test_builds_work_packet_for_router(self):
        wp = build_work_packet_for_router("!chrome-open-google-drive")
        assert wp is not None
        assert isinstance(wp, WorkPacket)
        assert wp.action_type == "chrome_open_google_drive"

    def test_packet_has_safe_url(self):
        wp = build_work_packet_for_router("!chrome-open-google-drive")
        assert wp.payload["url"] == "https://drive.google.com/drive/my-drive"

    def test_packet_has_source_interface(self):
        wp = build_work_packet_for_router("!chrome-open-google-drive")
        assert wp.source_interface == "discord_interface_adapter_v1"

    def test_packet_has_chrome_executable(self):
        wp = build_work_packet_for_router("!chrome-open-google-drive")
        assert "chrome.exe" in wp.payload["executable_path"].lower()

    def test_packet_blocks_unsafe_methods(self):
        wp = build_work_packet_for_router("!chrome-open-google-drive")
        blocked = wp.payload.get("blocked_launch_methods", [])
        assert "explorer_url" in blocked
        assert "default_browser" in blocked

    def test_packet_requires_no_mutation(self):
        wp = build_work_packet_for_router("!chrome-open-google-drive")
        assert wp.payload.get("no_mutation") is True


# ========================================================
# Test: Dispatch Routing (Control Plane)
# ========================================================


class TestDispatchRouting:
    def test_router_validates_chrome_open_google_drive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_test_registry(tmpdir)
            registry = AdapterRegistry.from_json_file(
                Path(tmpdir) / "data" / "registries" / "local_worker_adapter_registry_v1.json"
            )
            router = ControlPlaneRouterV1(
                registry=registry,
                config={"default_timeout_seconds": 2},
                base_dir=Path(tmpdir),
            )
            wp = WorkPacket(
                packet_id="PKT-test-drive",
                action_type="chrome_open_google_drive",
            )
            err = router.validate_packet(wp)
            assert err is None

    def test_router_resolves_capability(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_test_registry(tmpdir)
            registry = AdapterRegistry.from_json_file(
                Path(tmpdir) / "data" / "registries" / "local_worker_adapter_registry_v1.json"
            )
            router = ControlPlaneRouterV1(
                registry=registry,
                config={"default_timeout_seconds": 2},
                base_dir=Path(tmpdir),
            )
            cap = router.resolve_capability("chrome_open_google_drive")
            assert cap is not None
            assert cap.capability_type == CapabilityType.WINDOWS_GUI_EXECUTION

    def test_router_resolves_adapter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_test_registry(tmpdir)
            registry = AdapterRegistry.from_json_file(
                Path(tmpdir) / "data" / "registries" / "local_worker_adapter_registry_v1.json"
            )
            router = ControlPlaneRouterV1(
                registry=registry,
                config={"default_timeout_seconds": 2},
                base_dir=Path(tmpdir),
            )
            adapter = router.resolve_adapter("chrome_open_google_drive")
            assert adapter is not None
            assert adapter.adapter_id == "windows_interactive_desktop_relay"

    def test_router_dry_run_routes_successfully(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_test_registry(tmpdir)
            registry = AdapterRegistry.from_json_file(
                Path(tmpdir) / "data" / "registries" / "local_worker_adapter_registry_v1.json"
            )
            router = ControlPlaneRouterV1(
                registry=registry,
                config={"default_timeout_seconds": 2},
                base_dir=Path(tmpdir),
            )
            wp = WorkPacket(
                packet_id="PKT-dry-run",
                action_type="chrome_open_google_drive",
            )
            result = router.route_dry_run(wp)
            assert result.router_status == RouterStatus.ROUTED
            assert result.router_decision is not None
            assert result.adapter_selected == "windows_interactive_desktop_relay"


# ========================================================
# Test: Spine Infrastructure
# ========================================================


class TestSpineInfrastructure:
    def test_build_spine_infrastructure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = SpineExecutionConfig(
                queue_dir=Path("queue"),
                ledger_dir=Path("ledger"),
                proof_dir=Path("proofs"),
                gate_proof_dir=Path("gate_proofs"),
            )
            spine = build_spine_infrastructure(config, Path(tmpdir))
            assert isinstance(spine, LiveLocalRuntimeExecution)

    def test_spine_config_defaults(self):
        config = SpineExecutionConfig()
        assert config.worker_id == "local-worker-01"
        assert config.environment_id == "local_windows_desktop"
        assert config.max_retries == 3


# ========================================================
# Test: Authority Enforcement
# ========================================================


class TestAuthorityEnforcement:
    def test_spine_allows_chrome_open_google_drive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            spine = _make_spine(Path(tmpdir))
            result = spine.execute(
                packet_id="PKT-auth-test",
                action_type="chrome_open_google_drive",
                target_environment="local_windows_desktop",
                target_runtime="local-worker-01",
                required_adapter_id="windows_interactive_desktop_relay",
            )
            assert result.outcome == ExecutionSpineOutcome.SUCCESS
            assert result.authority_decision is not None
            assert result.authority_decision.authority_class != AuthorityClass.DENY

    def test_spine_blocks_forbidden_action(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            spine = _make_spine(Path(tmpdir))
            result = spine.execute(
                packet_id="PKT-forbidden",
                action_type="wallet_execution",
            )
            assert result.outcome == ExecutionSpineOutcome.GOVERNANCE_BLOCKED
            assert "structurally_forbidden" in result.denial_reasons[0]

    def test_forbidden_actions_defense_in_depth(self):
        assert "wallet_execution" in SPINE_FORBIDDEN_ACTIONS
        assert "financial_execution" in SPINE_FORBIDDEN_ACTIONS
        assert "credential_access" in SPINE_FORBIDDEN_ACTIONS
        assert "wallet_execution" in SUPERVISOR_FORBIDDEN_ACTIONS


# ========================================================
# Test: Gate Validation
# ========================================================


class TestGateValidation:
    def test_gate_passes_for_chrome_open_google_drive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            spine = _make_spine(Path(tmpdir))
            result = spine.execute(
                packet_id="PKT-gate-test",
                action_type="chrome_open_google_drive",
                target_environment="local_windows_desktop",
                target_runtime="local-worker-01",
                required_adapter_id="windows_interactive_desktop_relay",
            )
            assert result.gate_result is not None
            assert result.outcome == ExecutionSpineOutcome.SUCCESS


# ========================================================
# Test: Proof Generation
# ========================================================


class TestProofGeneration:
    def test_execution_generates_proofs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            spine = _make_spine(Path(tmpdir))
            result = spine.execute(
                packet_id="PKT-proof-test",
                action_type="chrome_open_google_drive",
                target_environment="local_windows_desktop",
                target_runtime="local-worker-01",
                required_adapter_id="windows_interactive_desktop_relay",
            )
            assert result.succeeded
            assert result.execution_result is not None
            assert len(result.execution_result.proof_artifacts) >= 7

    def test_proof_types_cover_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            spine = _make_spine(Path(tmpdir))
            result = spine.execute(
                packet_id="PKT-proof-types",
                action_type="chrome_open_google_drive",
                target_environment="local_windows_desktop",
                target_runtime="local-worker-01",
                required_adapter_id="windows_interactive_desktop_relay",
            )
            proof_types = {p.proof_type.value for p in result.execution_result.proof_artifacts}
            assert "dispatch_proof" in proof_types
            assert "execution_proof" in proof_types
            assert "adapter_boundary_proof" in proof_types

    def test_proof_persists_to_disk(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            spine = _make_spine(Path(tmpdir))
            result = spine.execute(
                packet_id="PKT-proof-persist",
                action_type="chrome_open_google_drive",
                target_environment="local_windows_desktop",
                target_runtime="local-worker-01",
                required_adapter_id="windows_interactive_desktop_relay",
            )
            proof_dir = Path(tmpdir) / "spine_proofs"
            proof_files = list(proof_dir.glob("*.json"))
            assert len(proof_files) >= 1

    def test_proof_has_hash_chain(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            spine = _make_spine(Path(tmpdir))
            result = spine.execute(
                packet_id="PKT-proof-hash",
                action_type="chrome_open_google_drive",
                target_environment="local_windows_desktop",
                target_runtime="local-worker-01",
                required_adapter_id="windows_interactive_desktop_relay",
            )
            for proof in result.execution_result.proof_artifacts:
                assert proof.content_hash, f"proof {proof.proof_type} missing hash"


# ========================================================
# Test: Replay Reconstruction
# ========================================================


class TestReplayReconstruction:
    def test_ledger_captures_all_stages(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            spine = _make_spine(Path(tmpdir))
            result = spine.execute(
                packet_id="PKT-replay-test",
                action_type="chrome_open_google_drive",
                target_environment="local_windows_desktop",
                target_runtime="local-worker-01",
                required_adapter_id="windows_interactive_desktop_relay",
                trace_id="TRACE-replay-af",
            )
            assert result.succeeded
            ledger = TransformationStateLedger(Path(tmpdir) / "ledger")
            ledger_files = list((Path(tmpdir) / "ledger").glob("*.json"))
            assert len(ledger_files) >= 7

    def test_trace_is_reconstructable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            spine = _make_spine(Path(tmpdir))
            result = spine.execute(
                packet_id="PKT-trace-test",
                action_type="chrome_open_google_drive",
                target_environment="local_windows_desktop",
                target_runtime="local-worker-01",
                required_adapter_id="windows_interactive_desktop_relay",
            )
            assert result.trace_id


# ========================================================
# Test: Spine Result Formatting
# ========================================================


class TestSpineResultFormatting:
    def test_format_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            spine = _make_spine(Path(tmpdir))
            spine_result = spine.execute(
                packet_id="PKT-fmt-test",
                action_type="chrome_open_google_drive",
                target_environment="local_windows_desktop",
                target_runtime="local-worker-01",
                required_adapter_id="windows_interactive_desktop_relay",
            )
            routed = SpineRoutedResult(
                command="!chrome-open-google-drive",
                spine_result=spine_result,
            )
            formatted = format_spine_result(routed)
            assert "!chrome-open-google-drive" in formatted
            assert "success" in formatted
            assert "spine_id" in formatted

    def test_format_denied(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            spine = _make_spine(Path(tmpdir))
            spine_result = spine.execute(
                packet_id="PKT-denied",
                action_type="wallet_execution",
            )
            routed = SpineRoutedResult(
                command="!chrome-open-google-drive",
                spine_result=spine_result,
            )
            formatted = format_spine_result(routed)
            assert "governance_blocked" in formatted
            assert "denied" in formatted

    def test_format_error(self):
        routed = SpineRoutedResult(
            command="!chrome-open-google-drive",
            error_message="no action_type mapping",
        )
        formatted = format_spine_result(routed)
        assert "error" in formatted

    def test_succeeded_property(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            spine = _make_spine(Path(tmpdir))
            spine_result = spine.execute(
                packet_id="PKT-prop-test",
                action_type="chrome_open_google_drive",
                target_environment="local_windows_desktop",
                target_runtime="local-worker-01",
                required_adapter_id="windows_interactive_desktop_relay",
            )
            routed = SpineRoutedResult(
                command="!chrome-open-google-drive",
                spine_result=spine_result,
            )
            assert routed.succeeded is True


# ========================================================
# Test: execute_spine_command Integration
# ========================================================


class TestExecuteSpineCommand:
    def test_chrome_open_google_drive_succeeds(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            spine = _make_spine(Path(tmpdir))
            result = execute_spine_command(spine, "!chrome-open-google-drive")
            assert result.succeeded
            assert result.command == "!chrome-open-google-drive"

    def test_unknown_command_returns_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            spine = _make_spine(Path(tmpdir))
            result = execute_spine_command(spine, "!nonexistent")
            assert not result.succeeded
            assert "no action_type mapping" in result.error_message

    def test_spine_result_has_trace_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            spine = _make_spine(Path(tmpdir))
            result = execute_spine_command(spine, "!chrome-open-google-drive")
            assert result.spine_result.trace_id
            assert result.spine_result.trace_id.startswith("DISCORD-SPINE-")

    def test_to_dict_serializable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            spine = _make_spine(Path(tmpdir))
            result = execute_spine_command(spine, "!chrome-open-google-drive")
            d = result.to_dict()
            assert d["succeeded"] is True
            assert d["command"] == "!chrome-open-google-drive"
            serialized = json.dumps(d, default=str)
            assert len(serialized) > 0


# ========================================================
# Test: End-to-End Discord→Spine
# ========================================================


class TestEndToEndDiscordToSpine:
    def test_full_path_success(self):
        """Discord command → WorkPacket → Authority → Gate → Dispatch
        → Supervisor → Proof → Ledger → Result"""
        with tempfile.TemporaryDirectory() as tmpdir:
            spine = _make_spine(Path(tmpdir))
            wp = build_work_packet_for_router("!chrome-open-google-drive")
            assert wp is not None

            result = execute_spine_command(
                spine,
                "!chrome-open-google-drive",
                packet_id=wp.packet_id,
                action_type=wp.action_type,
            )

            assert result.succeeded
            sr = result.spine_result
            assert sr.authority_decision is not None
            assert sr.gate_result is not None
            assert sr.execution_result is not None
            assert sr.execution_result.outcome == ExecutionOutcome.SUCCESS
            assert len(sr.execution_result.proof_artifacts) >= 7

    def test_full_path_persists_to_ledger(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            spine = _make_spine(Path(tmpdir))
            result = execute_spine_command(spine, "!chrome-open-google-drive")
            assert result.succeeded
            ledger_files = list((Path(tmpdir) / "ledger").glob("*.json"))
            assert len(ledger_files) >= 7

    def test_full_path_persists_spine_proof(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            spine = _make_spine(Path(tmpdir))
            result = execute_spine_command(spine, "!chrome-open-google-drive")
            assert result.succeeded
            spine_proofs = list((Path(tmpdir) / "spine_proofs").glob("*.json"))
            assert len(spine_proofs) >= 1

    def test_full_path_forbidden_action_blocked(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            spine = _make_spine(Path(tmpdir))
            result = execute_spine_command(
                spine,
                "!chrome-open-google-drive",
                action_type="wallet_execution",
            )
            assert not result.succeeded
            assert result.spine_result.outcome == ExecutionSpineOutcome.GOVERNANCE_BLOCKED


# ========================================================
# Test: Regression - Existing Commands Unaffected
# ========================================================


class TestRegressionExistingCommands:
    def test_ping_still_builds_packet(self):
        wp = build_work_packet_for_router("!ping")
        assert wp is not None
        assert wp.action_type == "ping"

    def test_chrome_still_builds_packet(self):
        wp = build_work_packet_for_router("!chrome")
        assert wp is not None
        assert wp.action_type == "open_application_url"

    def test_doc_still_builds_packet(self):
        wp = build_work_packet_for_router("!doc")
        assert wp is not None
        assert wp.action_type == "drive_open_safe_test_doc"

    def test_legacy_ping_still_works(self):
        packet = build_work_packet("!ping")
        assert packet is not None
        assert packet["action_type"] == "ping"

    def test_legacy_chrome_still_works(self):
        packet = build_work_packet("!chrome")
        assert packet is not None
        assert packet["action_type"] == "open_application_url"

    def test_unknown_still_rejected(self):
        assert build_work_packet_for_router("!hack") is None
        assert build_work_packet("!hack") is None


# ========================================================
# Test: Adapter Registry
# ========================================================


class TestAdapterRegistry:
    def test_production_registry_has_chrome_open_google_drive(self):
        registry = AdapterRegistry.from_json_file(
            Path(_ROOT) / "data" / "registries" / "local_worker_adapter_registry_v1.json"
        )
        adapter = registry.find_adapter_for_action("chrome_open_google_drive")
        assert adapter is not None
        assert adapter.adapter_id == "windows_interactive_desktop_relay"

    def test_production_registry_still_has_existing_capabilities(self):
        registry = AdapterRegistry.from_json_file(
            Path(_ROOT) / "data" / "registries" / "local_worker_adapter_registry_v1.json"
        )
        for action in ["ping", "open_application_url", "drive_open_safe_test_doc"]:
            adapter = registry.find_adapter_for_action(action)
            assert adapter is not None, f"adapter missing for {action}"


# ========================================================
# Test: Command Contract
# ========================================================


class TestCommandContract:
    def test_contract_complete(self):
        contract = COMMAND_CONTRACT["!chrome-open-google-drive"]
        required_fields = [
            "command",
            "capability",
            "adapter",
            "environment",
            "authority_required",
            "proof_required",
            "mutation_allowed",
        ]
        for f in required_fields:
            assert f in contract, f"missing field: {f}"

    def test_contract_no_mutation(self):
        contract = COMMAND_CONTRACT["!chrome-open-google-drive"]
        assert contract["mutation_allowed"] is False

    def test_contract_proof_required(self):
        contract = COMMAND_CONTRACT["!chrome-open-google-drive"]
        assert contract["proof_required"] is True

    def test_contract_authority(self):
        contract = COMMAND_CONTRACT["!chrome-open-google-drive"]
        assert contract["authority_required"] == "FOUNDER_APPROVAL"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
