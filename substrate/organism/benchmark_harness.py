"""Benchmark Harness — measures and compares Pipeline A (legacy) vs Pipeline B (governed).

Records identical metrics for both pipelines per cycle. Persists to JSONL.
Produces side-by-side comparison reports, between-cycle analysis, and campaign verdicts.

C32/C33 campaign infrastructure. UMH substrate subsystem. Instance-agnostic.
Supports 8 benchmark types (A-H) for C33 meta-harness validation.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


def _default_store() -> str:
    from substrate.state.runtime_paths import runtime_state_path

    return str(runtime_state_path("organism", "c33_benchmarks.jsonl", create_parent=False))


VALID_BENCHMARK_TYPES = {"A", "B", "C", "D", "E", "F", "G", "H"}


@dataclass
class CycleMetrics:
    cycle_id: str = ""
    pipeline: str = ""  # "legacy" or "governed"
    task_description: str = ""

    # Productivity
    start_time: float = 0.0
    end_time: float = 0.0
    elapsed_seconds: float = 0.0
    files_changed: int = 0
    lines_added: int = 0
    lines_removed: int = 0
    commits: int = 0

    # Quality
    tests_written: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    precommit_violations_caught: int = 0
    architecture_violations: int = 0
    bugs_found_post: int = 0

    # Governance (Pipeline B only, 0 for Pipeline A)
    work_packets_created: int = 0
    approvals_required: int = 0
    journal_entries: int = 0
    spine_submissions: int = 0

    # Intelligence (Pipeline B only, 0 for Pipeline A)
    learning_signals_generated: int = 0
    capabilities_extracted: int = 0
    reliability_updates: int = 0
    proof_packages_created: int = 0

    # Compound Value
    reusable_assets_created: int = 0
    protocol_improvements: int = 0

    # C33 extensions
    benchmark_type: str = "A"
    recorded_live: bool = False
    idempotency_key: str = ""

    # Fast-path (D3)
    fast_path_used: bool = False
    fast_path_reason: str = ""

    # Compounding (D1/D4)
    capabilities_reused: int = 0
    templates_matched: int = 0
    learning_signals_consumed: int = 0

    # Timing breakdown (D3/D10)
    spine_submit_ms: float = 0.0
    governance_check_ms: float = 0.0
    proof_capture_ms: float = 0.0
    journal_write_ms: float = 0.0
    learning_record_ms: float = 0.0
    total_overhead_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CycleMetrics:
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})


class BenchmarkHarness:
    """Records and compares benchmark metrics across C32 cycles."""

    def __init__(self, store_path: str | None = None) -> None:
        self._path = store_path or _default_store()
        self._records: list[CycleMetrics] = []
        self._active: dict[str, CycleMetrics] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        self._records.append(CycleMetrics.from_dict(json.loads(line)))
                    except (json.JSONDecodeError, TypeError) as exc:
                        logger.debug("skip malformed benchmark line: %s", exc)
        except OSError as exc:
            logger.debug("cannot read benchmarks: %s", exc)

    def _persist(self, metrics: CycleMetrics) -> None:
        if metrics.idempotency_key:
            existing_keys = {
                r.idempotency_key for r in self._records if r.idempotency_key and r is not metrics
            }
            if metrics.idempotency_key in existing_keys:
                logger.debug(
                    "duplicate idempotency_key, skipping persist: %s", metrics.idempotency_key
                )
                return
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        try:
            with open(self._path, "a") as f:
                f.write(json.dumps(metrics.to_dict(), default=str) + "\n")
        except OSError as exc:
            logger.debug("cannot persist benchmark: %s", exc)

    def start_cycle(
        self,
        cycle_id: str,
        pipeline: str,
        task: str,
        benchmark_type: str = "A",
    ) -> CycleMetrics:
        metrics = CycleMetrics(
            cycle_id=cycle_id,
            pipeline=pipeline,
            task_description=task,
            start_time=time.time(),
            benchmark_type=benchmark_type if benchmark_type in VALID_BENCHMARK_TYPES else "A",
            recorded_live=True,
            idempotency_key=f"{cycle_id}:{pipeline}:{uuid4().hex[:8]}",
        )
        self._active[f"{cycle_id}:{pipeline}"] = metrics
        logger.info(
            "benchmark started: cycle=%s pipeline=%s type=%s", cycle_id, pipeline, benchmark_type
        )
        return metrics

    def end_cycle(self, cycle_id: str, pipeline: str, **overrides: Any) -> CycleMetrics:
        key = f"{cycle_id}:{pipeline}"
        metrics = self._active.pop(key, None)
        if metrics is None:
            metrics = CycleMetrics(cycle_id=cycle_id, pipeline=pipeline)

        metrics.end_time = time.time()
        metrics.elapsed_seconds = max(metrics.end_time - metrics.start_time, 0)

        for k, v in overrides.items():
            if hasattr(metrics, k):
                setattr(metrics, k, v)

        self._records.append(metrics)
        self._persist(metrics)
        logger.info(
            "benchmark ended: cycle=%s pipeline=%s elapsed=%.1fs",
            cycle_id,
            pipeline,
            metrics.elapsed_seconds,
        )
        return metrics

    def collect_git_metrics(self, worktree_path: str) -> dict[str, int]:
        """Auto-collect files changed, lines added/removed, commits from git."""
        from substrate.execution.cpu_gate import gated_subprocess_run

        result: dict[str, int] = {
            "files_changed": 0,
            "lines_added": 0,
            "lines_removed": 0,
            "commits": 0,
        }
        try:
            diff = gated_subprocess_run(
                ["git", "diff", "--stat", "HEAD~1"],
                caller="benchmark_harness.collect_git_metrics",
                capture_output=True,
                text=True,
                cwd=worktree_path,
                timeout=10,
            )
            if diff is not None and diff.returncode == 0:
                lines = diff.stdout.strip().split("\n")
                for line in lines:
                    if "insertion" in line or "deletion" in line:
                        parts = line.split(",")
                        for part in parts:
                            part = part.strip()
                            if "file" in part:
                                result["files_changed"] = int(part.split()[0])
                            elif "insertion" in part:
                                result["lines_added"] = int(part.split()[0])
                            elif "deletion" in part:
                                result["lines_removed"] = int(part.split()[0])

            log = gated_subprocess_run(
                ["git", "rev-list", "--count", "HEAD"],
                caller="benchmark_harness.collect_git_metrics",
                capture_output=True,
                text=True,
                cwd=worktree_path,
                timeout=10,
            )
            if log is not None and log.returncode == 0:
                result["commits"] = int(log.stdout.strip())
        except (ValueError, OSError) as exc:
            logger.debug("git metrics collection failed: %s", exc)
        return result

    def compare(self, cycle_id: str) -> str:
        """Produce side-by-side comparison report for a cycle."""
        legacy = [r for r in self._records if r.cycle_id == cycle_id and r.pipeline == "legacy"]
        governed = [r for r in self._records if r.cycle_id == cycle_id and r.pipeline == "governed"]

        if not legacy or not governed:
            return f"Cycle {cycle_id}: incomplete data (legacy={len(legacy)}, governed={len(governed)})"

        a, b = legacy[-1], governed[-1]
        lines = [
            f"# Cycle {cycle_id} — A/B Comparison",
            f"Task: {a.task_description}",
            "",
            "| Metric | Legacy (A) | Governed (B) | Delta |",
            "|--------|-----------|-------------|-------|",
        ]

        def _row(label: str, va: Any, vb: Any) -> str:
            if isinstance(va, float) and isinstance(vb, float):
                delta = vb - va
                return f"| {label} | {va:.1f} | {vb:.1f} | {delta:+.1f} |"
            delta = (
                vb - va if isinstance(va, (int, float)) and isinstance(vb, (int, float)) else "—"
            )
            return f"| {label} | {va} | {vb} | {delta} |"

        lines.append(_row("Elapsed (s)", a.elapsed_seconds, b.elapsed_seconds))
        lines.append(_row("Files changed", a.files_changed, b.files_changed))
        lines.append(_row("Lines added", a.lines_added, b.lines_added))
        lines.append(_row("Lines removed", a.lines_removed, b.lines_removed))
        lines.append(_row("Commits", a.commits, b.commits))
        lines.append(_row("Tests written", a.tests_written, b.tests_written))
        lines.append(_row("Tests passed", a.tests_passed, b.tests_passed))
        lines.append(_row("Tests failed", a.tests_failed, b.tests_failed))
        lines.append(
            _row(
                "Pre-commit violations",
                a.precommit_violations_caught,
                b.precommit_violations_caught,
            )
        )
        lines.append(_row("Bugs found post", a.bugs_found_post, b.bugs_found_post))
        lines.append("")
        lines.append("### Governance (Pipeline B only)")
        lines.append(f"- Work packets: {b.work_packets_created}")
        lines.append(f"- Spine submissions: {b.spine_submissions}")
        lines.append(f"- Journal entries: {b.journal_entries}")
        lines.append(f"- Approvals required: {b.approvals_required}")
        lines.append("")
        lines.append("### Intelligence (Pipeline B only)")
        lines.append(f"- Learning signals: {b.learning_signals_generated}")
        lines.append(f"- Capabilities extracted: {b.capabilities_extracted}")
        lines.append(f"- Reliability updates: {b.reliability_updates}")
        lines.append(f"- Proof packages: {b.proof_packages_created}")
        lines.append(f"- Reusable assets: {b.reusable_assets_created}")
        lines.append(f"- Protocol improvements: {b.protocol_improvements}")
        return "\n".join(lines)

    def campaign_summary(self) -> str:
        """Full campaign comparison with improvement curve."""
        cycles = sorted(set(r.cycle_id for r in self._records))
        if not cycles:
            return "No benchmark data recorded."

        lines = [
            "# C32 Campaign Summary",
            "",
            "| Cycle | Legacy (s) | Governed (s) | Delta (s) | Gov. Signals | Gov. Proofs | Gov. Capabilities |",
            "|-------|-----------|-------------|-----------|-------------|------------|-------------------|",
        ]
        for cid in cycles:
            a = next(
                (r for r in self._records if r.cycle_id == cid and r.pipeline == "legacy"), None
            )
            b = next(
                (r for r in self._records if r.cycle_id == cid and r.pipeline == "governed"), None
            )
            at = f"{a.elapsed_seconds:.1f}" if a else "—"
            bt = f"{b.elapsed_seconds:.1f}" if b else "—"
            delta = f"{b.elapsed_seconds - a.elapsed_seconds:+.1f}" if a and b else "—"
            sigs = str(b.learning_signals_generated) if b else "—"
            proofs = str(b.proof_packages_created) if b else "—"
            caps = str(b.capabilities_extracted) if b else "—"
            lines.append(f"| {cid} | {at} | {bt} | {delta} | {sigs} | {proofs} | {caps} |")

        total_legacy = sum(r.elapsed_seconds for r in self._records if r.pipeline == "legacy")
        total_governed = sum(r.elapsed_seconds for r in self._records if r.pipeline == "governed")
        lines.append("")
        lines.append(f"**Total legacy time:** {total_legacy:.1f}s")
        lines.append(f"**Total governed time:** {total_governed:.1f}s")
        if total_legacy > 0:
            ratio = total_governed / total_legacy
            lines.append(f"**Governed/Legacy ratio:** {ratio:.2f}x")
        return "\n".join(lines)

    def between_cycle_analysis(self, cycle_ids: list[str]) -> dict[str, Any]:
        """Compute per-metric deltas between consecutive cycles."""
        if len(cycle_ids) < 2:
            return {"improvements": [], "error": "need at least 2 cycle IDs"}

        _NUMERIC_FIELDS = [
            "elapsed_seconds",
            "files_changed",
            "lines_added",
            "lines_removed",
            "commits",
            "tests_written",
            "tests_passed",
            "tests_failed",
            "capabilities_extracted",
            "capabilities_reused",
            "templates_matched",
            "learning_signals_generated",
            "learning_signals_consumed",
            "proof_packages_created",
            "reusable_assets_created",
            "total_overhead_ms",
            "spine_submit_ms",
            "governance_check_ms",
        ]

        improvements: list[dict[str, Any]] = []
        for i in range(1, len(cycle_ids)):
            prev_id, curr_id = cycle_ids[i - 1], cycle_ids[i]
            prev = [r for r in self._records if r.cycle_id == prev_id and r.pipeline == "governed"]
            curr = [r for r in self._records if r.cycle_id == curr_id and r.pipeline == "governed"]
            if not prev or not curr:
                continue
            p, c = prev[-1], curr[-1]
            for fld in _NUMERIC_FIELDS:
                old_val = getattr(p, fld, 0)
                new_val = getattr(c, fld, 0)
                delta = new_val - old_val
                if abs(delta) < 0.001:
                    continue
                direction = (
                    "improved"
                    if (
                        (
                            fld
                            in (
                                "elapsed_seconds",
                                "total_overhead_ms",
                                "tests_failed",
                                "spine_submit_ms",
                                "governance_check_ms",
                            )
                            and delta < 0
                        )
                        or (
                            fld
                            not in (
                                "elapsed_seconds",
                                "total_overhead_ms",
                                "tests_failed",
                                "spine_submit_ms",
                                "governance_check_ms",
                            )
                            and delta > 0
                        )
                    )
                    else "regressed"
                )
                improvements.append(
                    {
                        "from_cycle": prev_id,
                        "to_cycle": curr_id,
                        "metric": fld,
                        "old": round(old_val, 3) if isinstance(old_val, float) else old_val,
                        "new": round(new_val, 3) if isinstance(new_val, float) else new_val,
                        "delta": round(delta, 3) if isinstance(delta, float) else delta,
                        "direction": direction,
                    }
                )

        return {"improvements": improvements, "cycle_count": len(cycle_ids)}

    def campaign_verdict(self, benchmark_type: str = "") -> dict[str, Any]:
        """Compute aggregate stats and pass/fail verdict for a benchmark type."""
        records = self._records
        if benchmark_type:
            records = [r for r in records if r.benchmark_type == benchmark_type]

        if not records:
            return {"verdict": "NO_DATA", "benchmark_type": benchmark_type or "all"}

        governed = [r for r in records if r.pipeline == "governed"]
        legacy = [r for r in records if r.pipeline == "legacy"]

        total_gov_time = sum(r.elapsed_seconds for r in governed)
        total_leg_time = sum(r.elapsed_seconds for r in legacy)
        overhead_pct = (
            ((total_gov_time - total_leg_time) / total_leg_time * 100)
            if total_leg_time > 0
            else 0.0
        )

        total_caps_extracted = sum(r.capabilities_extracted for r in governed)
        total_caps_reused = sum(r.capabilities_reused for r in governed)
        total_templates = sum(r.templates_matched for r in governed)
        total_signals = sum(r.learning_signals_generated for r in governed)
        total_signals_consumed = sum(r.learning_signals_consumed for r in governed)
        fast_path_count = sum(1 for r in governed if r.fast_path_used)
        total_proofs = sum(r.proof_packages_created for r in governed)

        avg_overhead_ms = (
            (sum(r.total_overhead_ms for r in governed) / len(governed)) if governed else 0.0
        )

        has_capability_reuse = total_caps_reused > 0
        has_fast_path = fast_path_count > 0
        has_template_match = total_templates > 0
        overhead_below_10 = overhead_pct < 10.0

        if benchmark_type == "A":
            passes = overhead_below_10 and has_capability_reuse and has_fast_path
        elif benchmark_type == "E":
            compound_signals = sum(
                [
                    total_caps_extracted > 0,
                    total_caps_reused > 0,
                    total_templates > 0,
                    total_signals_consumed > 0,
                    has_fast_path,
                    total_proofs > 0,
                ]
            )
            passes = compound_signals >= 4
        else:
            passes = True

        return {
            "verdict": "PASS" if passes else "FAIL",
            "benchmark_type": benchmark_type or "all",
            "governed_cycles": len(governed),
            "legacy_cycles": len(legacy),
            "total_governed_time": round(total_gov_time, 1),
            "total_legacy_time": round(total_leg_time, 1),
            "overhead_pct": round(overhead_pct, 1),
            "overhead_below_10": overhead_below_10,
            "avg_overhead_ms": round(avg_overhead_ms, 1),
            "capabilities_extracted": total_caps_extracted,
            "capabilities_reused": total_caps_reused,
            "templates_matched": total_templates,
            "signals_generated": total_signals,
            "signals_consumed": total_signals_consumed,
            "fast_path_activations": fast_path_count,
            "proof_packages": total_proofs,
            "has_capability_reuse": has_capability_reuse,
            "has_fast_path": has_fast_path,
            "has_template_match": has_template_match,
        }

    def all_records(self) -> list[CycleMetrics]:
        return list(self._records)
