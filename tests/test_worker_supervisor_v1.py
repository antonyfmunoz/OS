"""Tests for Worker Supervisor v1.

Phase 96.8AB — autonomous worker supervision validation.
"""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import pytest

from execution.runtime.worker_runtime_contracts import WorkerHeartbeat
from execution.runtime.worker_supervisor_v1 import (
    AUTOSTART_ALLOWED_WORKERS,
    REQUIRES_HUMAN_CONFIRMATION,
    WORKER_DEPENDENCIES,
    AutostartDecision,
    RecoveryAction,
    WorkerHealthCheck,
    WorkerHealthStatus,
    WorkerRecoveryResult,
    WorkerStartupPlan,
    WorkerSupervisor,
    WorkerType,
)


class TestWorkerSupervisor:
    def test_init(self) -> None:
        sup = WorkerSupervisor()
        assert sup is not None

    def test_check_healthy_worker(self) -> None:
        sup = WorkerSupervisor()
        hb = WorkerHeartbeat(worker_id="daemon", status="alive")
        check = sup.check_worker(WorkerType.LOCAL_RUNTIME_DAEMON, hb)
        assert check.status == WorkerHealthStatus.HEALTHY
        assert check.connectivity_ok is True

    def test_check_degraded_worker(self) -> None:
        sup = WorkerSupervisor()
        hb = WorkerHeartbeat(worker_id="daemon", status="degraded")
        check = sup.check_worker(WorkerType.LOCAL_RUNTIME_DAEMON, hb)
        assert check.status == WorkerHealthStatus.DEGRADED

    def test_check_unknown_worker(self) -> None:
        sup = WorkerSupervisor()
        check = sup.check_worker(WorkerType.LOCAL_RUNTIME_DAEMON)
        assert check.status == WorkerHealthStatus.UNKNOWN

    def test_unmet_dependencies_detected(self) -> None:
        sup = WorkerSupervisor()
        check = sup.check_worker(WorkerType.DRIVE_ADAPTER)
        assert check.dependencies_met is False
        assert "chrome_browser" in check.unmet_dependencies

    def test_dependencies_met_when_healthy(self) -> None:
        sup = WorkerSupervisor()
        hb_daemon = WorkerHeartbeat(worker_id="daemon", status="alive")
        sup.check_worker(WorkerType.LOCAL_RUNTIME_DAEMON, hb_daemon)
        hb_relay = WorkerHeartbeat(worker_id="relay", status="alive")
        sup.check_worker(WorkerType.WINDOWS_RELAY, hb_relay)
        hb_chrome = WorkerHeartbeat(worker_id="chrome", status="alive")
        sup.check_worker(WorkerType.CHROME_BROWSER, hb_chrome)
        check = sup.check_worker(WorkerType.DRIVE_ADAPTER)
        assert check.dependencies_met is True


class TestWorkerStartupPlan:
    def test_already_healthy(self) -> None:
        sup = WorkerSupervisor()
        hb = WorkerHeartbeat(worker_id="daemon", status="alive")
        sup.check_worker(WorkerType.LOCAL_RUNTIME_DAEMON, hb)
        plan = sup.plan_startup(WorkerType.LOCAL_RUNTIME_DAEMON)
        assert plan.recovery_action == RecoveryAction.NO_ACTION

    def test_autostart_allowed_for_daemon(self) -> None:
        sup = WorkerSupervisor()
        sup.check_worker(WorkerType.LOCAL_RUNTIME_DAEMON)
        plan = sup.plan_startup(WorkerType.LOCAL_RUNTIME_DAEMON)
        assert plan.autostart_decision == AutostartDecision.ALLOWED
        assert plan.recovery_action == RecoveryAction.AUTOSTART

    def test_autostart_allowed_for_discord(self) -> None:
        sup = WorkerSupervisor()
        sup.check_worker(WorkerType.DISCORD_ADAPTER)
        plan = sup.plan_startup(WorkerType.DISCORD_ADAPTER)
        assert plan.autostart_decision == AutostartDecision.ALLOWED

    def test_chrome_requires_human(self) -> None:
        sup = WorkerSupervisor()
        hb_daemon = WorkerHeartbeat(worker_id="d", status="alive")
        sup.check_worker(WorkerType.LOCAL_RUNTIME_DAEMON, hb_daemon)
        hb_relay = WorkerHeartbeat(worker_id="r", status="alive")
        sup.check_worker(WorkerType.WINDOWS_RELAY, hb_relay)
        sup.check_worker(WorkerType.CHROME_BROWSER)
        plan = sup.plan_startup(WorkerType.CHROME_BROWSER)
        assert plan.autostart_decision == AutostartDecision.REQUIRES_HUMAN
        assert plan.recovery_action == RecoveryAction.ESCALATE_TO_FOUNDER

    def test_relay_requires_human(self) -> None:
        sup = WorkerSupervisor()
        hb_daemon = WorkerHeartbeat(worker_id="d", status="alive")
        sup.check_worker(WorkerType.LOCAL_RUNTIME_DAEMON, hb_daemon)
        sup.check_worker(WorkerType.WINDOWS_RELAY)
        plan = sup.plan_startup(WorkerType.WINDOWS_RELAY)
        assert plan.autostart_decision == AutostartDecision.REQUIRES_HUMAN

    def test_blocked_dependency(self) -> None:
        sup = WorkerSupervisor()
        sup.check_worker(WorkerType.DRIVE_ADAPTER)
        plan = sup.plan_startup(WorkerType.DRIVE_ADAPTER)
        assert plan.autostart_decision == AutostartDecision.BLOCKED_DEPENDENCY
        assert plan.recovery_action == RecoveryAction.WAIT_DEPENDENCY

    def test_autostart_disabled(self) -> None:
        sup = WorkerSupervisor(autostart_workers=False)
        sup.check_worker(WorkerType.LOCAL_RUNTIME_DAEMON)
        plan = sup.plan_startup(WorkerType.LOCAL_RUNTIME_DAEMON)
        assert plan.autostart_decision == AutostartDecision.BLOCKED_CONFIG


class TestWorkerRecovery:
    def test_autostart_recovery(self) -> None:
        sup = WorkerSupervisor()
        sup.check_worker(WorkerType.LOCAL_RUNTIME_DAEMON)
        result = sup.attempt_recovery(WorkerType.LOCAL_RUNTIME_DAEMON, trace_id="T1")
        assert result.success is True
        assert result.action_taken == RecoveryAction.AUTOSTART
        assert result.new_status == WorkerHealthStatus.HEALTHY

    def test_escalation_recovery(self) -> None:
        sup = WorkerSupervisor()
        hb = WorkerHeartbeat(worker_id="d", status="alive")
        sup.check_worker(WorkerType.LOCAL_RUNTIME_DAEMON, hb)
        hb2 = WorkerHeartbeat(worker_id="r", status="alive")
        sup.check_worker(WorkerType.WINDOWS_RELAY, hb2)
        sup.check_worker(WorkerType.CHROME_BROWSER)
        result = sup.attempt_recovery(WorkerType.CHROME_BROWSER)
        assert result.success is False
        assert result.action_taken == RecoveryAction.ESCALATE_TO_FOUNDER

    def test_already_healthy_recovery(self) -> None:
        sup = WorkerSupervisor()
        hb = WorkerHeartbeat(worker_id="d", status="alive")
        sup.check_worker(WorkerType.LOCAL_RUNTIME_DAEMON, hb)
        result = sup.attempt_recovery(WorkerType.LOCAL_RUNTIME_DAEMON)
        assert result.success is True
        assert result.action_taken == RecoveryAction.NO_ACTION


class TestWorkerDependencies:
    def test_daemon_has_no_deps(self) -> None:
        assert WORKER_DEPENDENCIES[WorkerType.LOCAL_RUNTIME_DAEMON] == []

    def test_drive_adapter_needs_chrome(self) -> None:
        assert WorkerType.CHROME_BROWSER in WORKER_DEPENDENCIES[WorkerType.DRIVE_ADAPTER]

    def test_chrome_needs_relay(self) -> None:
        assert WorkerType.WINDOWS_RELAY in WORKER_DEPENDENCIES[WorkerType.CHROME_BROWSER]

    def test_relay_needs_daemon(self) -> None:
        assert WorkerType.LOCAL_RUNTIME_DAEMON in WORKER_DEPENDENCIES[WorkerType.WINDOWS_RELAY]


class TestRemediationReport:
    def test_report_structure(self) -> None:
        sup = WorkerSupervisor()
        report = sup.get_remediation_report()
        assert "total_workers" in report
        assert "healthy" in report
        assert "unhealthy" in report
        assert "blocked_startups" in report
        assert "all_checks" in report
        assert report["total_workers"] == len(WorkerType)

    def test_all_workers_checked(self) -> None:
        sup = WorkerSupervisor()
        checks = sup.check_all_workers()
        assert len(checks) == len(WorkerType)


class TestStaleWorkerDetection:
    def test_no_heartbeat_is_unknown(self) -> None:
        sup = WorkerSupervisor()
        check = sup.check_worker(WorkerType.DISCORD_ADAPTER)
        assert check.status == WorkerHealthStatus.UNKNOWN

    def test_pre_populated_statuses(self) -> None:
        sup = WorkerSupervisor(
            worker_statuses={
                "local_runtime_daemon": WorkerHealthStatus.HEALTHY,
                "discord_adapter": WorkerHealthStatus.STOPPED,
            }
        )
        checks = sup.check_all_workers()
        assert checks["local_runtime_daemon"].status == WorkerHealthStatus.HEALTHY
        assert checks["discord_adapter"].status == WorkerHealthStatus.STOPPED


class TestAutoStartPolicy:
    def test_daemon_is_autostart_allowed(self) -> None:
        assert WorkerType.LOCAL_RUNTIME_DAEMON in AUTOSTART_ALLOWED_WORKERS

    def test_discord_is_autostart_allowed(self) -> None:
        assert WorkerType.DISCORD_ADAPTER in AUTOSTART_ALLOWED_WORKERS

    def test_chrome_requires_human(self) -> None:
        assert WorkerType.CHROME_BROWSER in REQUIRES_HUMAN_CONFIRMATION

    def test_relay_requires_human(self) -> None:
        assert WorkerType.WINDOWS_RELAY in REQUIRES_HUMAN_CONFIRMATION

    def test_drive_adapter_not_autostart(self) -> None:
        assert WorkerType.DRIVE_ADAPTER not in AUTOSTART_ALLOWED_WORKERS

    def test_docs_adapter_not_autostart(self) -> None:
        assert WorkerType.DOCS_ADAPTER not in AUTOSTART_ALLOWED_WORKERS
