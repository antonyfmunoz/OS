"""Pytest evidence plugin — machine-readable test-lifecycle acquisition (v1.2).

Loaded by the controlling CLI with ``-p
substrate.understanding.reconstruction.pytest_evidence_plugin``. Writes ONE
canonical JSON artifact describing the session: collected items, deselections,
collection errors, and per-phase (setup/call/teardown) raw outcomes for every
executed test. Semantic normalization (xpassed/error/two-dimension outcomes)
happens at INGESTION (test_evidence.py), never here — the plugin records raw
pytest facts only.

Activation is OPT-IN: the plugin is a no-op unless ``UMH_TEST_EVIDENCE_OUT`` is
set. Repository state is INJECTED by the CLI through environment variables
(``UMH_TEST_EVIDENCE_COMMIT`` etc.) — the plugin NEVER shells out to git.

Failure policy (non-runtest hooks must not raise): every acquisition/
serialization step is wrapped; internal errors are recorded as a bounded
``plugin_error`` entry in the artifact instead of propagating, and an artifact
carrying ``plugin_error`` fails evidence qualification downstream. The artifact
is written atomically at session finish; a partial artifact is never left
behind as valid.

Privacy: never captures env values, credentials, full command lines, or
unrestricted test output. Skip/xfail reasons and failure crash lines are
bounded and pass through the canonical ``redact()``; if redaction is
unavailable the text is DROPPED, never stored unredacted.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Optional

PLUGIN_VERSION = "umh-pytest-evidence-v1"
TEST_EVIDENCE_SCHEMA_VERSION = "test-evidence-v1"

ENV_OUT = "UMH_TEST_EVIDENCE_OUT"
ENV_COMMIT = "UMH_TEST_EVIDENCE_COMMIT"
ENV_DIRTY = "UMH_TEST_EVIDENCE_DIRTY"
ENV_FINGERPRINT = "UMH_TEST_EVIDENCE_FINGERPRINT"
ENV_TEMPLATE = "UMH_TEST_EVIDENCE_TEMPLATE"
ENV_SCHEMA = "UMH_TEST_EVIDENCE_SCHEMA"

_MAX_REASON_CHARS = 200
_MAX_SELECTION_ARGS = 50
_MAX_ARG_CHARS = 200
_MAX_COLLECTION_ERRORS = 50
_REDACTION_UNAVAILABLE = "[REDACTION_UNAVAILABLE]"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _bounded_redacted(text: Any) -> str:
    """Bound to _MAX_REASON_CHARS and redact. Text is DROPPED (marker stored)
    when the canonical redactor cannot be imported — never stored unredacted."""
    if text is None:
        return ""
    s = str(text)[:_MAX_REASON_CHARS]
    try:
        from substrate.understanding.reconstruction.runtime_probes import redact

        cleaned, _ = redact(s)
        return cleaned
    except Exception:
        return _REDACTION_UNAVAILABLE


class _EvidenceCollector:
    """Per-session collector registered in pytest_configure (no module-level
    mutable state — repeated invocations in one interpreter do not leak)."""

    def __init__(self, out_path: str) -> None:
        self.out_path = out_path
        self.started_at: Optional[str] = None
        self.finished_at: Optional[str] = None
        self.exit_status: Optional[int] = None
        self.collected: list[dict[str, Any]] = []
        self.deselected_after_collection: list[str] = []
        self.collection_errors: list[dict[str, Any]] = []
        self.executions: dict[str, dict[str, Any]] = {}
        self.selection_args: list[str] = []
        self.plugin_error: Optional[dict[str, str]] = None
        self.injected = {
            "repository_commit": os.environ.get(ENV_COMMIT, ""),
            "repository_dirty": os.environ.get(ENV_DIRTY, "unknown"),
            "repository_fingerprint": os.environ.get(ENV_FINGERPRINT, ""),
            "selection_template_id": os.environ.get(ENV_TEMPLATE, ""),
            "expected_schema_version": os.environ.get(ENV_SCHEMA, ""),
        }

    def _record_error(self, stage: str, exc: BaseException) -> None:
        # First error wins — it marks the whole artifact as unqualifiable.
        if self.plugin_error is None:
            self.plugin_error = {
                "stage": stage,
                "message": f"{type(exc).__name__}: {str(exc)[:_MAX_REASON_CHARS]}",
            }

    # ── session lifecycle ────────────────────────────────────────────────
    def pytest_sessionstart(self, session: Any) -> None:
        try:
            self.started_at = _now_iso()
            args = getattr(getattr(session.config, "invocation_params", None), "args", ()) or ()
            bounded: list[str] = []
            for a in args:
                if len(bounded) >= _MAX_SELECTION_ARGS:
                    bounded.append("[TRUNCATED_ARGS]")
                    break
                bounded.append(str(a)[:_MAX_ARG_CHARS])
            self.selection_args = bounded
        except Exception as exc:  # non-runtest hook: never raise
            self._record_error("sessionstart", exc)

    # ── collection ───────────────────────────────────────────────────────
    def pytest_collection_modifyitems(self, config: Any, items: list[Any]) -> None:
        try:
            for item in items:
                callspec = getattr(item, "callspec", None)
                self.collected.append(
                    {
                        "nodeid": item.nodeid,
                        "path": str(getattr(item, "path", "")),
                        "markers": sorted({m.name for m in item.iter_markers()}),
                        "parametrized": callspec is not None,
                        "callspec_id": getattr(callspec, "id", "") if callspec else "",
                    }
                )
        except Exception as exc:
            self._record_error("collection_modifyitems", exc)

    def pytest_deselected(self, items: list[Any]) -> None:
        try:
            self.deselected_after_collection.extend(i.nodeid for i in items)
        except Exception as exc:
            self._record_error("deselected", exc)

    def pytest_collectreport(self, report: Any) -> None:
        try:
            if getattr(report, "failed", False):
                if len(self.collection_errors) < _MAX_COLLECTION_ERRORS:
                    self.collection_errors.append(
                        {
                            "nodeid": getattr(report, "nodeid", ""),
                            "message": _bounded_redacted(getattr(report, "longrepr", "")),
                        }
                    )
        except Exception as exc:
            self._record_error("collectreport", exc)

    # ── execution (runtest family — pytest permits exceptions here, but we
    # still never raise: evidence loss must not corrupt the test run) ──────
    def pytest_runtest_logreport(self, report: Any) -> None:
        try:
            phases = self.executions.setdefault(report.nodeid, {"phases": {}})
            entry: dict[str, Any] = {
                "outcome": report.outcome,  # raw pytest: passed|failed|skipped
                "duration": round(float(getattr(report, "duration", 0.0)), 6),
            }
            if hasattr(report, "wasxfail"):
                entry["wasxfail"] = True
                entry["wasxfail_reason"] = _bounded_redacted(getattr(report, "wasxfail", ""))
            if report.outcome != "passed":
                crash = getattr(report, "longrepr", None)
                reprcrash = getattr(crash, "reprcrash", None)
                message = getattr(reprcrash, "message", None)
                entry["detail"] = _bounded_redacted(
                    message if message is not None else (crash if crash is not None else "")
                )
            phases["phases"][report.when] = entry
        except Exception as exc:
            self._record_error("runtest_logreport", exc)

    # ── artifact write ───────────────────────────────────────────────────
    def pytest_sessionfinish(self, session: Any, exitstatus: Any) -> None:
        try:
            self.finished_at = _now_iso()
            self.exit_status = int(getattr(exitstatus, "value", exitstatus))
        except Exception as exc:
            self._record_error("sessionfinish", exc)
        self._write_artifact()

    def _write_artifact(self) -> None:
        try:
            import pytest as _pytest

            pytest_version = _pytest.__version__
        except Exception:
            pytest_version = "unknown"
        import platform

        artifact = {
            "schema_version": TEST_EVIDENCE_SCHEMA_VERSION,
            "plugin_version": PLUGIN_VERSION,
            "session": {
                "pytest_version": pytest_version,
                "python_version": platform.python_version(),
                "started_at": self.started_at,
                "finished_at": self.finished_at,
                "exit_status": self.exit_status,
                "injected": self.injected,
                "selection_manifest": {
                    "template_id": self.injected["selection_template_id"],
                    "args": self.selection_args,
                },
            },
            "collected": self.collected,
            "deselected_after_collection": sorted(self.deselected_after_collection),
            "collection_errors": self.collection_errors,
            "executions": self.executions,
            "plugin_error": self.plugin_error,
        }
        try:
            payload = json.dumps(artifact, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        except Exception as exc:
            # Serialization failed — emit a minimal error-only artifact so the
            # failure is visible (a missing report also fails qualification).
            self._record_error("serialize", exc)
            payload = json.dumps(
                {
                    "schema_version": TEST_EVIDENCE_SCHEMA_VERSION,
                    "plugin_version": PLUGIN_VERSION,
                    "plugin_error": self.plugin_error,
                },
                sort_keys=True,
            )
        try:
            tmp = f"{self.out_path}.tmp.{os.getpid()}"
            with open(tmp, "w", encoding="utf-8") as fh:
                fh.write(payload)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self.out_path)
        except Exception:
            # Nothing safe left to do: no artifact → downstream qualification
            # fails loudly. Never corrupt the test run itself.
            return


def pytest_configure(config: Any) -> None:
    """Opt-in registration: no output path → the plugin does nothing at all."""
    try:
        out = os.environ.get(ENV_OUT, "").strip()
        if not out:
            return
        collector = _EvidenceCollector(out)
        config.pluginmanager.register(collector, "umh-test-evidence-collector")
        config._umh_evidence_collector = collector
    except Exception:
        # Registration failure must never break the test run; the missing
        # artifact fails evidence qualification downstream.
        return


def pytest_unconfigure(config: Any) -> None:
    try:
        collector = getattr(config, "_umh_evidence_collector", None)
        if collector is not None:
            config.pluginmanager.unregister(collector)
            del config._umh_evidence_collector
    except Exception:
        return
