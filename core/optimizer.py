"""
optimizer.py — Feedback loop for the EOS AI OS.

Reads the append-only logs produced by the rest of the stack, looks for
patterns worth acting on, and writes improvement PROPOSALS to disk. A
proposal is a declarative record of a change — it never mutates anything
by itself. Acting on a proposal is a separate, gated step (either manual
operator review or the healer/executor path).

    Run → Observe → Learn → Modify → Run improved version

Inputs:
  data/workflow_log.jsonl          — WorkflowEngine events
  data/orchestrator_log.jsonl      — Orchestrator events
  data/harness_log.jsonl           — Harness calls
  data/action_log.jsonl            — Action executions
  data/agent_state/observer.json   — Observer's rollups

Outputs:
  data/optimizer_proposals.jsonl   — proposals (append-only)
  data/optimizer_state.json        — last analysis timestamps

Proposal shape (JSONL row):
    {
      "id": "prop-...",
      "created_at": "...",
      "kind": "increase_job_interval" | "flag_flaky_step" | ...,
      "target": "continuous-research" | "wf-research.scan" | ...,
      "reason": "...",
      "evidence": {...},
      "suggested_action": {
          "action_type": "edit_file" | "run_command" | "none",
          "target": "...",
          "payload": {...}
      },
      "status": "pending" | "applied" | "rejected"
    }

Design:
  * Pure analyzer in this module — never touches the action system
    directly. The orchestrator (or an operator) submits the action from
    the proposal row.
  * Each heuristic is a small function with a clear name. New heuristics
    drop into ANALYZERS without touching other ones.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

_REPO_ROOT = "/opt/OS"
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


DATA_DIR = Path(_REPO_ROOT) / "data"
WORKFLOW_LOG = DATA_DIR / "workflow_log.jsonl"
ORCH_LOG = DATA_DIR / "orchestrator_log.jsonl"
HARNESS_LOG = DATA_DIR / "harness_log.jsonl"
ACTION_LOG = DATA_DIR / "action_log.jsonl"
OBSERVER_STATE = DATA_DIR / "agent_state" / "observer.json"
PROPOSALS_LOG = DATA_DIR / "optimizer_proposals.jsonl"
OPTIMIZER_STATE = DATA_DIR / "optimizer_state.json"


# ---------------------------------------------------------------------------
# Proposal type
# ---------------------------------------------------------------------------


@dataclass
class Proposal:
    id: str
    kind: str
    target: str
    reason: str
    evidence: dict[str, Any] = field(default_factory=dict)
    suggested_action: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _new_id() -> str:
    return f"prop-{uuid.uuid4().hex[:10]}"


# ---------------------------------------------------------------------------
# Log readers
# ---------------------------------------------------------------------------


def _read_jsonl(path: Path, limit: int = 2000) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f.readlines()[-limit:]:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        return []
    return rows


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Analyzers — each returns a list of Proposal
# ---------------------------------------------------------------------------


Analyzer = Callable[[dict[str, Any]], list[Proposal]]


def analyze_flaky_steps(ctx: dict[str, Any]) -> list[Proposal]:
    """Identify steps that retried more than once on average.

    Evidence: workflow_log.jsonl rows with event=step_retry grouped by
    (workflow_name, step_id).
    """
    rows: list[dict[str, Any]] = ctx["workflow_rows"]
    retries: Counter[tuple[str, str]] = Counter()
    totals: Counter[tuple[str, str]] = Counter()

    for r in rows:
        wf = r.get("workflow_name")
        sid = r.get("step_id")
        ev = r.get("event")
        if not wf or not sid:
            continue
        if ev == "step_started":
            totals[(wf, sid)] += 1
        elif ev == "step_retry":
            retries[(wf, sid)] += 1

    proposals: list[Proposal] = []
    for key, retry_count in retries.items():
        wf, sid = key
        total = max(totals.get(key, 0), 1)
        avg = retry_count / total
        if avg >= 1.0 and total >= 2:
            proposals.append(
                Proposal(
                    id=_new_id(),
                    kind="flag_flaky_step",
                    target=f"{wf}.{sid}",
                    reason=(
                        f"step {sid!r} in workflow {wf!r} retries on avg "
                        f"{avg:.1f}× across {total} runs"
                    ),
                    evidence={
                        "retry_count": retry_count,
                        "total_starts": total,
                        "avg_retries": round(avg, 2),
                    },
                    suggested_action={
                        "action_type": "none",
                        "target": f"{wf}.{sid}",
                        "payload": {
                            "suggestion": "investigate step implementation; consider max_attempts bump or input validation",
                        },
                    },
                )
            )
    return proposals


def analyze_disabled_jobs(ctx: dict[str, Any]) -> list[Proposal]:
    """Propose human review for disabled jobs and increase backoff base
    for jobs that have been failing.
    """
    rows: list[dict[str, Any]] = ctx["orch_rows"]
    disabled: list[str] = []
    failure_counts: Counter[str] = Counter()

    for r in rows:
        ev = r.get("event")
        jid = r.get("job_id")
        if not jid:
            continue
        if ev == "job_disabled":
            disabled.append(jid)
        if ev == "job_failed":
            failure_counts[jid] += 1

    proposals: list[Proposal] = []
    for jid in sorted(set(disabled)):
        proposals.append(
            Proposal(
                id=_new_id(),
                kind="review_disabled_job",
                target=jid,
                reason=f"orchestrator disabled job {jid!r} due to consecutive failures",
                evidence={
                    "disabled_events": disabled.count(jid),
                    "recent_failures": failure_counts.get(jid, 0),
                },
                suggested_action={
                    "action_type": "none",
                    "target": jid,
                    "payload": {
                        "suggestion": "operator: inspect logs, fix root cause, then orch.registry[jid].status = IDLE",
                    },
                },
            )
        )
    # Non-disabled but failing ≥ 3 times → recommend bumping backoff
    for jid, n in failure_counts.items():
        if jid in set(disabled):
            continue
        if n >= 3:
            proposals.append(
                Proposal(
                    id=_new_id(),
                    kind="bump_backoff",
                    target=jid,
                    reason=f"job {jid!r} failed {n} times in window — increase backoff_base",
                    evidence={"failure_count": n},
                    suggested_action={
                        "action_type": "none",
                        "target": f"scripts/orchestrator.py::{jid}",
                        "payload": {
                            "suggestion": "double backoff_base for this job",
                        },
                    },
                )
            )
    return proposals


def analyze_capability_denials(ctx: dict[str, Any]) -> list[Proposal]:
    """When the harness denies capability repeatedly for the same
    (agent, operation), propose broadening the profile — but only as
    a human-review proposal, never an automatic change.
    """
    rows: list[dict[str, Any]] = ctx["harness_rows"]
    denials: Counter[tuple[str, str]] = Counter()
    for r in rows:
        if r.get("ok") is not False:
            continue
        err = r.get("error") or ""
        # Shape: "<agent> allow-list does not include <op>" OR
        #        "<agent> explicitly denies <op>" OR
        #        "<agent> has max_capability=..."
        agent = r.get("agent") or ""
        op = r.get("operation") or ""
        if any(k in err for k in ("allow-list", "explicitly denies", "max_capability")):
            denials[(agent, op)] += 1

    proposals: list[Proposal] = []
    for (agent, op), n in denials.items():
        if n < 3:
            continue
        proposals.append(
            Proposal(
                id=_new_id(),
                kind="capability_denial_pattern",
                target=f"{agent}:{op}",
                reason=(
                    f"agent {agent!r} denied capability {op!r} {n} times — "
                    f"operator should decide whether to widen the profile"
                ),
                evidence={"denials": n},
                suggested_action={
                    "action_type": "none",
                    "target": f"core/capability.py::DEFAULT_PROFILES[{agent!r}]",
                    "payload": {
                        "suggestion": (
                            "review whether this agent legitimately needs "
                            f"{op} — if yes, add to allowed_operations"
                        ),
                    },
                },
            )
        )
    return proposals


def analyze_stale_graph(ctx: dict[str, Any]) -> list[Proposal]:
    """If the graph file is stale, propose a refresh command."""
    graph_file = DATA_DIR / "codebase_graph.json"
    if not graph_file.exists():
        return []
    age_h = (datetime.now().timestamp() - graph_file.stat().st_mtime) / 3600.0
    if age_h < 24.0:
        return []
    return [
        Proposal(
            id=_new_id(),
            kind="refresh_graph",
            target="data/codebase_graph.json",
            reason=f"codebase graph is {age_h:.1f}h old (>24h)",
            evidence={"age_hours": round(age_h, 2)},
            suggested_action={
                "action_type": "run_command",
                "target": "scripts/update-graph",
                "payload": {"command": "scripts/update-graph"},
            },
        )
    ]


def analyze_llm_failures(ctx: dict[str, Any]) -> list[Proposal]:
    """High LLM failure rate → suggest checking provider quotas."""
    rows: list[dict[str, Any]] = ctx["harness_rows"]
    llm_rows = [r for r in rows if (r.get("operation") == "call_llm")]
    if len(llm_rows) < 5:
        return []
    failed = [r for r in llm_rows if r.get("ok") is False]
    rate = len(failed) / len(llm_rows)
    if rate < 0.5:
        return []
    # Tally providers seen
    providers = Counter(r.get("provider") or "unknown" for r in llm_rows)
    return [
        Proposal(
            id=_new_id(),
            kind="llm_failure_spike",
            target="eos_ai/model_router.py",
            reason=(
                f"LLM call failure rate is {rate:.0%} over "
                f"{len(llm_rows)} calls — check provider quotas"
            ),
            evidence={
                "llm_calls": len(llm_rows),
                "failed": len(failed),
                "providers_seen": dict(providers),
            },
            suggested_action={
                "action_type": "run_command",
                "target": "ollama list",
                "payload": {
                    "command": "ollama list",
                    "note": "verify local fallback model is loaded",
                },
            },
        )
    ]


def analyze_advisor_effectiveness(ctx: dict[str, Any]) -> list[Proposal]:
    """Analyze advisor usage patterns and suggest rule tuning.

    Reads the advisor log to measure:
      - How often the advisor is triggered
      - Which escalation reasons dominate
      - Whether advisor calls are effective (modify/reject vs approve)
      - Whether certain rules are too aggressive (always approve)
    """
    advisor_log = DATA_DIR / "advisor_log.jsonl"
    rows = _read_jsonl(advisor_log, 500)
    if len(rows) < 5:
        return []

    proposals: list[Proposal] = []
    total = len(rows)

    # Count decisions
    decisions = Counter(r.get("decision", "unknown") for r in rows)
    approve_count = decisions.get("approve", 0)
    modify_count = decisions.get("modify", 0)
    reject_count = decisions.get("reject", 0)

    # Count escalation reasons
    reasons = Counter(r.get("escalation_reason", "unknown") for r in rows)

    # High approve rate means escalation rules are too aggressive
    approve_rate = approve_count / total if total else 0.0
    if approve_rate > 0.85 and total >= 10:
        # Find the most common reason that leads to approve
        reason_approve_counts: dict[str, int] = defaultdict(int)
        for r in rows:
            if r.get("decision") == "approve":
                reason_approve_counts[r.get("escalation_reason", "unknown")] += 1

        top_wasteful = max(
            reason_approve_counts.items(), key=lambda x: x[1], default=("", 0)
        )
        proposals.append(
            Proposal(
                id=_new_id(),
                kind="advisor_rule_too_aggressive",
                target=f"core/advisor.py::{top_wasteful[0]}",
                reason=(
                    f"advisor approve rate is {approve_rate:.0%} over {total} calls — "
                    f"rule '{top_wasteful[0]}' triggered {top_wasteful[1]} approvals "
                    f"(wasted advisor budget)"
                ),
                evidence={
                    "total_calls": total,
                    "approve_rate": round(approve_rate, 3),
                    "decisions": dict(decisions),
                    "top_wasteful_rule": top_wasteful[0],
                    "wasteful_count": top_wasteful[1],
                },
                suggested_action={
                    "action_type": "none",
                    "target": "core/advisor.py::EscalationConfig",
                    "payload": {
                        "suggestion": (
                            f"tighten or remove escalation rule '{top_wasteful[0]}' — "
                            f"it triggers advisor calls that always approve"
                        ),
                    },
                },
            )
        )

    # High reject rate means the executor is unreliable for certain tasks
    reject_rate = reject_count / total if total else 0.0
    if reject_rate > 0.30 and total >= 10:
        proposals.append(
            Proposal(
                id=_new_id(),
                kind="advisor_high_reject_rate",
                target="eos_ai/model_router.py",
                reason=(
                    f"advisor reject rate is {reject_rate:.0%} over {total} calls — "
                    f"executor model may need upgrading for these task types"
                ),
                evidence={
                    "total_calls": total,
                    "reject_rate": round(reject_rate, 3),
                    "reasons": dict(reasons),
                },
                suggested_action={
                    "action_type": "none",
                    "target": "eos_ai/model_router.py",
                    "payload": {
                        "suggestion": "review executor model capabilities for rejected task types",
                    },
                },
            )
        )

    # Latency analysis — if avg latency is too high, suggest timeout tuning
    latencies = [r.get("latency_ms", 0) for r in rows if r.get("latency_ms")]
    if latencies:
        avg_latency = sum(latencies) / len(latencies)
        if avg_latency > 15000:  # 15 seconds
            proposals.append(
                Proposal(
                    id=_new_id(),
                    kind="advisor_slow",
                    target="core/advisor.py::EscalationConfig",
                    reason=f"avg advisor latency is {avg_latency:.0f}ms (>15s) — consider timeout tuning",
                    evidence={
                        "avg_latency_ms": round(avg_latency),
                        "max_latency_ms": max(latencies),
                        "sample_size": len(latencies),
                    },
                    suggested_action={
                        "action_type": "none",
                        "target": "core/advisor.py::EscalationConfig",
                        "payload": {
                            "suggestion": "reduce advisor_timeout_sec or investigate slow provider",
                        },
                    },
                )
            )

    return proposals


ANALYZERS: list[Analyzer] = [
    analyze_flaky_steps,
    analyze_disabled_jobs,
    analyze_capability_denials,
    analyze_stale_graph,
    analyze_llm_failures,
    analyze_advisor_effectiveness,
]


# ---------------------------------------------------------------------------
# Optimizer
# ---------------------------------------------------------------------------


class Optimizer:
    """Owns the analyze → propose pipeline."""

    def __init__(self, *, verbose: bool = False) -> None:
        self.verbose = verbose

    def gather_context(self) -> dict[str, Any]:
        return {
            "workflow_rows": _read_jsonl(WORKFLOW_LOG, 2000),
            "orch_rows": _read_jsonl(ORCH_LOG, 2000),
            "harness_rows": _read_jsonl(HARNESS_LOG, 2000),
            "action_rows": _read_jsonl(ACTION_LOG, 2000),
            "observer": _read_json(OBSERVER_STATE),
        }

    def analyze(self) -> list[Proposal]:
        ctx = self.gather_context()
        all_proposals: list[Proposal] = []
        for analyzer in ANALYZERS:
            try:
                ps = analyzer(ctx)
            except Exception as e:
                if self.verbose:
                    print(f"[optimizer] analyzer {analyzer.__name__} failed: {e}")
                ps = []
            all_proposals.extend(ps)
        return all_proposals

    def persist(self, proposals: list[Proposal]) -> int:
        if not proposals:
            return 0
        with PROPOSALS_LOG.open("a", encoding="utf-8") as f:
            for p in proposals:
                f.write(json.dumps(p.to_dict(), default=str) + "\n")
        self._update_state(len(proposals))
        return len(proposals)

    def run_once(self) -> dict[str, Any]:
        proposals = self.analyze()
        written = self.persist(proposals)
        return {
            "ok": True,
            "proposals_new": written,
            "proposals_total_pending": self.count_pending(),
            "kinds": dict(Counter(p.kind for p in proposals)),
        }

    def count_pending(self) -> int:
        """Count proposals in the log with status=pending (scans entire log)."""
        if not PROPOSALS_LOG.exists():
            return 0
        n = 0
        try:
            with PROPOSALS_LOG.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except Exception:
                        continue
                    if row.get("status", "pending") == "pending":
                        n += 1
        except Exception:
            pass
        return n

    def _update_state(self, added: int) -> None:
        prev = _read_json(OPTIMIZER_STATE)
        prev["last_run_at"] = datetime.now(timezone.utc).isoformat()
        prev["last_added"] = added
        prev["total_added"] = int(prev.get("total_added", 0)) + added
        try:
            OPTIMIZER_STATE.write_text(
                json.dumps(prev, indent=2, default=str), encoding="utf-8"
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _cmd_once(args: argparse.Namespace) -> int:
    opt = Optimizer(verbose=args.verbose)
    result = opt.run_once()
    print(json.dumps(result, indent=2, default=str))
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    if not PROPOSALS_LOG.exists():
        print("no proposals yet")
        return 0
    printed = 0
    with PROPOSALS_LOG.open("r", encoding="utf-8") as f:
        lines = f.readlines()[-(args.limit or 20) :]
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        print(
            f"[{row.get('status', 'pending'):7s}] "
            f"{row.get('kind', '?'):28s} "
            f"{row.get('target', '?'):48s} "
            f"— {row.get('reason', '')[:80]}"
        )
        printed += 1
    print(f"\n{printed} proposals shown")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="optimizer",
        description="EOS optimizer — reads logs, proposes improvements.",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_once = sub.add_parser("once", help="run a single analysis pass")
    p_once.add_argument("-v", "--verbose", action="store_true")
    p_once.set_defaults(func=_cmd_once)

    p_list = sub.add_parser("list", help="list recent proposals")
    p_list.add_argument("--limit", type=int, default=20)
    p_list.set_defaults(func=_cmd_list)

    # Also accept --once as a top-level flag for convenience
    if argv is None:
        argv = sys.argv[1:]
    if argv == ["--once"] or argv == []:
        argv = ["once"]

    args = ap.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
