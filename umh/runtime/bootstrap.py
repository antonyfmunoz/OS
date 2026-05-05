"""Runtime bootstrap — crash-safe state rehydration on startup.

Loads persisted jobs, classifies them by status, and transitions
RUNNING jobs to ORPHANED (the process that was executing them is dead).
Returns a hydrated JobStore ready for the runtime loop.

Also rehydrates prediction records and weights from persistence (Phase 23).

No imports from umh/cells, umh/environments, umh/adapters, subprocess, or shell.
No execution side effects during rehydration.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from umh.jobs.lifecycle import should_retry, transition
from umh.jobs.models import JobStatus
from umh.jobs.store import JobStore
from umh.prediction.persistence import FilePredictionBackend
from umh.prediction.store import PredictionStore
from umh.prediction.weights import WeightStore

_log = logging.getLogger(__name__)


@dataclass
class BootstrapReport:
    """Summary of what happened during bootstrap rehydration."""

    total_loaded: int = 0
    kept_as_is: int = 0
    orphaned: int = 0
    retried: int = 0
    terminal: int = 0
    errors: int = 0
    details: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_loaded": self.total_loaded,
            "kept_as_is": self.kept_as_is,
            "orphaned": self.orphaned,
            "retried": self.retried,
            "terminal": self.terminal,
            "errors": self.errors,
            "details": self.details,
        }


@dataclass
class PredictionBootstrapReport:
    """Summary of prediction rehydration on startup."""

    records_loaded: int = 0
    records_restored: int = 0
    records_skipped: int = 0
    weights_loaded: int = 0
    weights_restored: int = 0
    weights_skipped: int = 0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "records_loaded": self.records_loaded,
            "records_restored": self.records_restored,
            "records_skipped": self.records_skipped,
            "weights_loaded": self.weights_loaded,
            "weights_restored": self.weights_restored,
            "weights_skipped": self.weights_skipped,
            "errors": self.errors,
        }


_TERMINAL_STATUSES = {JobStatus.SUCCEEDED, JobStatus.CANCELLED}
_KEEP_STATUSES = {JobStatus.CREATED, JobStatus.SUBMITTED}


class RuntimeBootstrap:
    """Rehydrates job state on startup. No execution side effects."""

    def rehydrate(self, store: JobStore) -> BootstrapReport:
        """Classify and fix jobs loaded from persistence.

        - SUCCEEDED, CANCELLED → terminal, do nothing
        - FAILED, TIMEOUT, ORPHANED with exhausted retries → terminal
        - CREATED, SUBMITTED → keep as-is
        - RUNNING → mark ORPHANED, then retry if allowed
        - FAILED, TIMEOUT, ORPHANED with retries remaining → retry to SUBMITTED
        """
        report = BootstrapReport()
        all_jobs = store.list_jobs()
        report.total_loaded = len(all_jobs)

        for job in all_jobs:
            try:
                if job.status in _TERMINAL_STATUSES:
                    report.terminal += 1
                    report.details.append(
                        {"job_id": job.job_id, "action": "terminal", "status": job.status.value}
                    )
                    continue

                if job.status in _KEEP_STATUSES:
                    report.kept_as_is += 1
                    report.details.append(
                        {"job_id": job.job_id, "action": "kept", "status": job.status.value}
                    )
                    continue

                if job.status == JobStatus.RUNNING:
                    transition(job, JobStatus.ORPHANED, reason="process restart")
                    store.update_job(job)
                    report.orphaned += 1
                    report.details.append(
                        {"job_id": job.job_id, "action": "orphaned", "status": "orphaned"}
                    )

                    if should_retry(job):
                        transition(job, JobStatus.SUBMITTED, reason="auto-retry after orphan")
                        store.update_job(job)
                        report.retried += 1
                        report.details.append(
                            {"job_id": job.job_id, "action": "retried", "status": "submitted"}
                        )
                    continue

                if job.status in (JobStatus.FAILED, JobStatus.TIMEOUT, JobStatus.ORPHANED):
                    if should_retry(job):
                        transition(job, JobStatus.SUBMITTED, reason="auto-retry on startup")
                        store.update_job(job)
                        report.retried += 1
                        report.details.append(
                            {"job_id": job.job_id, "action": "retried", "status": "submitted"}
                        )
                    else:
                        report.terminal += 1
                        report.details.append(
                            {
                                "job_id": job.job_id,
                                "action": "terminal_exhausted",
                                "status": job.status.value,
                            }
                        )
                    continue

            except Exception as e:
                report.errors += 1
                report.details.append({"job_id": job.job_id, "action": "error", "error": str(e)})
                _log.warning("Bootstrap error for job %s: %s", job.job_id, e)

        _log.info(
            "Bootstrap complete: %d loaded, %d terminal, %d orphaned, %d retried, %d kept, %d errors",
            report.total_loaded,
            report.terminal,
            report.orphaned,
            report.retried,
            report.kept_as_is,
            report.errors,
        )
        return report

    def rehydrate_predictions(
        self,
        backend: FilePredictionBackend,
        store: PredictionStore | None = None,
        weight_store: WeightStore | None = None,
    ) -> PredictionBootstrapReport:
        """Restore prediction records and weights from persistence.

        Corrupted entries are skipped. Never crashes — returns report.
        """
        report = PredictionBootstrapReport()

        try:
            records, rec_stats = backend.load_records()
            report.records_loaded = rec_stats.records_loaded
            report.records_skipped = rec_stats.records_skipped
            if rec_stats.errors:
                report.errors.extend(rec_stats.errors)

            if store is not None:
                for rec in records:
                    try:
                        store.append(rec)
                        report.records_restored += 1
                    except Exception as e:
                        report.records_skipped += 1
                        report.errors.append(f"restore record {rec.prediction_id}: {e}")
        except Exception as e:
            report.errors.append(f"load_records failed: {e}")
            _log.warning("Prediction record rehydration failed: %s", e)

        try:
            weights, w_stats = backend.load_weights()
            report.weights_loaded = w_stats.weights_loaded
            report.weights_skipped = w_stats.weights_skipped
            if w_stats.errors:
                report.errors.extend(w_stats.errors)

            if weight_store is not None:
                for w_data in weights:
                    try:
                        weight_store.restore_weight(
                            pattern_key=w_data["pattern_key"],
                            weight=w_data.get("weight", 1.0),
                            success_count=w_data.get("success_count", 0),
                            failure_count=w_data.get("failure_count", 0),
                            last_updated=w_data.get("last_updated", ""),
                        )
                        report.weights_restored += 1
                    except Exception as e:
                        report.weights_skipped += 1
                        report.errors.append(f"restore weight {w_data.get('pattern_key', '?')}: {e}")
        except Exception as e:
            report.errors.append(f"load_weights failed: {e}")
            _log.warning("Prediction weight rehydration failed: %s", e)

        _log.info(
            "Prediction rehydration: %d records restored, %d weights restored, %d errors",
            report.records_restored,
            report.weights_restored,
            len(report.errors),
        )
        return report
