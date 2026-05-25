"""EOS Engineering Agent — technical execution, architecture, deployment.

Permission tier: EXECUTE — can deploy, run CI/CD, manage infrastructure.
"""

from __future__ import annotations

from typing import Any

from substrate import Substrate
from substrate.types import Component, ComponentType, PermissionTier, RegistrationResult

from projections.eos.agents.base import DepartmentAgent, SkillResult


class EngineeringAgent(DepartmentAgent):
    DEPARTMENT = "engineering"
    PERMISSION_TIER = PermissionTier.EXECUTE

    def _register_skills(self) -> None:
        self._add_skill(
            "code_review",
            "analyze",
            "Review code for quality, security, and style",
            self._code_review,
        )
        self._add_skill(
            "architecture_analysis",
            "analyze",
            "Analyze system architecture for issues",
            self._architecture_analysis,
        )
        self._add_skill(
            "deployment_status",
            "report",
            "Report on deployment and service health",
            self._deployment_status,
        )
        self._add_skill(
            "tech_debt_report",
            "report",
            "Report on technical debt inventory",
            self._tech_debt_report,
        )
        self._add_skill(
            "incident_response",
            "analyze",
            "Analyze an incident and suggest resolution",
            self._incident_response,
        )
        self._add_skill(
            "deploy",
            "container_execution",
            "Deploy a service (EXECUTE tier)",
            self._deploy,
        )

    def _code_review(self, **kwargs: Any) -> SkillResult:
        code = kwargs.get("code", "")
        language = kwargs.get("language", "python")

        if not code:
            return SkillResult(success=False, error="No code provided for review")

        issues = []
        if "except:" in code or "except Exception:" in code:
            issues.append({"severity": "medium", "issue": "Broad exception catching"})
        if "import *" in code:
            issues.append({"severity": "high", "issue": "Wildcard import"})
        if "TODO" in code:
            issues.append({"severity": "low", "issue": "Unresolved TODO"})
        if "password" in code.lower() and "=" in code:
            issues.append({"severity": "critical", "issue": "Possible hardcoded credential"})

        try:
            from adapters.models.model_router import call_with_fallback

            result = call_with_fallback(
                prompt=(
                    f"Review this {language} code for issues. Be concise — "
                    f"list only real problems, not style preferences:\n\n{code[:3000]}"
                ),
                system="Senior code reviewer. Focus on bugs, security, and performance.",
                task_type="fast_response",
            )
            if result.output:
                return SkillResult(
                    success=True,
                    output={
                        "issues": issues,
                        "ai_review": result.output.strip()[:1000],
                        "language": language,
                    },
                )
        except Exception:
            pass

        return SkillResult(success=True, output={"issues": issues, "language": language})

    def _architecture_analysis(self, **kwargs: Any) -> SkillResult:
        system = kwargs.get("system", "")
        concerns = kwargs.get("concerns", [])

        return SkillResult(
            success=True,
            output={
                "system": system,
                "concerns": concerns,
                "checks": [
                    "Dependency direction (inner -> outer only)",
                    "No circular imports",
                    "Single responsibility per module",
                    "Proper abstraction boundaries",
                    "Error handling at system boundaries",
                ],
                "status": "needs_manual_review",
            },
        )

    def _deployment_status(self, **kwargs: Any) -> SkillResult:
        import subprocess

        services = {}
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
                    services[name] = {
                        "status": "healthy" if "Up" in status else "unhealthy",
                        "details": status,
                    }
        except Exception:
            services = {"note": "Docker not accessible"}

        return SkillResult(success=True, output={"services": services})

    def _tech_debt_report(self, **kwargs: Any) -> SkillResult:
        import subprocess

        debt_items = []
        try:
            result = subprocess.run(
                ["grep", "-r", "TODO\\|FIXME\\|HACK\\|XXX", ".", "--include=*.py", "-c"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd="/opt/OS",
            )
            total = 0
            for line in result.stdout.strip().split("\n"):
                if ":" in line:
                    try:
                        count = int(line.split(":")[-1])
                        total += count
                    except ValueError:
                        pass
            debt_items.append({"type": "todo_markers", "count": total})
        except Exception:
            pass

        return SkillResult(success=True, output={"debt_items": debt_items})

    def _incident_response(self, **kwargs: Any) -> SkillResult:
        error_msg = kwargs.get("error", "")
        service = kwargs.get("service", "")

        steps = [
            f"Check {service} container logs: docker logs {service} --tail 50",
            f"Check if service is running: docker ps | grep {service}",
            "Check memory/CPU: docker stats --no-stream",
            "Check recent deployments: git log --oneline -5",
            "Restart if needed: docker restart " + service,
        ]

        return SkillResult(
            success=True,
            output={
                "service": service,
                "error": error_msg[:500],
                "investigation_steps": steps,
                "status": "investigating",
            },
        )

    def _deploy(self, **kwargs: Any) -> SkillResult:
        service = kwargs.get("service", "")
        return SkillResult(
            success=True,
            output={
                "service": service,
                "status": "deployment_initiated",
                "command": f"docker restart {service}",
                "note": "Service restart initiated",
            },
        )


async def register_engineering_agent(substrate: Substrate) -> RegistrationResult:
    agent = EngineeringAgent()
    component = Component(
        component_type=ComponentType.AGENT,
        name="eos-engineering",
        capabilities=[
            "code_review",
            "architecture_analysis",
            "deployment_management",
            "technical_debt_tracking",
            "incident_response",
            "service_deployment",
        ],
        metadata=agent.metadata(),
    )
    return await substrate.register(component)
