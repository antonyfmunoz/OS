"""EOS Operations Agent — workflow optimization, process automation, system health.

Permission tier: EXECUTE — can automate processes and manage system operations.
"""

from __future__ import annotations

import subprocess
from typing import Any

from substrate import Substrate
from substrate.types import Component, ComponentType, PermissionTier, RegistrationResult

from projections.eos.agents.base import DepartmentAgent, SkillResult


class OperationsAgent(DepartmentAgent):
    DEPARTMENT = "operations"
    PERMISSION_TIER = PermissionTier.EXECUTE

    def _register_skills(self) -> None:
        self._add_skill(
            "system_health",
            "status_check",
            "Check overall system health",
            self._system_health,
        )
        self._add_skill(
            "workflow_audit",
            "analyze",
            "Audit workflows for bottlenecks and optimization",
            self._workflow_audit,
        )
        self._add_skill(
            "process_automation",
            "create_task",
            "Identify and draft automation opportunities",
            self._process_automation,
        )
        self._add_skill(
            "resource_allocation",
            "analyze",
            "Analyze resource allocation and utilization",
            self._resource_allocation,
        )
        self._add_skill(
            "bottleneck_detection",
            "analyze",
            "Detect operational bottlenecks",
            self._bottleneck_detection,
        )
        self._add_skill(
            "ops_report",
            "report",
            "Generate operational summary report",
            self._ops_report,
        )

    def _system_health(self, **kwargs: Any) -> SkillResult:
        health: dict[str, Any] = {"services": {}, "resources": {}}

        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            for line in result.stdout.strip().split("\n"):
                if "\t" in line:
                    name, status = line.split("\t", 1)
                    health["services"][name] = "up" if "Up" in status else "down"
        except Exception:
            health["services"]["note"] = "Docker not accessible"

        try:
            result = subprocess.run(
                ["df", "-h", "/opt/OS"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            lines = result.stdout.strip().split("\n")
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) >= 5:
                    health["resources"]["disk_usage"] = parts[4]
                    health["resources"]["disk_available"] = parts[3]
        except Exception:
            pass

        return SkillResult(success=True, output=health)

    def _workflow_audit(self, **kwargs: Any) -> SkillResult:
        workflow = kwargs.get("workflow", "")
        return SkillResult(
            success=True,
            output={
                "workflow": workflow,
                "audit_checks": [
                    "Step count and redundancy",
                    "Average completion time",
                    "Failure points and retry rates",
                    "Automation coverage",
                    "Human intervention frequency",
                ],
                "status": "needs_data",
            },
        )

    def _process_automation(self, **kwargs: Any) -> SkillResult:
        process = kwargs.get("process", "")
        current_steps = kwargs.get("steps", [])

        automatable = []
        manual = []
        for step in current_steps:
            name = step if isinstance(step, str) else step.get("name", "")
            if any(kw in name.lower() for kw in ["copy", "transfer", "notify", "update", "sync"]):
                automatable.append(name)
            else:
                manual.append(name)

        return SkillResult(
            success=True,
            output={
                "process": process,
                "automatable_steps": automatable,
                "manual_steps": manual,
                "automation_potential": (
                    f"{len(automatable)}/{len(current_steps)} steps automatable"
                    if current_steps
                    else "No steps provided"
                ),
                "status": "draft",
            },
        )

    def _resource_allocation(self, **kwargs: Any) -> SkillResult:
        try:
            result = subprocess.run(
                [
                    "docker",
                    "stats",
                    "--no-stream",
                    "--format",
                    "{{.Name}}\t{{.CPUPerc}}\t{{.MemPerc}}\t{{.MemUsage}}",
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
            containers = []
            for line in result.stdout.strip().split("\n"):
                parts = line.split("\t")
                if len(parts) >= 4:
                    containers.append(
                        {
                            "name": parts[0],
                            "cpu": parts[1],
                            "memory_pct": parts[2],
                            "memory_usage": parts[3],
                        }
                    )
            return SkillResult(success=True, output={"containers": containers})
        except Exception:
            return SkillResult(
                success=True, output={"containers": [], "note": "Docker stats unavailable"}
            )

    def _bottleneck_detection(self, **kwargs: Any) -> SkillResult:
        try:
            from substrate import get_conn

            with get_conn(self._org_id) as cur:
                cur.execute(
                    """
                    SELECT event_type,
                           COUNT(*) as count,
                           AVG(EXTRACT(EPOCH FROM (
                               (payload_json->>'completed_at')::timestamp -
                               created_at
                           ))) as avg_duration_seconds
                    FROM events
                    WHERE org_id = %s
                    AND payload_json->>'completed_at' IS NOT NULL
                    AND created_at >= NOW() - INTERVAL '7 days'
                    GROUP BY event_type
                    HAVING AVG(EXTRACT(EPOCH FROM (
                        (payload_json->>'completed_at')::timestamp -
                        created_at
                    ))) > 3600
                    ORDER BY avg_duration_seconds DESC
                    LIMIT 10
                    """,
                    (self._org_id,),
                )
                rows = cur.fetchall()
                bottlenecks = [
                    {
                        "event_type": r["event_type"],
                        "count": r["count"],
                        "avg_hours": round(float(r["avg_duration_seconds"]) / 3600, 1),
                    }
                    for r in rows
                ]
                return SkillResult(
                    success=True,
                    output={"bottlenecks": bottlenecks},
                )
        except Exception:
            return SkillResult(success=True, output={"bottlenecks": []})

    def _ops_report(self, **kwargs: Any) -> SkillResult:
        health_result = self._system_health()
        resource_result = self._resource_allocation()

        return SkillResult(
            success=True,
            output={
                "system_health": health_result.output,
                "resources": resource_result.output,
                "report_type": "operational_summary",
            },
        )


async def register_operations_agent(substrate: Substrate) -> RegistrationResult:
    agent = OperationsAgent()
    component = Component(
        component_type=ComponentType.AGENT,
        name="eos-operations",
        capabilities=[
            "workflow_optimization",
            "process_automation",
            "system_monitoring",
            "bottleneck_detection",
            "resource_allocation",
            "operational_reporting",
        ],
        metadata=agent.metadata(),
    )
    return await substrate.register(component)
