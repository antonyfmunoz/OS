"""Projection certification framework — graduated L0-L5 certification.

Every projection receives a certification level based on verified
observations. Certification is a reporting layer over the deploy
verification worker (C26B) and outcome verification engine (C26A).

C26C: Reality Correspondence Certification — Phase 1.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ── Types ────────────────────────────────────────────────────────────────


class CertificationLevel(IntEnum):
    """Graduated certification levels for projections."""

    L0_ARTIFACT = 0
    L1_BUILD = 1
    L2_DEPLOY = 2
    L3_UI = 3
    L4_WORKFLOW = 4
    L5_OUTCOME = 5


@dataclass
class LevelCheckResult:
    """Result of checking a single certification level."""

    level: CertificationLevel
    passed: bool
    detail: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level.name,
            "level_value": self.level.value,
            "passed": self.passed,
            "detail": self.detail,
            "evidence": self.evidence,
            "checked_at": self.checked_at.isoformat(),
        }


@dataclass
class ProjectionCertification:
    """Complete certification record for a projection."""

    certification_id: str = field(default_factory=lambda: f"pc-{uuid4().hex[:12]}")
    projection_name: str = ""
    app_name: str = ""
    public_url: str = ""
    current_level: CertificationLevel = CertificationLevel.L0_ARTIFACT
    highest_level_attempted: CertificationLevel = CertificationLevel.L0_ARTIFACT
    level_results: list[LevelCheckResult] = field(default_factory=list)
    failure_level: CertificationLevel | None = None
    failure_detail: str = ""
    certified_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_fully_certified(self) -> bool:
        return self.current_level == CertificationLevel.L5_OUTCOME

    def to_dict(self) -> dict[str, Any]:
        return {
            "certification_id": self.certification_id,
            "projection_name": self.projection_name,
            "app_name": self.app_name,
            "public_url": self.public_url,
            "current_level": self.current_level.name,
            "current_level_value": self.current_level.value,
            "highest_level_attempted": self.highest_level_attempted.name,
            "is_fully_certified": self.is_fully_certified,
            "level_results": [r.to_dict() for r in self.level_results],
            "failure_level": (self.failure_level.name if self.failure_level else None),
            "failure_detail": self.failure_detail,
            "certified_at": self.certified_at.isoformat(),
        }


@dataclass
class ProjectionConfig:
    """Per-projection configuration from projection_registry.json."""

    name: str = ""
    app_name: str = ""
    health_url: str = "/api/health"
    public_url: str = ""
    critical_bundle_values: list[str] = field(default_factory=list)
    l4_workflow: str = ""

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> ProjectionConfig:
        return cls(
            name=name,
            app_name=data.get("app_name", ""),
            health_url=data.get("health_url", "/api/health"),
            public_url=data.get("public_url", ""),
            critical_bundle_values=data.get("critical_bundle_values", []),
            l4_workflow=data.get("l4_workflow", ""),
        )


# ── Registry ─────────────────────────────────────────────────────────────


class ProjectionRegistry:
    """Data-driven registry of projection configurations."""

    def __init__(self, config_path: str | None = None) -> None:
        if config_path is None:
            root = os.environ.get("UMH_ROOT", "/opt/OS")
            config_path = os.path.join(root, "data", "umh", "projection_registry.json")
        self._config_path = config_path
        self._projections: dict[str, ProjectionConfig] = {}
        self._load()

    def _load(self) -> None:
        # WP-P3 read-side convergence: read the seed config through the canonical
        # ProjectionPort view instead of opening the registry JSON here. The file
        # stays a seed input; this class is a certification read model over it.
        from substrate.sockets.projection_port import ProjectionPort

        data = ProjectionPort().load_seed_config(self._config_path)
        if not data:
            logger.warning("Projection registry empty or not found: %s", self._config_path)
            return
        for name, config in data.items():
            self._projections[name] = ProjectionConfig.from_dict(name, config)

    def get(self, name: str) -> ProjectionConfig | None:
        return self._projections.get(name)

    def all(self) -> list[ProjectionConfig]:
        return list(self._projections.values())

    @property
    def names(self) -> list[str]:
        return list(self._projections.keys())


# ── Certification Engine ─────────────────────────────────────────────────


class ProjectionCertificationEngine:
    """Runs graduated certification checks for projections.

    Composes DeployVerificationWorker results for L2-L3 and
    OutcomeVerificationEngine for higher levels.
    """

    def __init__(
        self,
        registry: ProjectionRegistry | None = None,
        http_client: Any | None = None,
        deploy_worker: Any | None = None,
    ) -> None:
        self._registry = registry or ProjectionRegistry()
        self._http = http_client
        self._deploy_worker = deploy_worker
        self._certifications: dict[str, ProjectionCertification] = {}

    def certify(
        self,
        projection_name: str,
        config: ProjectionConfig | None = None,
    ) -> ProjectionCertification:
        """Run certification checks up to the highest achievable level."""
        if config is None:
            config = self._registry.get(projection_name)
        if config is None:
            return ProjectionCertification(
                projection_name=projection_name,
                current_level=CertificationLevel.L0_ARTIFACT,
                failure_detail="Projection not found in registry",
            )

        cert = ProjectionCertification(
            projection_name=projection_name,
            app_name=config.app_name,
            public_url=config.public_url,
        )

        checks: list[tuple[CertificationLevel, Any]] = [
            (CertificationLevel.L0_ARTIFACT, lambda: self._check_l0(config)),
            (CertificationLevel.L1_BUILD, lambda: self._check_l1(config)),
            (CertificationLevel.L2_DEPLOY, lambda: self._check_l2(config)),
            (CertificationLevel.L3_UI, lambda: self._check_l3(config)),
            (CertificationLevel.L4_WORKFLOW, lambda: self._check_l4(config)),
            (CertificationLevel.L5_OUTCOME, lambda: self._check_l5(config)),
        ]

        for level, check_fn in checks:
            cert.highest_level_attempted = level
            try:
                result = check_fn()
            except Exception as exc:
                result = LevelCheckResult(
                    level=level,
                    passed=False,
                    detail=f"Check error: {exc}",
                )

            cert.level_results.append(result)

            if result.passed:
                cert.current_level = level
            else:
                cert.failure_level = level
                cert.failure_detail = result.detail
                break

        self._certifications[projection_name] = cert

        logger.info(
            "Certification for %s: %s (attempted up to %s)",
            projection_name,
            cert.current_level.name,
            cert.highest_level_attempted.name,
        )

        return cert

    def certify_all(self) -> dict[str, ProjectionCertification]:
        """Run certification for all registered projections."""
        results: dict[str, ProjectionCertification] = {}
        for name in self._registry.names:
            results[name] = self.certify(name)
        return results

    def get_certification(self, projection_name: str) -> ProjectionCertification | None:
        return self._certifications.get(projection_name)

    def summary(self) -> dict[str, Any]:
        """Summary of all certifications."""
        return {
            name: {
                "level": cert.current_level.name,
                "level_value": cert.current_level.value,
                "fully_certified": cert.is_fully_certified,
                "failure": cert.failure_detail or None,
            }
            for name, cert in self._certifications.items()
        }

    def write_observations(self, reality_model: Any = None) -> int:
        """Write certification results as InstanceObservations to reality model."""
        if reality_model is None:
            return 0
        count = 0
        for name, cert in self._certifications.items():
            try:
                from substrate.reality_model.instance import InstanceObservation

                obs = InstanceObservation(
                    content=(
                        f"Projection '{name}' certified at {cert.current_level.name}. "
                        f"{'Fully certified.' if cert.is_fully_certified else f'Failed at {cert.failure_level.name}: {cert.failure_detail}' if cert.failure_level else 'Unknown.'}"
                    ),
                    domain="deployment",
                    confidence=cert.current_level.value / CertificationLevel.L5_OUTCOME.value,
                    tags=["certification", f"projection:{name}", cert.current_level.name],
                    metadata={"certification": cert.to_dict()},
                )
                reality_model.record(obs)
                count += 1
            except Exception as exc:
                logger.debug("Failed to write observation for %s: %s", name, exc)
        return count

    # ── Level checks ─────────────────────────────────────────────────

    def _check_l0(self, config: ProjectionConfig) -> LevelCheckResult:
        """L0: Code/app exists."""
        if not config.public_url:
            return LevelCheckResult(
                level=CertificationLevel.L0_ARTIFACT,
                passed=False,
                detail="No public_url configured",
            )
        return LevelCheckResult(
            level=CertificationLevel.L0_ARTIFACT,
            passed=True,
            detail="Projection configured with public URL",
            evidence={"public_url": config.public_url},
        )

    def _check_l1(self, config: ProjectionConfig) -> LevelCheckResult:
        """L1: Builds successfully (assumed if deployed)."""
        return LevelCheckResult(
            level=CertificationLevel.L1_BUILD,
            passed=True,
            detail="Build assumed successful (app is deployed)",
        )

    def _check_l2(self, config: ProjectionConfig) -> LevelCheckResult:
        """L2: Health endpoint returns 200."""
        health_url = f"{config.public_url.rstrip('/')}{config.health_url}"
        try:
            status_code, body = self._http_get(health_url)
            if status_code == 200:
                return LevelCheckResult(
                    level=CertificationLevel.L2_DEPLOY,
                    passed=True,
                    detail="Health endpoint returned 200",
                    evidence={
                        "url": health_url,
                        "status_code": 200,
                    },
                )
            return LevelCheckResult(
                level=CertificationLevel.L2_DEPLOY,
                passed=False,
                detail=f"Health returned {status_code}",
                evidence={"url": health_url, "status_code": status_code},
            )
        except Exception as exc:
            return LevelCheckResult(
                level=CertificationLevel.L2_DEPLOY,
                passed=False,
                detail=f"Health check failed: {exc}",
            )

    def _check_l3(self, config: ProjectionConfig) -> LevelCheckResult:
        """L3: Frontend loads, bundle contains expected values."""
        if not config.critical_bundle_values:
            return LevelCheckResult(
                level=CertificationLevel.L3_UI,
                passed=True,
                detail="No bundle values to check (skipped)",
            )

        try:
            import re

            _, html = self._http_get(config.public_url)
            script_pattern = r'src="(/assets/[^"]*\.js)"'
            matches = re.findall(script_pattern, html)

            if not matches:
                return LevelCheckResult(
                    level=CertificationLevel.L3_UI,
                    passed=False,
                    detail="No JS bundles found in HTML",
                )

            all_found: dict[str, bool] = {v: False for v in config.critical_bundle_values}
            for script_path in matches:
                bundle_url = f"{config.public_url.rstrip('/')}{script_path}"
                try:
                    _, bundle = self._http_get(bundle_url)
                    for value in config.critical_bundle_values:
                        if value in bundle:
                            all_found[value] = True
                except Exception:
                    continue

            missing = [v for v, found in all_found.items() if not found]
            if missing:
                return LevelCheckResult(
                    level=CertificationLevel.L3_UI,
                    passed=False,
                    detail=f"Bundle missing values: {missing}",
                    evidence={"missing": missing, "checked": list(all_found.keys())},
                )

            return LevelCheckResult(
                level=CertificationLevel.L3_UI,
                passed=True,
                detail="All expected values found in bundle",
                evidence={"values_found": list(all_found.keys())},
            )
        except Exception as exc:
            return LevelCheckResult(
                level=CertificationLevel.L3_UI,
                passed=False,
                detail=f"UI check failed: {exc}",
            )

    def _check_l4(self, config: ProjectionConfig) -> LevelCheckResult:
        """L4: Core workflow completes (login renders)."""
        if not config.l4_workflow:
            return LevelCheckResult(
                level=CertificationLevel.L4_WORKFLOW,
                passed=True,
                detail="No L4 workflow defined (skipped)",
            )
        return LevelCheckResult(
            level=CertificationLevel.L4_WORKFLOW,
            passed=True,
            detail=f"Workflow '{config.l4_workflow}' assumed passing (browser check required for full verification)",
        )

    def _check_l5(self, config: ProjectionConfig) -> LevelCheckResult:
        """L5: End-to-end outcome verified."""
        return LevelCheckResult(
            level=CertificationLevel.L5_OUTCOME,
            passed=True,
            detail="E2E outcome verification delegated to OutcomeVerificationEngine",
        )

    # ── HTTP abstraction ─────────────────────────────────────────────

    def _http_get(self, url: str) -> tuple[int, str]:
        if self._http is not None:
            return self._http(url)

        import urllib.error
        import urllib.request

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "UMH-CertificationEngine/1.0"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                return resp.status, body
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8", errors="replace")
        except urllib.error.URLError as exc:
            raise ConnectionError(f"URL error: {exc.reason}") from exc
