#!/usr/bin/env python3
"""Authoritative whole-tree shard result model — one canonical verdict.

Why this exists
---------------
The previous ad-hoc harness wrote a ``COMPLETE`` line after each shard's pytest
call returned, UNCONDITIONALLY. shard_04 of the run at ``e7ff662c`` was killed by
its 5400s bound (EXIT=124, no summary, ~70% of its tests executed) and still
carried a ``COMPLETE`` marker. The exit code was recorded alongside it, so a
careful reader could see the truth — but any consumer keying on the marker would
have read an incomplete run as green. A completion MARKER must never be able to
outrank authoritative failure evidence.

This module makes that structurally impossible: marker text, shard status,
coverage status, and the aggregate verdict are all DERIVED from one
``ShardResult``. There is no second place where "did it succeed?" is decided,
so the marker cannot drift from reality.

Fail-closed by construction: a shard is successful only when every invariant
below holds. Anything else — nonzero exit, timeout, missing artifact, malformed
artifact, or a coverage mismatch between assigned/collected/executed — yields an
explicit non-success status naming the reason.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# The exit code `timeout(1)` uses when it kills a command at its bound.
TIMEOUT_EXIT_CODE = 124

COMPLETE_MARKER = "COMPLETE"


@dataclass(frozen=True)
class ShardResult:
    """The ONE canonical record of what a shard actually did.

    Every downstream question — marker text, success, aggregate verdict — is
    answered from this object. Nothing else is authoritative.
    """

    shard_id: str
    assigned_files: int
    collected_files: int
    executed_files: int
    exit_code: int | None
    duration_seconds: float = 0.0
    artifact_present: bool = True
    artifact_malformed: bool = False
    summary_line: str = ""
    sha: str = ""

    # ── Invariants ──────────────────────────────────────────────────

    @property
    def timed_out(self) -> bool:
        return self.exit_code == TIMEOUT_EXIT_CODE

    @property
    def coverage_consistent(self) -> bool:
        """Assigned == collected == executed, and non-zero.

        A shard that silently ran fewer files than it was given has not proven
        anything about the rest, so partial coverage is a failure state rather
        than a footnote.
        """
        return (
            self.assigned_files > 0
            and self.assigned_files == self.collected_files == self.executed_files
        )

    def failure_reasons(self) -> list[str]:
        """Every reason this shard is not a clean success, most specific first."""
        reasons: list[str] = []
        if self.exit_code is None:
            reasons.append("no exit status recorded")
        elif self.timed_out:
            reasons.append(f"timed out (exit {TIMEOUT_EXIT_CODE}) after {self.duration_seconds:.0f}s")
        elif self.exit_code != 0:
            reasons.append(f"nonzero exit {self.exit_code}")
        if not self.artifact_present:
            reasons.append("result artifact missing")
        if self.artifact_malformed:
            reasons.append("result artifact malformed")
        if not self.coverage_consistent:
            reasons.append(
                "coverage mismatch "
                f"(assigned={self.assigned_files} collected={self.collected_files} "
                f"executed={self.executed_files})"
            )
        return reasons

    @property
    def succeeded(self) -> bool:
        """True only when the shard exited 0 AND every completeness check passes."""
        return not self.failure_reasons()

    def marker(self) -> str:
        """The status line written beside the shard.

        ``COMPLETE`` is emitted ONLY for a genuine success. Every other state
        gets an explicit, self-describing non-success marker, so a stale or
        copied marker can never be mistaken for a passing shard.
        """
        if self.succeeded:
            return COMPLETE_MARKER
        if self.timed_out:
            return f"INCOMPLETE_EXIT_{TIMEOUT_EXIT_CODE}"
        if self.exit_code is None:
            return "INCOMPLETE_NO_EXIT_STATUS"
        if self.exit_code != 0:
            return f"FAILED_EXIT_{self.exit_code}"
        # exit 0 but an invariant failed
        return "INCOMPLETE_COVERAGE"


@dataclass
class WholeTreeVerdict:
    """Aggregate over shards. Fails closed on ANY incomplete shard."""

    shards: list[ShardResult] = field(default_factory=list)
    discovered_nodes: int = 0
    excluded_node_ids: list[str] = field(default_factory=list)

    @property
    def complete(self) -> bool:
        """Every shard succeeded. One bad shard makes the whole run incomplete.

        Deliberately derived from ``ShardResult.succeeded`` rather than from any
        marker text, so the aggregate cannot be fooled by a stale COMPLETE line.
        """
        return bool(self.shards) and all(s.succeeded for s in self.shards)

    def incomplete_shards(self) -> list[ShardResult]:
        return [s for s in self.shards if not s.succeeded]

    def verdict(self) -> str:
        if not self.shards:
            return "INCOMPLETE — no shard results"
        if self.complete:
            if self.excluded_node_ids:
                # Truthful disposition: never "absolute green" when a node was
                # excluded, even a formally accepted pre-existing one.
                return (
                    "COMPLETE WITH "
                    f"{len(self.excluded_node_ids)} FORMALLY ACCEPTED PRE-EXISTING "
                    "BASELINE EXCEPTION(S)"
                )
            return "COMPLETE"
        bad = self.incomplete_shards()
        return (
            f"INCOMPLETE — {len(bad)} of {len(self.shards)} shards did not pass: "
            + "; ".join(f"{s.shard_id}: {', '.join(s.failure_reasons())}" for s in bad)
        )


# ── The formally accepted baseline exception ────────────────────────
#
# EXACTLY ONE node id. Not a file, not a class, not a directory, not a pattern.
# Extending this list is an owner decision requiring its own evidence record —
# see docs/cockpit-surface-convergence.md (S15) for the full disposition.
BASELINE_EXCEPTED_NODE_IDS: tuple[str, ...] = (
    "tests/test_strategic_context_runtime.py::TestHealthClassification::test_healthy_no_engines",
)
