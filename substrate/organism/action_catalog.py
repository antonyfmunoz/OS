"""Action Catalog — data-driven registry of governed operator actions.

Actions are data, not code. Each ActionDefinition specifies a command
template, risk level, preconditions, and parameter schema. Adding a
new action means registering a definition, not writing Python.

UMH substrate subsystem. Domain-agnostic.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ActionRiskLevel(str, Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionCategory(str, Enum):
    CONTAINER = "container"
    SERVICE = "service"
    BUILD = "build"
    TEST = "test"
    WORKSPACE = "workspace"
    OBSERVATION = "observation"


class ActionStatus(str, Enum):
    PENDING = "pending"
    PRECONDITION_CHECK = "precondition_check"
    AWAITING_APPROVAL = "awaiting_approval"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class ActionParameter:
    name: str
    param_type: str = "string"
    required: bool = True
    default: str = ""
    choices: list[str] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "param_type": self.param_type,
            "required": self.required,
            "default": self.default,
            "choices": self.choices,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ActionParameter:
        known = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class ActionPrecondition:
    check_type: str
    target: str = ""
    expected: bool = True
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_type": self.check_type,
            "target": self.target,
            "expected": self.expected,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ActionPrecondition:
        known = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class ActionDefinition:
    action_id: str
    name: str
    description: str
    category: str
    risk_level: str
    executor_type: str = "workstation"
    operation: str = "run_command"
    command_template: str = ""
    parameters: list[ActionParameter] = field(default_factory=list)
    preconditions: list[ActionPrecondition] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "risk_level": self.risk_level,
            "executor_type": self.executor_type,
            "operation": self.operation,
            "command_template": self.command_template,
            "parameters": [p.to_dict() for p in self.parameters],
            "preconditions": [p.to_dict() for p in self.preconditions],
            "tags": self.tags,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ActionDefinition:
        d = dict(data)
        if "parameters" in d:
            d["parameters"] = [ActionParameter.from_dict(p) for p in d["parameters"]]
        if "preconditions" in d:
            d["preconditions"] = [ActionPrecondition.from_dict(p) for p in d["preconditions"]]
        known = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in d.items() if k in known})


class ActionCatalog:
    """Data-driven registry of governed actions.

    Deterministic keyword matching — no LLM calls.
    """

    def __init__(self) -> None:
        self._actions: dict[str, ActionDefinition] = {}
        self._seed_defaults()

    def resolve(self, text: str) -> ActionDefinition | None:
        """Match operator text against action IDs and tags."""
        normalized = text.lower().strip()
        for action in self._actions.values():
            if not action.enabled:
                continue
            if action.action_id in normalized:
                return action
            for tag in action.tags:
                if tag in normalized:
                    return action
        return None

    def resolve_by_id(self, action_id: str) -> ActionDefinition | None:
        action = self._actions.get(action_id)
        if action and action.enabled:
            return action
        return None

    def list_actions(
        self, category: str | None = None, enabled_only: bool = True
    ) -> list[ActionDefinition]:
        results = []
        for action in self._actions.values():
            if enabled_only and not action.enabled:
                continue
            if category and action.category != category:
                continue
            results.append(action)
        return results

    def register(self, action: ActionDefinition) -> None:
        self._actions[action.action_id] = action
        logger.debug("Registered action: %s", action.action_id)

    def _seed_defaults(self) -> None:
        defaults = [
            ActionDefinition(
                action_id="list_containers",
                name="List Containers",
                description="Show all Docker containers with status",
                category=ActionCategory.OBSERVATION.value,
                risk_level=ActionRiskLevel.SAFE.value,
                command_template="docker ps -a --format '{{.Names}}\t{{.Status}}'",
                tags=["docker", "containers", "list", "ps"],
            ),
            ActionDefinition(
                action_id="container_logs",
                name="Container Logs",
                description="Show recent logs for a container",
                category=ActionCategory.OBSERVATION.value,
                risk_level=ActionRiskLevel.SAFE.value,
                command_template="docker logs --tail {lines} {container_name}",
                parameters=[
                    ActionParameter(name="container_name", description="Docker container name"),
                    ActionParameter(
                        name="lines",
                        param_type="integer",
                        required=False,
                        default="50",
                        description="Number of log lines",
                    ),
                ],
                preconditions=[
                    ActionPrecondition(
                        check_type="container_exists",
                        description="Container must exist",
                    ),
                ],
                tags=["docker", "logs", "container logs"],
            ),
            ActionDefinition(
                action_id="service_health",
                name="Service Health",
                description="Check health status of a Docker container",
                category=ActionCategory.OBSERVATION.value,
                risk_level=ActionRiskLevel.SAFE.value,
                command_template=(
                    "docker inspect --format='{{.State.Health.Status}}' {container_name}"
                ),
                parameters=[
                    ActionParameter(name="container_name", description="Docker container name"),
                ],
                preconditions=[
                    ActionPrecondition(
                        check_type="container_exists",
                        description="Container must exist",
                    ),
                ],
                tags=["health", "docker", "inspect", "service health"],
            ),
            ActionDefinition(
                action_id="run_tests",
                name="Run Tests",
                description="Run pytest on a test file or directory",
                category=ActionCategory.TEST.value,
                risk_level=ActionRiskLevel.LOW.value,
                command_template="python3 -m pytest {test_path} -x",
                parameters=[
                    ActionParameter(
                        name="test_path",
                        required=False,
                        default="tests/",
                        description="Test file or directory path",
                    ),
                ],
                tags=["test", "pytest", "run tests"],
            ),
            ActionDefinition(
                action_id="run_lint",
                name="Run Lint",
                description="Run ruff linter on target path",
                category=ActionCategory.TEST.value,
                risk_level=ActionRiskLevel.SAFE.value,
                command_template="ruff check {target_path}",
                parameters=[
                    ActionParameter(
                        name="target_path",
                        required=False,
                        default=".",
                        description="Path to lint",
                    ),
                ],
                tags=["lint", "ruff", "check"],
            ),
            ActionDefinition(
                action_id="git_status",
                name="Git Status",
                description="Show git working tree status",
                category=ActionCategory.OBSERVATION.value,
                risk_level=ActionRiskLevel.SAFE.value,
                command_template="git -C {repo_path} status",
                parameters=[
                    ActionParameter(
                        name="repo_path",
                        required=False,
                        default="/opt/OS",
                        description="Repository root path",
                    ),
                ],
                tags=["git", "status"],
            ),
            ActionDefinition(
                action_id="restart_container",
                name="Restart Container",
                description="Restart a Docker container (requires approval)",
                category=ActionCategory.CONTAINER.value,
                risk_level=ActionRiskLevel.MEDIUM.value,
                command_template="docker restart {container_name}",
                parameters=[
                    ActionParameter(name="container_name", description="Docker container name"),
                ],
                preconditions=[
                    ActionPrecondition(
                        check_type="container_running",
                        description="Container must be running",
                    ),
                ],
                tags=["docker", "restart", "container"],
            ),
        ]
        for action in defaults:
            self.register(action)
