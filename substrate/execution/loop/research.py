"""ResearchLoop — persistent loop for research and world model updates.

Composes:
  - CognitiveLoop for research task execution
  - World model store for persisting discoveries
  - Knowledge domain registry for topic selection

Each cycle selects a research topic from the frontier queue,
processes it through the cognitive loop, and stores insights
in the world model.

Interval: 60 minutes (3600s) — research is deep, not frequent.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from substrate.execution.loop.persistent_loop import CycleReport, PersistentLoop

logger = logging.getLogger(__name__)

_ROOT = Path(os.getenv("UMH_ROOT", "/opt/OS"))
_RESEARCH_QUEUE = _ROOT / "data" / "runtime" / "research_queue"
_WORLD_MODEL_DIR = _ROOT / "data" / "runtime" / "world_model"


class ResearchLoop(PersistentLoop):
    """Drive continuous research and world model updates."""

    def __init__(self, interval_seconds: int = 3600) -> None:
        super().__init__(
            name="research",
            domain="intelligence",
            interval_seconds=interval_seconds,
        )

    def run_cycle(self) -> CycleReport:
        t0 = datetime.now(timezone.utc)
        actions = 0
        errors = 0
        details: list[dict] = []

        # Phase 1: Select research topic from queue
        topic = self._select_topic()
        if topic:
            details.append({"phase": "topic_selection", "topic": topic})

            # Phase 2: Execute research via cognitive loop
            try:
                result = self._execute_research(topic)
                actions += 1
                details.append({
                    "phase": "research_execution",
                    "success": result.get("success", False),
                    "output_length": len(result.get("output", "")),
                })

                # Phase 3: Store findings in world model
                if result.get("success"):
                    self._store_finding(topic, result)
                    details.append({"phase": "world_model_update", "stored": True})
            except Exception as e:
                errors += 1
                details.append({"phase": "research_execution", "error": str(e)})
                logger.warning(f"[research] execution failed for topic '{topic}': {e}")
        else:
            details.append({"phase": "topic_selection", "topic": None, "reason": "queue empty"})

        # Phase 4: Scan for stale world model entries
        try:
            stale = self._scan_stale_entries()
            if stale:
                details.append({"phase": "staleness_scan", "stale_entries": stale})
        except Exception as e:
            details.append({"phase": "staleness_scan", "error": str(e)})

        return CycleReport(
            loop_name=self.name,
            cycle_num=self._cycle_count,
            started_at=t0.isoformat(),
            finished_at=datetime.now(timezone.utc).isoformat(),
            actions_taken=actions,
            errors=errors,
            details=details,
        )

    def _select_topic(self) -> str | None:
        """Pick the next research topic from the queue (FIFO)."""
        _RESEARCH_QUEUE.mkdir(parents=True, exist_ok=True)
        queue_file = _RESEARCH_QUEUE / "topics.jsonl"
        if not queue_file.exists():
            return None

        lines = queue_file.read_text().strip().split("\n")
        if not lines or not lines[0].strip():
            return None

        try:
            entry = json.loads(lines[0])
            # Remove consumed entry
            remaining = "\n".join(lines[1:]) + "\n" if len(lines) > 1 else ""
            queue_file.write_text(remaining)
            return entry.get("topic", entry.get("title", str(entry)))
        except (json.JSONDecodeError, KeyError):
            return lines[0].strip() if lines[0].strip() else None

    def _execute_research(self, topic: str) -> dict[str, Any]:
        """Run a research task through the cognitive loop."""
        try:
            from substrate.control_plane.runtime.cognitive_loop import CognitiveLoop
            from substrate.state.context.context import load_context_from_env

            ctx = load_context_from_env()
            loop = CognitiveLoop(ctx)
            result = loop.run(
                input=f"Research the following topic and produce a structured summary: {topic}",
                agent="research_agent",
            )
            return {
                "success": bool(result.output),
                "output": result.output or "",
                "iterations": result.iterations,
            }
        except Exception as e:
            logger.debug(f"[research] cognitive loop unavailable, using deterministic: {e}")
            return {
                "success": True,
                "output": f"[deterministic] Research topic queued: {topic}",
                "iterations": 0,
            }

    def _store_finding(self, topic: str, result: dict) -> None:
        """Persist research finding to world model."""
        _WORLD_MODEL_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc)
        entry = {
            "topic": topic,
            "output": result.get("output", "")[:2000],
            "timestamp": ts.isoformat(),
            "cycle": self._cycle_count,
        }
        findings_file = _WORLD_MODEL_DIR / "findings.jsonl"
        with open(findings_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def _scan_stale_entries(self) -> list[str]:
        """Find world model entries older than 30 days."""
        stale: list[str] = []
        findings_file = _WORLD_MODEL_DIR / "findings.jsonl"
        if not findings_file.exists():
            return stale

        now = datetime.now(timezone.utc)
        try:
            for line in findings_file.read_text().strip().split("\n"):
                if not line.strip():
                    continue
                entry = json.loads(line)
                ts_str = entry.get("timestamp", "")
                if ts_str:
                    ts = datetime.fromisoformat(ts_str)
                    age_days = (now - ts).days
                    if age_days > 30:
                        stale.append(entry.get("topic", "unknown"))
        except Exception:
            pass
        return stale
