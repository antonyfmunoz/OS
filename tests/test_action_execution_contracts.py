"""Tests for execution/action_execution_contracts.py — Phase 96.8A.1."""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import unittest
from execution.runtime.action_execution_contracts import (
    ActionType,
    ExecutionSeparationStatus,
    ActionContract,
    ExecutionBinding,
    build_action_contract,
    build_execution_binding,
    action_contract_is_complete,
    execution_binding_is_complete,
    validate_action_execution_separation,
    summarize_action_execution_contract,
)


class TestActionContractBuilds(unittest.TestCase):
    def test_build_returns_action_contract(self):
        ac = build_action_contract(
            action_id="act-001",
            action_type=ActionType.READ,
            intended_state_change="Read Drive inventory",
        )
        self.assertIsInstance(ac, ActionContract)
        self.assertEqual(ac.action_id, "act-001")
        self.assertEqual(ac.action_type, ActionType.READ)

    def test_default_risk_level(self):
        ac = build_action_contract(action_id="act-002")
        self.assertEqual(ac.risk_level, "low")


class TestExecutionBindingBuilds(unittest.TestCase):
    def test_build_returns_binding(self):
        eb = build_execution_binding(
            action_id="act-001",
            work_packet_id="wp-001",
            environment_id="local_wsl",
            worker_runtime_id="wsl-worker-001",
            adapter_boundaries=["env-bridge-local-wsl"],
        )
        self.assertIsInstance(eb, ExecutionBinding)
        self.assertEqual(eb.action_id, "act-001")
        self.assertEqual(eb.environment_id, "local_wsl")

    def test_default_status(self):
        eb = build_execution_binding(action_id="act-003")
        self.assertEqual(eb.status, "pending")


class TestActionWithoutCapabilityInvalid(unittest.TestCase):
    def test_no_capabilities(self):
        ac = build_action_contract(
            action_id="act-010",
            intended_state_change="Read files",
            governance_policy="gov",
            proof_requirements=["proof"],
        )
        eb = build_execution_binding(
            action_id="act-010",
            environment_id="local_wsl",
            worker_runtime_id="worker",
            adapter_boundaries=["adapter"],
        )
        status = validate_action_execution_separation(ac, eb)
        self.assertEqual(status, ExecutionSeparationStatus.CAPABILITY_MISSING)


class TestBindingWithoutEnvironmentInvalid(unittest.TestCase):
    def test_no_environment(self):
        ac = build_action_contract(
            action_id="act-020",
            required_capabilities=["read"],
            intended_state_change="Read",
            governance_policy="gov",
            proof_requirements=["proof"],
        )
        eb = build_execution_binding(
            action_id="act-020",
            worker_runtime_id="worker",
            adapter_boundaries=["adapter"],
        )
        status = validate_action_execution_separation(ac, eb)
        self.assertEqual(status, ExecutionSeparationStatus.ENVIRONMENT_MISSING)


class TestBindingWithoutWorkerInvalid(unittest.TestCase):
    def test_no_worker(self):
        ac = build_action_contract(
            action_id="act-030",
            required_capabilities=["read"],
            intended_state_change="Read",
            governance_policy="gov",
            proof_requirements=["proof"],
        )
        eb = build_execution_binding(
            action_id="act-030",
            environment_id="local_wsl",
            adapter_boundaries=["adapter"],
        )
        status = validate_action_execution_separation(ac, eb)
        self.assertEqual(status, ExecutionSeparationStatus.WORKER_MISSING)


class TestBindingWithoutAdapterBoundaryInvalid(unittest.TestCase):
    def test_no_adapter_boundary(self):
        ac = build_action_contract(
            action_id="act-040",
            required_capabilities=["read"],
            intended_state_change="Read",
            governance_policy="gov",
            proof_requirements=["proof"],
        )
        eb = build_execution_binding(
            action_id="act-040",
            environment_id="local_wsl",
            worker_runtime_id="worker",
        )
        status = validate_action_execution_separation(ac, eb)
        self.assertEqual(status, ExecutionSeparationStatus.ADAPTER_BOUNDARY_MISSING)


class TestActionExecutionSeparationValidatesWhenComplete(unittest.TestCase):
    def test_complete_separation_is_valid(self):
        ac = build_action_contract(
            action_id="act-100",
            action_type=ActionType.READ,
            intended_state_change="Read Drive inventory",
            required_capabilities=["drive_read"],
            required_adapters=["W-GDRIVE-API-001"],
            required_environments=["local_wsl"],
            required_workers=["wsl-worker"],
            governance_policy="cu_governance_v1",
            proof_requirements=["inventory_visible"],
        )
        eb = build_execution_binding(
            action_id="act-100",
            work_packet_id="wp-100",
            environment_id="local_wsl",
            worker_runtime_id="wsl-worker-001",
            adapter_boundaries=["env-bridge-local-wsl"],
            trace_id="trace-100",
        )
        status = validate_action_execution_separation(ac, eb)
        self.assertEqual(status, ExecutionSeparationStatus.VALID)


class TestAdapterIsNotTreatedAsWorker(unittest.TestCase):
    def test_adapter_in_boundaries_not_worker(self):
        eb = build_execution_binding(
            action_id="act-200",
            environment_id="local_wsl",
            worker_runtime_id="wsl-worker",
            adapter_boundaries=["W-GDRIVE-API-001"],
        )
        self.assertNotEqual(eb.adapter_boundaries[0], eb.worker_runtime_id)

    def test_environment_is_not_worker(self):
        eb = build_execution_binding(
            action_id="act-210",
            environment_id="local_wsl",
            worker_runtime_id="wsl-worker",
            adapter_boundaries=["env-bridge"],
        )
        self.assertNotEqual(eb.environment_id, eb.worker_runtime_id)


class TestActionMissing(unittest.TestCase):
    def test_empty_action_id(self):
        ac = build_action_contract(action_id="")
        eb = build_execution_binding(action_id="")
        status = validate_action_execution_separation(ac, eb)
        self.assertEqual(status, ExecutionSeparationStatus.ACTION_MISSING)


class TestGovernanceMissing(unittest.TestCase):
    def test_no_governance(self):
        ac = build_action_contract(
            action_id="act-300",
            required_capabilities=["read"],
            intended_state_change="Read",
            proof_requirements=["proof"],
        )
        eb = build_execution_binding(
            action_id="act-300",
            environment_id="env",
            worker_runtime_id="worker",
            adapter_boundaries=["adapter"],
        )
        status = validate_action_execution_separation(ac, eb)
        self.assertEqual(status, ExecutionSeparationStatus.GOVERNANCE_MISSING)


class TestProofMissing(unittest.TestCase):
    def test_no_proof(self):
        ac = build_action_contract(
            action_id="act-310",
            required_capabilities=["read"],
            intended_state_change="Read",
            governance_policy="gov",
        )
        eb = build_execution_binding(
            action_id="act-310",
            environment_id="env",
            worker_runtime_id="worker",
            adapter_boundaries=["adapter"],
        )
        status = validate_action_execution_separation(ac, eb)
        self.assertEqual(status, ExecutionSeparationStatus.PROOF_MISSING)


class TestSummarize(unittest.TestCase):
    def test_summarize_returns_dict(self):
        ac = build_action_contract(action_id="act-400")
        eb = build_execution_binding(action_id="act-400")
        s = summarize_action_execution_contract(ac, eb)
        self.assertIsInstance(s, dict)
        self.assertIn("separation_status", s)
        self.assertIn("action_complete", s)
        self.assertIn("binding_complete", s)


class TestToDict(unittest.TestCase):
    def test_action_to_dict(self):
        ac = build_action_contract(action_id="act-500")
        d = ac.to_dict()
        self.assertIn("action_id", d)
        self.assertIn("action_type", d)

    def test_binding_to_dict(self):
        eb = build_execution_binding(action_id="act-500")
        d = eb.to_dict()
        self.assertIn("action_id", d)
        self.assertIn("environment_id", d)


if __name__ == "__main__":
    unittest.main()
