#!/usr/bin/env python3
"""action_system.py — Controlled execution layer on top of the EOS cognition stack.

Sits between the AI (which proposes actions) and the filesystem / shell
(which executes them). Every action goes through the same pipeline:

    propose → assess_impact (graph) → evaluate_risk → approval gate
           → (dry_run | execute) → log → refresh graph → result

The primary graph is the source of truth for "what depends on this?", so
the action system reuses scripts.query_graph.GraphQuery directly rather
than reinventing impact analysis. After a mutation, the action system
calls scripts.incremental_graph.update so the cognition stack reconverges
without a full rebuild.

Audit trail:
  - data/action_log.jsonl      — local append-only JSONL, authoritative
  - data/action_snapshots/<id> — pre-mutation file snapshots for rollback
  - eos_ai.memory.AgentMemory  — best-effort Neon log_event call, never
                                  blocks or fails the action

CLI
---
    python3 scripts/action_system.py query-graph --target eos_ai/memory.py
    python3 scripts/action_system.py edit-file \\
        --target eos_ai/memory.py --payload-file /tmp/new.py --dry-run
    python3 scripts/action_system.py edit-file \\
        --target eos_ai/memory.py --payload-file /tmp/new.py --approve
    python3 scripts/action_system.py run-command --payload "ls -la" --approve
    python3 scripts/action_system.py history --limit 20
    python3 scripts/action_system.py rollback <action_id>

Python API
----------
    from scripts.action_system import ActionSystem, ActionType
    sys = ActionSystem()
    action = sys.propose(
        action_type=ActionType.EDIT_FILE,
        target="eos_ai/memory.py",
        payload={"content": new_text},
        reason="fix typo in docstring",
    )
    impact = sys.assess_impact(action)
    result = sys.execute(action, dry_run=False, approve=True)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

sys.path.insert(0, "/opt/OS")

# Reuse the existing cognition stack — do not reinvent.
from scripts.query_graph import GraphQuery  # noqa: E402

ROOT = Path("/opt/OS")
DATA_DIR = ROOT / "data"
LOG_PATH = DATA_DIR / "action_log.jsonl"
SNAPSHOT_DIR = DATA_DIR / "action_snapshots"

# Commands that should be CRITICAL regardless of context. Matched as
# substring on the lowered command string. If a command contains any
# of these tokens, the risk assessor bumps it to CRITICAL.
CRITICAL_COMMAND_MARKERS = (
    "rm -rf /",
    "rm -rf ~",
    "rm -rf *",
    ":(){ :|:& };:",
    "dd if=",
    "mkfs",
    "> /dev/sda",
    "git reset --hard",
    "git push --force",
    "git push -f",
    "drop table",
    "drop database",
    "truncate table",
    "docker system prune",
    "docker rm -f",
    "docker volume rm",
    "chmod -r 000",
    "chown -r",
    "shutdown",
    "reboot",
    "halt",
    "kill -9 1",
)

# Commands that are allowed without approval at the HIGH level default.
# These are read-only inspection commands commonly issued by the AI.
SAFE_COMMAND_PREFIXES = (
    "ls",
    "cat",
    "head",
    "tail",
    "wc",
    "stat",
    "file",
    "pwd",
    "whoami",
    "uname",
    "df",
    "du",
    "free",
    "ps",
    "git status",
    "git log",
    "git diff",
    "git branch",
    "git show",
    "python3 scripts/query_graph.py",
    "python3 scripts/verify_knowledge_system.py",
    "python3 scripts/session_bootstrap.py",
)

# How many top-centrality files count as "critical hubs". Edits that
# touch one of these escalate to HIGH risk regardless of raw
# dependents count.
CRITICAL_HUB_RANK = 20


# ─── Model ──────────────────────────────────────────────────────────────────


class ActionType(str, Enum):
    QUERY_GRAPH = "query_graph"
    EDIT_FILE = "edit_file"
    WRITE_FILE = "write_file"
    DELETE_FILE = "delete_file"
    RUN_SCRIPT = "run_script"
    RUN_COMMAND = "run_command"


class RiskLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def rank(self) -> int:
        return _RISK_RANK[self]


_RISK_RANK = {
    RiskLevel.NONE: 0,
    RiskLevel.LOW: 1,
    RiskLevel.MEDIUM: 2,
    RiskLevel.HIGH: 3,
    RiskLevel.CRITICAL: 4,
}


class ActionStatus(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    SKIPPED_DRY_RUN = "skipped_dry_run"


@dataclass
class Impact:
    """Graph-derived blast radius for a target file."""

    target: str
    in_graph: bool
    direct_dependents: list[str] = field(default_factory=list)
    direct_dependencies: list[str] = field(default_factory=list)
    is_critical_hub: bool = False
    centrality_rank: int | None = None
    notes: list[str] = field(default_factory=list)


@dataclass
class Action:
    """A single proposed or executed action."""

    id: str
    type: ActionType
    target: str
    payload: dict[str, Any]
    reason: str = ""
    dependencies: list[str] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.NONE
    requires_approval: bool = False
    status: ActionStatus = ActionStatus.PROPOSED
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    impact: Impact | None = None


@dataclass
class ActionResult:
    action_id: str
    status: ActionStatus
    output: str = ""
    error: str | None = None
    snapshot_dir: str | None = None
    duration_seconds: float = 0.0
    graph_refresh: dict[str, Any] | None = None


# ─── Core system ────────────────────────────────────────────────────────────


class ActionSystem:
    """Single orchestration surface for propose → assess → execute → log."""

    def __init__(self, *, verbose: bool = False) -> None:
        self.verbose = verbose
        self._graph_query: GraphQuery | None = None
        self._critical_hubs: set[str] | None = None
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

    # ─── Lazy graph layer ──────────────────────────────────────────────────

    def _graph(self) -> GraphQuery:
        if self._graph_query is None:
            self._graph_query = GraphQuery.load()
        return self._graph_query

    def _critical_hub_set(self) -> set[str]:
        if self._critical_hubs is not None:
            return self._critical_hubs
        try:
            ranked = self._graph().centrality(top=CRITICAL_HUB_RANK)
        except Exception as exc:
            if self.verbose:
                print(f"[action] centrality query failed: {exc}")
            self._critical_hubs = set()
            return self._critical_hubs
        # centrality() returns list[tuple[str, int, int]] — (path, inbound, outbound)
        hubs = {row[0] for row in ranked if row}
        self._critical_hubs = hubs
        return hubs

    # ─── Propose ───────────────────────────────────────────────────────────

    def propose(
        self,
        *,
        action_type: ActionType,
        target: str,
        payload: dict[str, Any] | None = None,
        reason: str = "",
    ) -> Action:
        """Create an Action, populate impact + risk, but do NOT execute."""
        action = Action(
            id=_new_id(),
            type=action_type,
            target=target,
            payload=payload or {},
            reason=reason,
        )
        action.impact = self.assess_impact(action)
        action.risk_level = self.evaluate_risk(action)
        action.requires_approval = action.risk_level.rank >= RiskLevel.HIGH.rank
        action.dependencies = (
            action.impact.direct_dependents if action.impact else []
        )
        self._emit_log(action, event="proposed")
        return action

    # ─── Impact ────────────────────────────────────────────────────────────

    def assess_impact(self, action: Action) -> Impact:
        """Use the graph to describe the blast radius of this action.

        For targets that are files in the graph, this returns direct
        dependents and dependencies plus critical-hub flagging. For
        non-file targets (commands, scripts-by-name) it returns an
        empty impact with explanatory notes.
        """
        impact = Impact(target=action.target, in_graph=False)

        if action.type in (ActionType.RUN_COMMAND, ActionType.QUERY_GRAPH):
            impact.notes.append(
                f"{action.type.value} has no file target; impact limited to "
                f"shell/graph side effects"
            )
            return impact

        rel = _rel_to_root(action.target)
        try:
            gq = self._graph()
        except Exception as exc:
            impact.notes.append(f"graph unavailable: {exc}")
            return impact

        # Files are stored under the raw payload, keyed by rel_path.
        files_map = gq.raw.get("files", {})
        if rel not in files_map:
            impact.notes.append(
                f"{rel} is not in the graph — either a new file, untracked "
                f"language, or typo; impact cannot be computed"
            )
            return impact

        impact.in_graph = True
        try:
            impact.direct_dependents = sorted(gq.dependents(rel))
        except Exception as exc:
            impact.notes.append(f"dependents query failed: {exc}")
        try:
            impact.direct_dependencies = sorted(gq.dependencies(rel))
        except Exception as exc:
            impact.notes.append(f"deps query failed: {exc}")

        hubs = self._critical_hub_set()
        if rel in hubs:
            impact.is_critical_hub = True
            try:
                ranked = gq.centrality(top=CRITICAL_HUB_RANK)
                for i, row in enumerate(ranked, start=1):
                    if row and row[0] == rel:
                        impact.centrality_rank = i
                        break
            except Exception:
                pass

        return impact

    # ─── Risk ──────────────────────────────────────────────────────────────

    def evaluate_risk(self, action: Action) -> RiskLevel:
        """Deterministic risk assignment. No LLM, no heuristics that
        require network calls. The rules must be predictable so the
        operator can trust the approval gate."""
        if action.type == ActionType.QUERY_GRAPH:
            return RiskLevel.NONE

        if action.type in (ActionType.EDIT_FILE, ActionType.WRITE_FILE):
            impact = action.impact or self.assess_impact(action)
            if impact.is_critical_hub:
                return RiskLevel.HIGH
            if not impact.in_graph:
                # New file or outside tracked scope — LOW (no blast radius)
                return RiskLevel.LOW
            n = len(impact.direct_dependents)
            if n == 0:
                return RiskLevel.LOW
            if n <= 5:
                return RiskLevel.MEDIUM
            return RiskLevel.HIGH

        if action.type == ActionType.DELETE_FILE:
            impact = action.impact or self.assess_impact(action)
            if impact.is_critical_hub or len(impact.direct_dependents) > 0:
                return RiskLevel.CRITICAL
            return RiskLevel.HIGH

        if action.type == ActionType.RUN_SCRIPT:
            # Script runs are HIGH by default; scripts with destructive
            # markers in their name escalate.
            lowered = action.target.lower()
            if any(m in lowered for m in ("delete", "drop", "wipe", "reset")):
                return RiskLevel.CRITICAL
            return RiskLevel.HIGH

        if action.type == ActionType.RUN_COMMAND:
            cmd = str(action.payload.get("command", "")).lower().strip()
            if not cmd:
                return RiskLevel.LOW
            if any(m in cmd for m in CRITICAL_COMMAND_MARKERS):
                return RiskLevel.CRITICAL
            if cmd.startswith(SAFE_COMMAND_PREFIXES):
                return RiskLevel.LOW
            return RiskLevel.HIGH

        return RiskLevel.HIGH  # unknown types default HIGH, never LOW

    # ─── Execute ───────────────────────────────────────────────────────────

    def execute(
        self,
        action: Action,
        *,
        dry_run: bool = False,
        approve: bool = False,
    ) -> ActionResult:
        """Run the approval gate, then dispatch to the type-specific
        executor. Always logs the outcome — success or failure."""
        start = time.monotonic()

        if action.requires_approval and not approve and not dry_run:
            action.status = ActionStatus.REJECTED
            self._emit_log(action, event="rejected_no_approval")
            return ActionResult(
                action_id=action.id,
                status=ActionStatus.REJECTED,
                error=(
                    f"{action.type.value} with risk={action.risk_level.value} "
                    f"requires --approve; run with --dry-run to preview"
                ),
                duration_seconds=round(time.monotonic() - start, 3),
            )

        if dry_run:
            action.status = ActionStatus.SKIPPED_DRY_RUN
            self._emit_log(action, event="dry_run")
            return ActionResult(
                action_id=action.id,
                status=ActionStatus.SKIPPED_DRY_RUN,
                output=self._preview(action),
                duration_seconds=round(time.monotonic() - start, 3),
            )

        action.status = ActionStatus.EXECUTING
        self._emit_log(action, event="executing")

        try:
            if action.type == ActionType.QUERY_GRAPH:
                result = self._exec_query_graph(action)
            elif action.type == ActionType.EDIT_FILE:
                result = self._exec_edit_file(action)
            elif action.type == ActionType.WRITE_FILE:
                result = self._exec_write_file(action)
            elif action.type == ActionType.DELETE_FILE:
                result = self._exec_delete_file(action)
            elif action.type == ActionType.RUN_SCRIPT:
                result = self._exec_run_script(action)
            elif action.type == ActionType.RUN_COMMAND:
                result = self._exec_run_command(action)
            else:
                raise ValueError(f"unsupported action type: {action.type}")
        except Exception as exc:
            action.status = ActionStatus.FAILED
            result = ActionResult(
                action_id=action.id,
                status=ActionStatus.FAILED,
                error=f"{type(exc).__name__}: {exc}",
            )
            result.duration_seconds = round(time.monotonic() - start, 3)
            self._emit_log(action, event="failed", extra={"error": result.error})
            return result

        result.duration_seconds = round(time.monotonic() - start, 3)
        action.status = result.status
        self._emit_log(
            action,
            event=result.status.value,
            extra={"duration_seconds": result.duration_seconds},
        )

        # Refresh the graph ONLY when the action mutated source files.
        if result.status == ActionStatus.SUCCEEDED and action.type in (
            ActionType.EDIT_FILE,
            ActionType.WRITE_FILE,
            ActionType.DELETE_FILE,
        ):
            result.graph_refresh = self._refresh_graph([action.target])
        return result

    # ─── Type-specific executors ───────────────────────────────────────────

    def _exec_query_graph(self, action: Action) -> ActionResult:
        """Read-only graph lookup. payload.query must be one of:
        deps | dependents | search | stats | freshness."""
        query = str(action.payload.get("query", "dependents"))
        gq = self._graph()
        if query == "deps":
            data: Any = gq.dependencies(_rel_to_root(action.target))
        elif query == "dependents":
            data = gq.dependents(_rel_to_root(action.target))
        elif query == "search":
            data = gq.search(action.target)[:50]
        elif query == "stats":
            data = {
                "files": len(gq.raw.get("files", {})),
                "classes": len(gq.raw.get("classes", {})),
                "functions": len(gq.raw.get("functions", {})),
                "edges": len(gq.raw.get("edges", [])),
                "generated_at": gq.raw.get("generated_at"),
            }
        elif query == "freshness":
            data = gq.freshness()
        else:
            raise ValueError(f"unknown query kind: {query}")
        return ActionResult(
            action_id=action.id,
            status=ActionStatus.SUCCEEDED,
            output=json.dumps(data, indent=2, default=str),
        )

    def _exec_edit_file(self, action: Action) -> ActionResult:
        """Whole-file rewrite with snapshot. Payload must contain
        either `content` (str) or `content_path` (path to read from)."""
        path = _abs(action.target)
        if not path.exists():
            raise FileNotFoundError(f"edit target does not exist: {path}")
        new_content = self._resolve_content(action.payload)
        snapshot = self._snapshot_file(action.id, path)
        path.write_text(new_content)
        return ActionResult(
            action_id=action.id,
            status=ActionStatus.SUCCEEDED,
            output=f"wrote {len(new_content)} bytes to {path}",
            snapshot_dir=str(snapshot.parent),
        )

    def _exec_write_file(self, action: Action) -> ActionResult:
        """Create a new file (or overwrite). If the file exists, snapshots
        it first so rollback restores prior bytes; if it does not exist,
        rollback deletes the created file."""
        path = _abs(action.target)
        new_content = self._resolve_content(action.payload)
        snapshot_dir = SNAPSHOT_DIR / action.id
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        existed = path.exists()
        if existed:
            self._snapshot_file(action.id, path)
        else:
            (snapshot_dir / "__created__").write_text(str(path))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(new_content)
        return ActionResult(
            action_id=action.id,
            status=ActionStatus.SUCCEEDED,
            output=f"{'overwrote' if existed else 'created'} {path} ({len(new_content)} bytes)",
            snapshot_dir=str(snapshot_dir),
        )

    def _exec_delete_file(self, action: Action) -> ActionResult:
        """Soft delete: move to snapshot dir instead of actually unlinking."""
        path = _abs(action.target)
        if not path.exists():
            raise FileNotFoundError(f"delete target does not exist: {path}")
        snapshot_dir = SNAPSHOT_DIR / action.id
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        trash = snapshot_dir / path.name
        shutil.move(str(path), str(trash))
        (snapshot_dir / "__deleted_from__").write_text(str(path))
        return ActionResult(
            action_id=action.id,
            status=ActionStatus.SUCCEEDED,
            output=f"moved {path} → {trash}",
            snapshot_dir=str(snapshot_dir),
        )

    def _exec_run_script(self, action: Action) -> ActionResult:
        """Run a Python script by path. payload.args is optional list[str]."""
        script = _abs(action.target)
        if not script.exists():
            raise FileNotFoundError(f"script not found: {script}")
        args = [str(a) for a in action.payload.get("args", [])]
        timeout = int(action.payload.get("timeout", 120))
        proc = subprocess.run(
            ["python3", str(script), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(ROOT),
        )
        status = (
            ActionStatus.SUCCEEDED if proc.returncode == 0 else ActionStatus.FAILED
        )
        return ActionResult(
            action_id=action.id,
            status=status,
            output=(proc.stdout or "")[-4000:],
            error=(proc.stderr or "")[-4000:] if proc.returncode != 0 else None,
        )

    def _exec_run_command(self, action: Action) -> ActionResult:
        """Run a shell command. payload.command is required."""
        command = str(action.payload.get("command", "")).strip()
        if not command:
            raise ValueError("run_command requires payload.command")
        timeout = int(action.payload.get("timeout", 60))
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(ROOT),
        )
        status = (
            ActionStatus.SUCCEEDED if proc.returncode == 0 else ActionStatus.FAILED
        )
        return ActionResult(
            action_id=action.id,
            status=status,
            output=(proc.stdout or "")[-4000:],
            error=(proc.stderr or "")[-4000:] if proc.returncode != 0 else None,
        )

    # ─── Rollback ──────────────────────────────────────────────────────────

    def rollback(self, action_id: str) -> ActionResult:
        """Undo an earlier file-mutating action by restoring its snapshot.

        RUN_SCRIPT and RUN_COMMAND have no automatic rollback — those
        are rejected. Callers must compose a compensating action.
        """
        snap_dir = SNAPSHOT_DIR / action_id
        if not snap_dir.exists():
            raise FileNotFoundError(f"no snapshot dir for action {action_id}")

        created_marker = snap_dir / "__created__"
        deleted_marker = snap_dir / "__deleted_from__"

        if created_marker.exists():
            # Action was WRITE_FILE creating a new file — rollback deletes it.
            original_path = Path(created_marker.read_text().strip())
            if original_path.exists():
                original_path.unlink()
            output = f"deleted created file {original_path}"
        elif deleted_marker.exists():
            # Action was DELETE_FILE — restore from the trash copy.
            original_path = Path(deleted_marker.read_text().strip())
            # There is exactly one snapshot entry besides the marker.
            snapshots = [
                p for p in snap_dir.iterdir() if p.name != "__deleted_from__"
            ]
            if not snapshots:
                raise FileNotFoundError("snapshot payload missing")
            original_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(snapshots[0]), str(original_path))
            output = f"restored {original_path} from trash"
        else:
            # Action was EDIT_FILE — snapshot holds the original bytes,
            # possibly multiple files if the caller snapshotted more than one.
            restored: list[str] = []
            manifest = snap_dir / "manifest.json"
            if not manifest.exists():
                raise FileNotFoundError("snapshot manifest missing")
            data = json.loads(manifest.read_text())
            for entry in data.get("files", []):
                snap_file = Path(entry["snapshot"])
                original_path = Path(entry["original"])
                if not snap_file.exists():
                    continue
                original_path.write_bytes(snap_file.read_bytes())
                restored.append(str(original_path))
            output = f"restored {len(restored)} file(s): {restored}"

        # Log the rollback as its own action-like event so the audit
        # trail stays append-only.
        self._append_jsonl(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "event": "rolled_back",
                "action_id": action_id,
                "output": output,
            }
        )
        # Refresh graph — rollback is also a mutation.
        graph_refresh = self._refresh_graph(
            [str(Path(output.split()[-1]))] if output else []
        )
        return ActionResult(
            action_id=action_id,
            status=ActionStatus.ROLLED_BACK,
            output=output,
            graph_refresh=graph_refresh,
        )

    # ─── Snapshot + logging helpers ────────────────────────────────────────

    def _snapshot_file(self, action_id: str, path: Path) -> Path:
        snap_dir = SNAPSHOT_DIR / action_id
        snap_dir.mkdir(parents=True, exist_ok=True)
        snap_file = snap_dir / f"{path.name}.{_short_hash(str(path))}.bak"
        snap_file.write_bytes(path.read_bytes())

        # Append to manifest so rollback can restore multi-file edits.
        manifest = snap_dir / "manifest.json"
        data: dict[str, Any] = {"files": []}
        if manifest.exists():
            data = json.loads(manifest.read_text())
        data["files"].append({"original": str(path), "snapshot": str(snap_file)})
        manifest.write_text(json.dumps(data, indent=2))
        return snap_file

    def _resolve_content(self, payload: dict[str, Any]) -> str:
        if "content" in payload:
            return str(payload["content"])
        if "content_path" in payload:
            return Path(str(payload["content_path"])).read_text()
        raise ValueError("payload must include 'content' or 'content_path'")

    def _preview(self, action: Action) -> str:
        """Text preview used by dry-run."""
        lines = [
            f"[DRY RUN] {action.type.value} → {action.target}",
            f"  risk={action.risk_level.value}  approval={'yes' if action.requires_approval else 'no'}",
            f"  reason={action.reason}",
        ]
        if action.impact and action.impact.in_graph:
            lines.append(
                f"  graph impact: {len(action.impact.direct_dependents)} dependents, "
                f"{len(action.impact.direct_dependencies)} dependencies, "
                f"critical_hub={action.impact.is_critical_hub}"
            )
            if action.impact.direct_dependents:
                preview = ", ".join(action.impact.direct_dependents[:5])
                if len(action.impact.direct_dependents) > 5:
                    preview += f", …(+{len(action.impact.direct_dependents) - 5})"
                lines.append(f"  dependents: {preview}")
        if action.type == ActionType.RUN_COMMAND:
            lines.append(f"  command: {action.payload.get('command', '')}")
        if action.type in (ActionType.EDIT_FILE, ActionType.WRITE_FILE):
            content = action.payload.get("content", "")
            if content:
                lines.append(f"  bytes: {len(content)}")
        return "\n".join(lines)

    def _refresh_graph(self, paths: list[str]) -> dict[str, Any]:
        """Best-effort incremental refresh. Never raises — the action
        succeeded, and stale-graph is a recoverable annoyance."""
        try:
            from scripts.incremental_graph import update as incr_update
        except Exception as exc:
            return {"mode": "skipped", "reason": f"import failed: {exc}"}
        try:
            return incr_update(paths, mode="auto", verbose=self.verbose)
        except Exception as exc:
            return {"mode": "error", "reason": str(exc)}

    def _emit_log(
        self,
        action: Action,
        *,
        event: str,
        extra: dict[str, Any] | None = None,
    ) -> None:
        record: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "action_id": action.id,
            "type": action.type.value,
            "target": action.target,
            "risk": action.risk_level.value,
            "requires_approval": action.requires_approval,
            "reason": action.reason,
            "status": action.status.value,
        }
        if action.impact:
            record["impact"] = {
                "in_graph": action.impact.in_graph,
                "dependents": len(action.impact.direct_dependents),
                "dependencies": len(action.impact.direct_dependencies),
                "critical_hub": action.impact.is_critical_hub,
                "centrality_rank": action.impact.centrality_rank,
            }
        if extra:
            record.update(extra)
        self._append_jsonl(record)
        self._emit_neon(record)

    def _append_jsonl(self, record: dict[str, Any]) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")

    def _emit_neon(self, record: dict[str, Any]) -> None:
        """Best-effort Neon audit. Never blocks or raises."""
        try:
            from eos_ai.memory import AgentMemory
        except Exception:
            return
        try:
            org_id = os.getenv("EOS_ORG_ID")
            if not org_id:
                return
            AgentMemory().log_event(org_id, "action_system", record)
        except Exception as exc:
            if self.verbose:
                print(f"[action] neon log skipped: {exc}")

    # ─── History ───────────────────────────────────────────────────────────

    def history(self, *, limit: int = 20) -> list[dict[str, Any]]:
        if not LOG_PATH.exists():
            return []
        lines = LOG_PATH.read_text().strip().splitlines()
        out: list[dict[str, Any]] = []
        for line in lines[-limit:]:
            try:
                out.append(json.loads(line))
            except Exception:
                continue
        return out


# ─── Utility functions ──────────────────────────────────────────────────────


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _short_hash(s: str) -> str:
    return hashlib.sha1(s.encode()).hexdigest()[:8]


def _abs(target: str) -> Path:
    p = Path(target)
    if p.is_absolute():
        return p
    return (ROOT / p).resolve()


def _rel_to_root(target: str) -> str:
    p = _abs(target)
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return target


# ─── CLI ────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="action_system")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # edit-file
    p_edit = sub.add_parser("edit-file", help="whole-file rewrite")
    p_edit.add_argument("--target", required=True)
    p_edit.add_argument("--payload-file", help="read new file content from here")
    p_edit.add_argument("--payload-string", help="inline new content")
    p_edit.add_argument("--reason", default="")
    p_edit.add_argument("--dry-run", action="store_true")
    p_edit.add_argument("--approve", action="store_true")

    # write-file
    p_write = sub.add_parser("write-file", help="create or overwrite a file")
    p_write.add_argument("--target", required=True)
    p_write.add_argument("--payload-file", help="read new file content from here")
    p_write.add_argument("--payload-string", help="inline new content")
    p_write.add_argument("--reason", default="")
    p_write.add_argument("--dry-run", action="store_true")
    p_write.add_argument("--approve", action="store_true")

    # delete-file
    p_del = sub.add_parser("delete-file", help="soft-delete (moves to snapshot dir)")
    p_del.add_argument("--target", required=True)
    p_del.add_argument("--reason", default="")
    p_del.add_argument("--dry-run", action="store_true")
    p_del.add_argument("--approve", action="store_true")

    # run-script
    p_script = sub.add_parser("run-script", help="execute a python script")
    p_script.add_argument("--target", required=True)
    p_script.add_argument("--args", nargs="*", default=[])
    p_script.add_argument("--reason", default="")
    p_script.add_argument("--dry-run", action="store_true")
    p_script.add_argument("--approve", action="store_true")

    # run-command
    p_cmd = sub.add_parser("run-command", help="execute a shell command")
    p_cmd.add_argument("--payload", required=True, help="shell command string")
    p_cmd.add_argument("--reason", default="")
    p_cmd.add_argument("--dry-run", action="store_true")
    p_cmd.add_argument("--approve", action="store_true")

    # query-graph
    p_query = sub.add_parser("query-graph", help="graph lookup action")
    p_query.add_argument("--target", required=True)
    p_query.add_argument(
        "--kind",
        default="dependents",
        choices=["deps", "dependents", "search", "stats", "freshness"],
    )
    p_query.add_argument("--reason", default="")

    # history
    p_hist = sub.add_parser("history", help="recent actions")
    p_hist.add_argument("--limit", type=int, default=20)

    # rollback
    p_rb = sub.add_parser("rollback", help="restore snapshot for action_id")
    p_rb.add_argument("action_id")

    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    system = ActionSystem(verbose=getattr(args, "verbose", False))

    if args.cmd == "history":
        for rec in system.history(limit=args.limit):
            print(json.dumps(rec, default=str))
        return 0

    if args.cmd == "rollback":
        try:
            result = system.rollback(args.action_id)
        except FileNotFoundError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(json.dumps(asdict(result), indent=2, default=str))
        return 0

    # Propose + execute paths
    if args.cmd == "edit-file":
        action_type = ActionType.EDIT_FILE
    elif args.cmd == "write-file":
        action_type = ActionType.WRITE_FILE
    elif args.cmd == "delete-file":
        action_type = ActionType.DELETE_FILE
    elif args.cmd == "run-script":
        action_type = ActionType.RUN_SCRIPT
    elif args.cmd == "run-command":
        action_type = ActionType.RUN_COMMAND
    elif args.cmd == "query-graph":
        action_type = ActionType.QUERY_GRAPH
    else:
        parser.error(f"unknown command {args.cmd}")
        return 2

    payload: dict[str, Any] = {}
    target = getattr(args, "target", None) or ""

    if action_type in (ActionType.EDIT_FILE, ActionType.WRITE_FILE):
        if args.payload_file:
            payload["content_path"] = args.payload_file
        elif args.payload_string is not None:
            payload["content"] = args.payload_string
        else:
            parser.error(
                f"{args.cmd} requires --payload-file or --payload-string"
            )
            return 2

    if action_type == ActionType.RUN_SCRIPT:
        payload["args"] = list(args.args)

    if action_type == ActionType.RUN_COMMAND:
        payload["command"] = args.payload
        target = shlex.split(args.payload)[0] if args.payload else "command"

    if action_type == ActionType.QUERY_GRAPH:
        payload["query"] = args.kind

    action = system.propose(
        action_type=action_type,
        target=target,
        payload=payload,
        reason=getattr(args, "reason", ""),
    )

    # Print the proposal summary so the operator sees impact + risk
    # before (or instead of) execution.
    print(
        json.dumps(
            {
                "action_id": action.id,
                "type": action.type.value,
                "target": action.target,
                "risk": action.risk_level.value,
                "requires_approval": action.requires_approval,
                "impact": asdict(action.impact) if action.impact else None,
            },
            indent=2,
            default=str,
        )
    )

    dry_run = getattr(args, "dry_run", False)
    approve = getattr(args, "approve", False)
    result = system.execute(action, dry_run=dry_run, approve=approve)

    print(json.dumps(asdict(result), indent=2, default=str))
    return 0 if result.status in (
        ActionStatus.SUCCEEDED,
        ActionStatus.SKIPPED_DRY_RUN,
        ActionStatus.ROLLED_BACK,
    ) else 1


if __name__ == "__main__":
    sys.exit(main())
