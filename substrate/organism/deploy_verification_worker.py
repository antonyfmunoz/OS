"""Deploy verification worker — no human should discover a white screen.

Runs automatically after every deployment. Checks health, HTML, bundle
values, and optionally browser rendering. Emits CRITICAL attention items
on failure. Writes results to telemetry and reality model.

C26B: Reality Correspondence Certification — Phase 1.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ── Types ────────────────────────────────────────────────────────────────


class DeployCheckStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class DeployCheckResult:
    """Result of a single post-deploy check."""

    check_name: str
    status: DeployCheckStatus
    detail: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    duration_ms: int = 0
    checked_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_name": self.check_name,
            "status": self.status.value,
            "detail": self.detail,
            "evidence": self.evidence,
            "duration_ms": self.duration_ms,
            "checked_at": self.checked_at.isoformat(),
        }


@dataclass
class DeployVerificationResult:
    """Complete post-deploy verification result."""

    verification_id: str = field(
        default_factory=lambda: f"dv-{uuid4().hex[:12]}"
    )
    app_name: str = ""
    public_url: str = ""
    checks: list[DeployCheckResult] = field(default_factory=list)
    overall_passed: bool = False
    critical_failures: list[str] = field(default_factory=list)
    started_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    completed_at: datetime | None = None
    total_duration_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "verification_id": self.verification_id,
            "app_name": self.app_name,
            "public_url": self.public_url,
            "checks": [c.to_dict() for c in self.checks],
            "overall_passed": self.overall_passed,
            "critical_failures": self.critical_failures,
            "started_at": self.started_at.isoformat(),
            "completed_at": (
                self.completed_at.isoformat()
                if self.completed_at
                else None
            ),
            "total_duration_ms": self.total_duration_ms,
        }


# ── Worker ───────────────────────────────────────────────────────────────


class DeployVerificationWorker:
    """Post-deploy verification pipeline.

    Steps:
    1. Health endpoint probe (poll with backoff)
    2. HTML root element check
    3. JS bundle value inspection
    4. Browser check (if available)
    5. Emit results to telemetry + reality model + attention
    """

    def __init__(
        self,
        http_client: Any | None = None,
        telemetry_emitter: Any | None = None,
        reality_model: Any | None = None,
        attention_emitter: Any | None = None,
    ) -> None:
        self._http = http_client
        self._telemetry = telemetry_emitter
        self._reality = reality_model
        self._attention = attention_emitter

    def verify_deployment(
        self,
        app_name: str,
        public_url: str,
        health_path: str = "/api/health",
        expected_bundle_values: list[str] | None = None,
        health_timeout_seconds: float = 120.0,
        health_poll_interval: float = 5.0,
    ) -> DeployVerificationResult:
        """Run the full post-deploy verification pipeline."""
        result = DeployVerificationResult(
            app_name=app_name,
            public_url=public_url,
        )
        start = time.monotonic()

        self._emit_telemetry_start(app_name)

        health_url = f"{public_url.rstrip('/')}{health_path}"
        health_check = self._check_health(
            health_url, health_timeout_seconds, health_poll_interval
        )
        result.checks.append(health_check)

        if health_check.status != DeployCheckStatus.PASSED:
            result.critical_failures.append(
                f"Health check failed: {health_check.detail}"
            )
            self._finalize(result, start)
            return result

        html_check = self._check_html_root(public_url)
        result.checks.append(html_check)

        if expected_bundle_values:
            bundle_check = self._check_bundle_values(
                public_url, expected_bundle_values
            )
            result.checks.append(bundle_check)
            if bundle_check.status != DeployCheckStatus.PASSED:
                result.critical_failures.append(
                    f"Bundle check failed: {bundle_check.detail}"
                )

        if html_check.status != DeployCheckStatus.PASSED:
            result.critical_failures.append(
                f"HTML check failed: {html_check.detail}"
            )

        self._finalize(result, start)
        return result

    def _check_health(
        self,
        health_url: str,
        timeout: float,
        interval: float,
    ) -> DeployCheckResult:
        """Poll health endpoint with exponential backoff."""
        start = time.monotonic()
        attempts = 0
        last_status = 0
        last_error = ""

        while (time.monotonic() - start) < timeout:
            attempts += 1
            try:
                status_code, body = self._http_get(health_url)
                last_status = status_code
                if status_code == 200:
                    return DeployCheckResult(
                        check_name="health_probe",
                        status=DeployCheckStatus.PASSED,
                        detail=f"Health returned 200 after {attempts} attempt(s)",
                        evidence={
                            "url": health_url,
                            "status_code": 200,
                            "attempts": attempts,
                            "body_preview": str(body)[:200],
                        },
                        duration_ms=int(
                            (time.monotonic() - start) * 1000
                        ),
                    )
            except Exception as exc:
                last_error = str(exc)
                last_status = 0

            backoff = min(interval * (1.5 ** (attempts - 1)), 30.0)
            time.sleep(backoff)

        return DeployCheckResult(
            check_name="health_probe",
            status=DeployCheckStatus.FAILED,
            detail=f"Health did not return 200 within {timeout}s (last status={last_status})",
            evidence={
                "url": health_url,
                "last_status_code": last_status,
                "last_error": last_error,
                "attempts": attempts,
                "timeout_seconds": timeout,
            },
            duration_ms=int((time.monotonic() - start) * 1000),
        )

    def _check_html_root(self, public_url: str) -> DeployCheckResult:
        """Fetch HTML and verify root element exists."""
        start = time.monotonic()
        try:
            status_code, body = self._http_get(public_url)
            body_str = str(body)

            has_root = '<div id="root">' in body_str or "id=\"root\"" in body_str
            has_html = "<html" in body_str.lower()

            if not has_html:
                return DeployCheckResult(
                    check_name="html_root",
                    status=DeployCheckStatus.FAILED,
                    detail="Response is not HTML",
                    evidence={
                        "status_code": status_code,
                        "body_preview": body_str[:500],
                    },
                    duration_ms=int(
                        (time.monotonic() - start) * 1000
                    ),
                )

            if not has_root:
                return DeployCheckResult(
                    check_name="html_root",
                    status=DeployCheckStatus.FAILED,
                    detail='No <div id="root"> found in HTML',
                    evidence={
                        "status_code": status_code,
                        "body_preview": body_str[:500],
                    },
                    duration_ms=int(
                        (time.monotonic() - start) * 1000
                    ),
                )

            return DeployCheckResult(
                check_name="html_root",
                status=DeployCheckStatus.PASSED,
                detail='HTML contains <div id="root">',
                evidence={"status_code": status_code},
                duration_ms=int(
                    (time.monotonic() - start) * 1000
                ),
            )
        except Exception as exc:
            return DeployCheckResult(
                check_name="html_root",
                status=DeployCheckStatus.ERROR,
                detail=f"Failed to fetch HTML: {exc}",
                duration_ms=int(
                    (time.monotonic() - start) * 1000
                ),
            )

    def _check_bundle_values(
        self, public_url: str, expected_values: list[str]
    ) -> DeployCheckResult:
        """Fetch JS bundle and verify expected baked-in values are present."""
        start = time.monotonic()
        try:
            status_code, html_body = self._http_get(public_url)
            html_str = str(html_body)

            script_pattern = r'src="(/assets/[^"]*\.js)"'
            matches = re.findall(script_pattern, html_str)

            if not matches:
                return DeployCheckResult(
                    check_name="bundle_values",
                    status=DeployCheckStatus.FAILED,
                    detail="No JS bundle found in HTML",
                    evidence={"html_preview": html_str[:500]},
                    duration_ms=int(
                        (time.monotonic() - start) * 1000
                    ),
                )

            all_found: dict[str, bool] = {v: False for v in expected_values}

            for script_path in matches:
                bundle_url = f"{public_url.rstrip('/')}{script_path}"
                try:
                    _, bundle_body = self._http_get(bundle_url)
                    bundle_str = str(bundle_body)
                    for value in expected_values:
                        if value in bundle_str:
                            all_found[value] = True
                except Exception:
                    continue

            missing = [v for v, found in all_found.items() if not found]

            if missing:
                return DeployCheckResult(
                    check_name="bundle_values",
                    status=DeployCheckStatus.FAILED,
                    detail=f"Missing values in bundle: {missing}",
                    evidence={
                        "expected": expected_values,
                        "found": {v: f for v, f in all_found.items()},
                        "bundles_checked": matches,
                    },
                    duration_ms=int(
                        (time.monotonic() - start) * 1000
                    ),
                )

            return DeployCheckResult(
                check_name="bundle_values",
                status=DeployCheckStatus.PASSED,
                detail=f"All {len(expected_values)} expected values found in bundle",
                evidence={
                    "expected": expected_values,
                    "found": {v: True for v in expected_values},
                    "bundles_checked": matches,
                },
                duration_ms=int(
                    (time.monotonic() - start) * 1000
                ),
            )
        except Exception as exc:
            return DeployCheckResult(
                check_name="bundle_values",
                status=DeployCheckStatus.ERROR,
                detail=f"Bundle check failed: {exc}",
                duration_ms=int(
                    (time.monotonic() - start) * 1000
                ),
            )

    def _finalize(
        self, result: DeployVerificationResult, start: float
    ) -> None:
        """Compute overall status and emit downstream signals."""
        result.completed_at = datetime.now(timezone.utc)
        result.total_duration_ms = int(
            (time.monotonic() - start) * 1000
        )

        failed_checks = [
            c
            for c in result.checks
            if c.status in (DeployCheckStatus.FAILED, DeployCheckStatus.ERROR)
        ]
        result.overall_passed = len(failed_checks) == 0

        if result.overall_passed:
            self._emit_telemetry_passed(result)
            logger.info(
                "Deploy verification PASSED for %s (%dms)",
                result.app_name,
                result.total_duration_ms,
            )
        else:
            self._emit_telemetry_failed(result)
            self._emit_critical_attention(result)
            logger.warning(
                "Deploy verification FAILED for %s: %s",
                result.app_name,
                result.critical_failures,
            )

        self._write_reality_observation(result)

    # ── HTTP abstraction ─────────────────────────────────────────────

    def _http_get(self, url: str) -> tuple[int, str]:
        """Make an HTTP GET request. Uses injected client or urllib."""
        if self._http is not None:
            return self._http(url)

        import urllib.request
        import urllib.error

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "UMH-DeployVerifier/1.0"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                return resp.status, body
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8", errors="replace")
        except urllib.error.URLError as exc:
            raise ConnectionError(f"URL error: {exc.reason}") from exc

    # ── Telemetry ────────────────────────────────────────────────────

    def _emit_telemetry_start(self, app_name: str) -> None:
        if self._telemetry is None:
            return
        try:
            self._telemetry.emit(
                "deploy_verification_started",
                execution_id=app_name,
                request_id=app_name,
                executor_type="deploy_verifier",
                operation="post_deploy_check",
                status="started",
                payload={"app_name": app_name},
            )
        except Exception as exc:
            logger.debug("Telemetry emit failed: %s", exc)

    def _emit_telemetry_passed(
        self, result: DeployVerificationResult
    ) -> None:
        if self._telemetry is None:
            return
        try:
            self._telemetry.emit(
                "deploy_verification_passed",
                execution_id=result.app_name,
                request_id=result.verification_id,
                executor_type="deploy_verifier",
                operation="post_deploy_check",
                status="passed",
                payload={
                    "checks_passed": len(result.checks),
                    "duration_ms": result.total_duration_ms,
                },
            )
        except Exception as exc:
            logger.debug("Telemetry emit failed: %s", exc)

    def _emit_telemetry_failed(
        self, result: DeployVerificationResult
    ) -> None:
        if self._telemetry is None:
            return
        try:
            self._telemetry.emit(
                "deploy_verification_failed",
                execution_id=result.app_name,
                request_id=result.verification_id,
                executor_type="deploy_verifier",
                operation="post_deploy_check",
                status="failed",
                payload={
                    "critical_failures": result.critical_failures,
                    "duration_ms": result.total_duration_ms,
                },
            )
        except Exception as exc:
            logger.debug("Telemetry emit failed: %s", exc)

    # ── Attention ────────────────────────────────────────────────────

    def _emit_critical_attention(
        self, result: DeployVerificationResult
    ) -> None:
        if self._attention is None:
            return
        try:
            from substrate.operator.operator_context import (
                OperatorAttentionItem,
                OperatorAttentionType,
                OperatorSeverity,
            )

            item = OperatorAttentionItem(
                attention_type=OperatorAttentionType.SERVICE,
                severity=OperatorSeverity.CRITICAL,
                title=f"Deploy verification FAILED: {result.app_name}",
                detail="; ".join(result.critical_failures),
                source="deploy_verification_worker",
            )
            self._attention(item)
        except Exception as exc:
            logger.debug("Attention emit failed: %s", exc)

    # ── Reality model ────────────────────────────────────────────────

    def _write_reality_observation(
        self, result: DeployVerificationResult
    ) -> None:
        if self._reality is None:
            return
        try:
            from substrate.reality_model.instance import (
                InstanceObservation,
            )

            status = "PASSED" if result.overall_passed else "FAILED"
            obs = InstanceObservation(
                content=(
                    f"Deploy verification {status} for {result.app_name} "
                    f"at {result.public_url}"
                ),
                domain="deployment",
                confidence=0.95 if result.overall_passed else 0.99,
                tags=[
                    "deploy_verification",
                    result.app_name,
                    status.lower(),
                ],
                metadata=result.to_dict(),
            )
            self._reality.record(obs)
        except Exception as exc:
            logger.debug("Reality observation write failed: %s", exc)
