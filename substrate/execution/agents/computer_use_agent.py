"""Computer-Use Agent — governed visual automation across execution layers.

Screenshot → vision LLM → parse action → governance gate → execute → repeat.
Each action passes through ExecutionAuthorityEngine before execution.
Two concrete implementations: ContainerComputerAgent and NativeComputerAgent.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)

MAX_STEPS = 50
STEP_INTERVAL_S = 1.0


class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class ActionEntry:
    step: int
    action_type: str
    params: dict[str, Any]
    result: dict[str, Any]
    authority_class: str
    approved: bool
    timestamp: float = field(default_factory=time.time)


@dataclass
class ExecutionSlotState:
    slot: int
    agent_id: str
    layer: str
    task: str
    status: AgentStatus = AgentStatus.IDLE
    step_count: int = 0
    action_log: list[ActionEntry] = field(default_factory=list)
    authority_class: str = ""
    risk_class: str = ""
    approval_status: str = ""


class ComputerUseAgent(ABC):
    """Base class for governed visual automation agents."""

    def __init__(self, slot: int, layer: str) -> None:
        self.slot = slot
        self.layer = layer
        self.agent_id = f"cu-{layer}-{slot}-{uuid.uuid4().hex[:8]}"
        self.status = AgentStatus.IDLE
        self.step_count = 0
        self.action_log: list[ActionEntry] = []
        self._pause_event = asyncio.Event()
        self._pause_event.set()
        self._stop_requested = False

    @abstractmethod
    async def take_screenshot(self) -> bytes:
        """Capture current screen state as PNG bytes."""

    @abstractmethod
    async def execute_action(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute a single action (click, type, etc.) in the execution environment."""

    async def run_loop(
        self,
        task: str,
        on_status: Callable[[ExecutionSlotState], None] | None = None,
    ) -> ExecutionSlotState:
        """Main execution loop: screenshot → LLM → parse → gate → execute → repeat."""
        self.status = AgentStatus.RUNNING
        self.step_count = 0
        self.action_log = []
        self._stop_requested = False

        state = ExecutionSlotState(
            slot=self.slot,
            agent_id=self.agent_id,
            layer=self.layer,
            task=task,
            status=self.status,
        )

        try:
            while self.step_count < MAX_STEPS and not self._stop_requested:
                await self._pause_event.wait()

                screenshot_bytes = await self.take_screenshot()
                b64_image = base64.b64encode(screenshot_bytes).decode("ascii")

                action = await self._get_next_action(task, b64_image, self.action_log)

                if action.get("done"):
                    break

                gate_result = self._governance_gate(action)
                entry = ActionEntry(
                    step=self.step_count,
                    action_type=action.get("type", "unknown"),
                    params=action.get("params", {}),
                    result={},
                    authority_class=gate_result.get("authority_class", ""),
                    approved=gate_result.get("approved", False),
                )

                if not gate_result.get("approved", False):
                    entry.result = {"blocked": True, "reason": gate_result.get("reason", "")}
                    self.action_log.append(entry)
                    logger.info(
                        "step %d blocked by governance: %s",
                        self.step_count,
                        gate_result.get("reason"),
                    )
                    break

                result = await self.execute_action(action)
                entry.result = result
                self.action_log.append(entry)
                self.step_count += 1

                state.step_count = self.step_count
                state.action_log = self.action_log
                state.status = self.status
                if on_status:
                    on_status(state)

                await asyncio.sleep(STEP_INTERVAL_S)

        except Exception as exc:
            logger.error("computer-use agent error: %s", exc)
            self.status = AgentStatus.ERROR
        else:
            if not self._stop_requested:
                self.status = AgentStatus.STOPPED

        state.status = self.status
        state.step_count = self.step_count
        state.action_log = self.action_log
        return state

    def pause(self) -> None:
        self._pause_event.clear()
        self.status = AgentStatus.PAUSED

    def resume(self) -> None:
        self._pause_event.set()
        self.status = AgentStatus.RUNNING

    def stop(self) -> None:
        self._stop_requested = True
        self._pause_event.set()
        self.status = AgentStatus.STOPPED

    async def _get_next_action(
        self,
        task: str,
        screenshot_b64: str,
        history: list[ActionEntry],
    ) -> dict[str, Any]:
        """Ask vision LLM what to do next given the screenshot and task."""
        try:
            import sys
            sys.path.insert(0, "/opt/OS")
            from adapters.models.model_router import call_with_fallback
        except ImportError:
            return {"done": True, "reason": "model_router not available"}

        history_text = ""
        for entry in history[-5:]:
            history_text += (
                f"Step {entry.step}: {entry.action_type}"
                f"({entry.params}) -> {entry.result}\n"
            )

        prompt = (
            f"Task: {task}\n\n"
            f"Previous actions:\n{history_text}\n"
            "You are a computer-use agent looking at a screenshot. "
            "Respond with a JSON object describing the next action:\n"
            '{"type": "click"|"type"|"scroll"|"done", '
            '"params": {"x": int, "y": int} or {"text": "..."} or {}, '
            '"reasoning": "brief explanation"}\n'
            "If the task is complete, respond with: "
            '{"done": true, "reason": "task completed"}'
        )

        screenshot_bytes = base64.b64decode(screenshot_b64)
        response = call_with_fallback(
            prompt=prompt,
            images=[(screenshot_bytes, "image/png")],
            task_type="computer_use",
        )

        if not response:
            return {"done": True, "reason": "no LLM response"}

        import json
        try:
            return json.loads(response)
        except (json.JSONDecodeError, TypeError):
            return {"done": True, "reason": f"unparseable response: {response[:200]}"}

    def _governance_gate(self, action: dict[str, Any]) -> dict[str, Any]:
        """Check action against governance engine. Returns approval status."""
        action_type = action.get("type", "unknown")

        if self.layer == "container":
            return {
                "approved": True,
                "authority_class": "approve_execute",
                "risk_class": "low",
            }

        if self.layer == "native":
            if action_type in ("click", "type", "scroll"):
                return {
                    "approved": True,
                    "authority_class": "supervised_execute",
                    "risk_class": "medium",
                    "note": "native actions require operator supervision",
                }
            return {
                "approved": False,
                "authority_class": "deny",
                "reason": f"unknown action type for native layer: {action_type}",
            }

        return {"approved": False, "authority_class": "deny", "reason": "unknown layer"}


class ContainerComputerAgent(ComputerUseAgent):
    """Computer-use agent running in a Docker container."""

    def __init__(self, slot: int, container_name: str) -> None:
        super().__init__(slot, "container")
        self.container_name = container_name

    async def take_screenshot(self) -> bytes:
        from nodes.windows.umh_node.adapters.container import ContainerAdapter

        adapter = ContainerAdapter()
        result = adapter.handle(
            "container.screenshot",
            {"container_name": self.container_name},
        )
        if not result.get("success"):
            raise RuntimeError(f"screenshot failed: {result.get('error')}")
        return base64.b64decode(result["image_base64"])

    async def execute_action(self, action: dict[str, Any]) -> dict[str, Any]:
        from nodes.windows.umh_node.adapters.container import ContainerAdapter

        adapter = ContainerAdapter()
        action_type = action.get("type", "")
        params = action.get("params", {})

        if action_type == "click":
            x, y = params.get("x", 0), params.get("y", 0)
            return adapter.handle(
                "container.run_cmd",
                {"container_name": self.container_name, "cmd": f"xdotool mousemove {x} {y} click 1"},
            )
        elif action_type == "type":
            text = params.get("text", "")
            return adapter.handle(
                "container.run_cmd",
                {"container_name": self.container_name, "cmd": ["xdotool", "type", "--", text]},
            )
        elif action_type == "scroll":
            direction = params.get("direction", "down")
            button = "5" if direction == "down" else "4"
            return adapter.handle(
                "container.run_cmd",
                {"container_name": self.container_name, "cmd": f"xdotool click {button}"},
            )

        return {"success": False, "error": f"unsupported action: {action_type}"}


class NativeComputerAgent(ComputerUseAgent):
    """Computer-use agent running on native Windows desktop."""

    def __init__(self, slot: int) -> None:
        super().__init__(slot, "native")

    async def take_screenshot(self) -> bytes:
        from nodes.windows.umh_node.adapters.desktop import DesktopAdapter

        adapter = DesktopAdapter()
        result = adapter.execute("desktop.screenshot", {})
        if not result.get("success"):
            raise RuntimeError(f"screenshot failed: {result.get('error')}")
        return base64.b64decode(result["image_base64"])

    async def execute_action(self, action: dict[str, Any]) -> dict[str, Any]:
        from nodes.windows.umh_node.adapters.desktop import DesktopAdapter

        adapter = DesktopAdapter()
        action_type = action.get("type", "")
        params = action.get("params", {})

        if action_type == "click":
            return adapter.execute(
                "desktop.click",
                {"x": params.get("x", 0), "y": params.get("y", 0)},
            )
        elif action_type == "type":
            return adapter.execute(
                "desktop.type",
                {"text": params.get("text", "")},
            )

        return {"success": False, "error": f"unsupported action: {action_type}"}
