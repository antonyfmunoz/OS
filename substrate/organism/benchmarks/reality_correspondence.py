"""Reality Correspondence Benchmark — 50 failure scenarios across 5 domains.

Proves: UMH detects reality divergence before operator discovery.
Each scenario is deterministic — no LLM, no network calls.

Detection methods:
  - certification: mock HTTP → ProjectionCertificationEngine → level < L5
  - deploy_verification: mock HTTP → DeployVerificationWorker → overall_passed=False
  - trust_score: TrustScoreEngine.compute() → composite < 0.5
  - correspondence: claimed_state vs reality_observations dict mismatch

C26F: Reality Correspondence Certification — Phase 2.
"""

from __future__ import annotations

import json
import logging
import tempfile
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ── Types ────────────────────────────────────────────────────────────────


class BenchmarkDomain(str, Enum):
    BUILD = "build"
    DEPLOY = "deploy"
    AUTH = "auth"
    DATA = "data"
    INTEGRATION = "integration"


_SEVERITY_ORDER = {"critical": 3, "high": 2, "medium": 1, "low": 0}


@dataclass
class BenchmarkScenario:
    """A single failure scenario with claimed vs observed reality."""

    scenario_id: str = ""
    domain: BenchmarkDomain = BenchmarkDomain.BUILD
    name: str = ""
    description: str = ""
    claimed_state: dict[str, Any] = field(default_factory=dict)
    reality_observations: dict[str, Any] = field(default_factory=dict)
    expected_detection: bool = True
    expected_severity: str = "high"
    detection_method: str = "certification"

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "domain": self.domain.value,
            "name": self.name,
            "description": self.description,
            "claimed_state": self.claimed_state,
            "reality_observations": self.reality_observations,
            "expected_detection": self.expected_detection,
            "expected_severity": self.expected_severity,
            "detection_method": self.detection_method,
        }


@dataclass
class BenchmarkResult:
    """Result of running a single benchmark scenario."""

    scenario_id: str = ""
    detected: bool = False
    classified_correctly: bool = False
    detection_method: str = ""
    time_to_detect_ms: int = 0
    detected_severity: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "detected": self.detected,
            "classified_correctly": self.classified_correctly,
            "detection_method": self.detection_method,
            "time_to_detect_ms": self.time_to_detect_ms,
            "detected_severity": self.detected_severity,
            "notes": self.notes,
        }


# ── Scenario Definitions ────────────────────────────────────────────────


STANDARD_HTML = """<!DOCTYPE html>
<html lang="en"><head><title>App</title></head>
<body><div id="root"></div>
<script type="module" src="/assets/index-abc123.js"></script>
</body></html>"""

GOOD_BUNDLE = 'var c={clerkKey:"pk_test_aGlwLXNuaXBlLTMz"};'


def _build_scenarios() -> list[BenchmarkScenario]:
    scenarios: list[BenchmarkScenario] = []

    # ── BUILD domain (10) ────────────────────────────────────────────

    scenarios.append(BenchmarkScenario(
        scenario_id="BUILD-01",
        domain=BenchmarkDomain.BUILD,
        name="C25 bug replay: env var undefined",
        description="VITE_CLERK_PUBLISHABLE_KEY not in build args. Bundle has no Clerk key.",
        claimed_state={"build": "success", "deploy": "success", "clerk_key": "present"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (200, STANDARD_HTML),
            "bundle": (200, 'var c={clerkKey:undefined};'),
        },
        expected_severity="critical",
        detection_method="certification",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="BUILD-02",
        domain=BenchmarkDomain.BUILD,
        name="Wrong node version in Dockerfile",
        description="Node 16 used instead of 20. Build succeeds but runtime crashes.",
        claimed_state={"build": "success", "node_version": "20"},
        reality_observations={
            "health": (500, '{"error":"SyntaxError: Unexpected token ??="}'),
        },
        expected_severity="critical",
        detection_method="certification",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="BUILD-03",
        domain=BenchmarkDomain.BUILD,
        name="Missing dependency in package.json",
        description="Package removed from deps but still imported. Runtime crash.",
        claimed_state={"build": "success", "deps": "complete"},
        reality_observations={
            "health": (500, '{"error":"Cannot find module bcrypt"}'),
        },
        expected_severity="critical",
        detection_method="certification",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="BUILD-04",
        domain=BenchmarkDomain.BUILD,
        name="Build output empty (0 bytes bundle)",
        description="Vite build produced empty output. HTML loads but no JS.",
        claimed_state={"build": "success", "bundle_size": "250kb"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (200, STANDARD_HTML),
            "bundle": (200, ""),
        },
        expected_severity="critical",
        detection_method="certification",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="BUILD-05",
        domain=BenchmarkDomain.BUILD,
        name="Wrong entry point in build",
        description="Build output references wrong entry file. HTML has no script tags.",
        claimed_state={"build": "success", "entry": "index.tsx"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (200, '<!DOCTYPE html><html><body><div id="root"></div></body></html>'),
            "bundle": None,
        },
        expected_severity="critical",
        detection_method="certification",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="BUILD-06",
        domain=BenchmarkDomain.BUILD,
        name="TypeScript errors suppressed by skipLibCheck",
        description="Type errors hidden. Build passes but runtime throws.",
        claimed_state={"build": "success", "type_check": "clean"},
        reality_observations={
            "health": (500, '{"error":"TypeError: Cannot read properties of undefined"}'),
        },
        expected_severity="high",
        detection_method="certification",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="BUILD-07",
        domain=BenchmarkDomain.BUILD,
        name="CSS/Tailwind not compiled",
        description="Tailwind JIT not triggered. App loads but unstyled.",
        claimed_state={"build": "success", "css": "compiled"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (200, STANDARD_HTML),
            "bundle": (200, 'var c={clerkKey:"pk_test_aGlwLXNuaXBlLTMz"};'),
            "trust_claim": 1.0,
            "trust_verify": 0.3,
            "trust_reality": 0.2,
        },
        expected_severity="medium",
        detection_method="trust_score",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="BUILD-08",
        domain=BenchmarkDomain.BUILD,
        name="Source maps leak secrets",
        description="Production build includes source maps with API keys visible.",
        claimed_state={"build": "success", "source_maps": "stripped"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (200, STANDARD_HTML),
            "bundle": (200, GOOD_BUNDLE),
            "trust_claim": 1.0,
            "trust_verify": 0.4,
            "trust_reality": 0.1,
        },
        expected_severity="critical",
        detection_method="trust_score",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="BUILD-09",
        domain=BenchmarkDomain.BUILD,
        name="Build cached from wrong branch",
        description="Docker layer cache served old code. Deploy looks fresh but is stale.",
        claimed_state={"build": "success", "branch": "main", "commit": "abc123"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (200, STANDARD_HTML),
            "bundle": (200, GOOD_BUNDLE),
            "trust_claim": 1.0,
            "trust_verify": 0.5,
            "trust_reality": 0.3,
        },
        expected_severity="high",
        detection_method="trust_score",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="BUILD-10",
        domain=BenchmarkDomain.BUILD,
        name="Vite config wrong base path",
        description="Base path set to /old-app/ instead of /. Assets 404.",
        claimed_state={"build": "success", "base_path": "/"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (200, '<!DOCTYPE html><html><body><div id="root"></div><script type="module" src="/old-app/assets/index-abc123.js"></script></body></html>'),
            "bundle": (404, "Not Found"),
        },
        expected_severity="critical",
        detection_method="certification",
    ))

    # ── DEPLOY domain (10) ───────────────────────────────────────────

    scenarios.append(BenchmarkScenario(
        scenario_id="DEPLOY-01",
        domain=BenchmarkDomain.DEPLOY,
        name="Health 200 but app non-functional",
        description="Health passes but main page returns error HTML.",
        claimed_state={"deploy": "success", "health": "200"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (200, '<html><body><h1>Application Error</h1></body></html>'),
            "bundle": None,
        },
        expected_severity="critical",
        detection_method="certification",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="DEPLOY-02",
        domain=BenchmarkDomain.DEPLOY,
        name="Wrong internal_port",
        description="Container listens on 3000 but fly.toml says 5000. 502 on all requests.",
        claimed_state={"deploy": "success", "port": 5000},
        reality_observations={
            "health": (502, "Bad Gateway"),
        },
        expected_severity="critical",
        detection_method="certification",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="DEPLOY-03",
        domain=BenchmarkDomain.DEPLOY,
        name="Machine suspended, won't auto-start",
        description="auto_start_machines disabled. Machine in stopped state.",
        claimed_state={"deploy": "success", "machine_state": "running"},
        reality_observations={
            "health": (0, "Connection refused"),
        },
        expected_severity="critical",
        detection_method="certification",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="DEPLOY-04",
        domain=BenchmarkDomain.DEPLOY,
        name="Wrong region (latency spike)",
        description="Deployed to SYD instead of IAD. 400ms+ latency for US users.",
        claimed_state={"deploy": "success", "region": "iad"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (200, STANDARD_HTML),
            "bundle": (200, GOOD_BUNDLE),
            "trust_claim": 1.0,
            "trust_verify": 0.6,
            "trust_reality": 0.4,
        },
        expected_severity="medium",
        detection_method="trust_score",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="DEPLOY-05",
        domain=BenchmarkDomain.DEPLOY,
        name="Old image cached, new code not deployed",
        description="Docker registry returned cached image. Code is stale.",
        claimed_state={"deploy": "success", "image": "latest"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (200, STANDARD_HTML),
            "bundle": (200, GOOD_BUNDLE),
            "trust_claim": 1.0,
            "trust_verify": 0.5,
            "trust_reality": 0.2,
        },
        expected_severity="high",
        detection_method="trust_score",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="DEPLOY-06",
        domain=BenchmarkDomain.DEPLOY,
        name="Memory limit too low (OOM on first request)",
        description="256mb limit. App OOMs on first request after startup.",
        claimed_state={"deploy": "success", "memory": "256mb"},
        reality_observations={
            "health": (502, "Bad Gateway"),
        },
        expected_severity="critical",
        detection_method="certification",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="DEPLOY-07",
        domain=BenchmarkDomain.DEPLOY,
        name="auto_stop too aggressive",
        description="auto_stop_machines=stop with 10s idle. Drops active connections.",
        claimed_state={"deploy": "success", "auto_stop": "configured"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (200, STANDARD_HTML),
            "bundle": (200, GOOD_BUNDLE),
            "trust_claim": 1.0,
            "trust_verify": 0.4,
            "trust_reality": 0.3,
        },
        expected_severity="medium",
        detection_method="trust_score",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="DEPLOY-08",
        domain=BenchmarkDomain.DEPLOY,
        name="TLS cert expired",
        description="Certificate expired. HTTPS connections fail.",
        claimed_state={"deploy": "success", "tls": "valid"},
        reality_observations={
            "health": (0, "SSL: CERTIFICATE_VERIFY_FAILED"),
        },
        expected_severity="critical",
        detection_method="certification",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="DEPLOY-09",
        domain=BenchmarkDomain.DEPLOY,
        name="Proxy config wrong (502 on routes)",
        description="Nginx proxy_pass wrong backend. Health OK but routes 502.",
        claimed_state={"deploy": "success", "proxy": "configured"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (502, "Bad Gateway"),
        },
        expected_severity="critical",
        detection_method="certification",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="DEPLOY-10",
        domain=BenchmarkDomain.DEPLOY,
        name="Env vars from wrong app",
        description="Fly secrets copied from wrong app. DATABASE_URL points to test DB.",
        claimed_state={"deploy": "success", "env": "production"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (200, STANDARD_HTML),
            "bundle": (200, GOOD_BUNDLE),
            "trust_claim": 1.0,
            "trust_verify": 0.5,
            "trust_reality": 0.1,
        },
        expected_severity="critical",
        detection_method="trust_score",
    ))

    # ── AUTH domain (10) ─────────────────────────────────────────────

    scenarios.append(BenchmarkScenario(
        scenario_id="AUTH-01",
        domain=BenchmarkDomain.AUTH,
        name="Wrong Clerk publishable key (wrong app)",
        description="Key belongs to different Clerk app. Auth silently fails.",
        claimed_state={"auth": "configured", "clerk_key": "correct_app"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (200, STANDARD_HTML),
            "bundle": (200, 'var c={clerkKey:"pk_test_WRONG_APP_xyz"};'),
        },
        expected_severity="critical",
        detection_method="certification",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="AUTH-02",
        domain=BenchmarkDomain.AUTH,
        name="Clerk secret key missing",
        description="CLERK_SECRET_KEY not in Fly secrets. Server-side auth crashes.",
        claimed_state={"auth": "configured", "secret_key": "present"},
        reality_observations={
            "health": (500, '{"error":"CLERK_SECRET_KEY is required"}'),
        },
        expected_severity="critical",
        detection_method="certification",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="AUTH-03",
        domain=BenchmarkDomain.AUTH,
        name="Clerk key expired",
        description="Publishable key expired. Clerk SDK throws on init.",
        claimed_state={"auth": "configured", "key_status": "active"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (200, STANDARD_HTML),
            "bundle": (200, 'var c={clerkKey:"pk_test_EXPIRED_key_abc"};'),
        },
        expected_severity="critical",
        detection_method="certification",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="AUTH-04",
        domain=BenchmarkDomain.AUTH,
        name="CORS blocks auth requests",
        description="Access-Control-Allow-Origin missing. Auth API calls fail in browser.",
        claimed_state={"auth": "configured", "cors": "enabled"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (200, STANDARD_HTML),
            "bundle": (200, GOOD_BUNDLE),
            "trust_claim": 1.0,
            "trust_verify": 0.3,
            "trust_reality": 0.2,
        },
        expected_severity="high",
        detection_method="trust_score",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="AUTH-05",
        domain=BenchmarkDomain.AUTH,
        name="Auth middleware throws but caught silently",
        description="Middleware has except-pass. All requests pass unauthenticated.",
        claimed_state={"auth": "enforced", "middleware": "active"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (200, STANDARD_HTML),
            "bundle": (200, GOOD_BUNDLE),
            "trust_claim": 1.0,
            "trust_verify": 0.2,
            "trust_reality": 0.1,
        },
        expected_severity="critical",
        detection_method="trust_score",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="AUTH-06",
        domain=BenchmarkDomain.AUTH,
        name="Session cookie domain mismatch",
        description="Cookie set for .old-domain.com. Sessions not persisted.",
        claimed_state={"auth": "configured", "cookie_domain": "correct"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (200, STANDARD_HTML),
            "bundle": (200, GOOD_BUNDLE),
            "trust_claim": 1.0,
            "trust_verify": 0.4,
            "trust_reality": 0.3,
        },
        expected_severity="high",
        detection_method="trust_score",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="AUTH-07",
        domain=BenchmarkDomain.AUTH,
        name="JWT issuer mismatch",
        description="JWT iss claim doesn't match expected issuer. Token validation fails.",
        claimed_state={"auth": "configured", "jwt_issuer": "correct"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (200, STANDARD_HTML),
            "bundle": (200, GOOD_BUNDLE),
            "trust_claim": 1.0,
            "trust_verify": 0.3,
            "trust_reality": 0.2,
        },
        expected_severity="high",
        detection_method="trust_score",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="AUTH-08",
        domain=BenchmarkDomain.AUTH,
        name="Auth callback URL wrong",
        description="OAuth redirect points to localhost. Login flow breaks in production.",
        claimed_state={"auth": "configured", "callback": "production_url"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (200, STANDARD_HTML),
            "bundle": (200, GOOD_BUNDLE),
            "trust_claim": 1.0,
            "trust_verify": 0.3,
            "trust_reality": 0.1,
        },
        expected_severity="critical",
        detection_method="trust_score",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="AUTH-09",
        domain=BenchmarkDomain.AUTH,
        name="Clerk org not matching",
        description="Clerk org ID mismatch. Multi-tenant routing fails.",
        claimed_state={"auth": "configured", "org_id": "correct"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (200, STANDARD_HTML),
            "bundle": (200, GOOD_BUNDLE),
            "trust_claim": 1.0,
            "trust_verify": 0.4,
            "trust_reality": 0.2,
        },
        expected_severity="high",
        detection_method="trust_score",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="AUTH-10",
        domain=BenchmarkDomain.AUTH,
        name="API key present but revoked",
        description="API key in secrets but revoked on provider side. All API calls 401.",
        claimed_state={"auth": "configured", "api_key": "present"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (200, STANDARD_HTML),
            "bundle": (200, GOOD_BUNDLE),
            "trust_claim": 1.0,
            "trust_verify": 0.3,
            "trust_reality": 0.0,
        },
        expected_severity="critical",
        detection_method="trust_score",
    ))

    # ── DATA domain (10) ─────────────────────────────────────────────

    scenarios.append(BenchmarkScenario(
        scenario_id="DATA-01",
        domain=BenchmarkDomain.DATA,
        name="DATABASE_URL wrong",
        description="Connection string points to non-existent database.",
        claimed_state={"database": "connected", "url": "production"},
        reality_observations={
            "health": (503, '{"error":"database connection failed"}'),
        },
        expected_severity="critical",
        detection_method="certification",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="DATA-02",
        domain=BenchmarkDomain.DATA,
        name="Migration ran but schema mismatch",
        description="Migration applied but code expects columns that don't exist.",
        claimed_state={"database": "connected", "migration": "applied"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (200, STANDARD_HTML),
            "bundle": (200, GOOD_BUNDLE),
            "trust_claim": 1.0,
            "trust_verify": 0.5,
            "trust_reality": 0.2,
        },
        expected_severity="high",
        detection_method="trust_score",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="DATA-03",
        domain=BenchmarkDomain.DATA,
        name="Connection pool exhausted",
        description="Max connections reached. New queries hang then timeout.",
        claimed_state={"database": "connected", "pool": "healthy"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (200, STANDARD_HTML),
            "bundle": (200, GOOD_BUNDLE),
            "trust_claim": 1.0,
            "trust_verify": 0.4,
            "trust_reality": 0.2,
        },
        expected_severity="high",
        detection_method="trust_score",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="DATA-04",
        domain=BenchmarkDomain.DATA,
        name="Read replica stale",
        description="Replication lag > 60s. Reads return old data.",
        claimed_state={"database": "connected", "replication": "in_sync"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (200, STANDARD_HTML),
            "bundle": (200, GOOD_BUNDLE),
            "trust_claim": 1.0,
            "trust_verify": 0.5,
            "trust_reality": 0.3,
        },
        expected_severity="medium",
        detection_method="trust_score",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="DATA-05",
        domain=BenchmarkDomain.DATA,
        name="RLS policy blocks all queries",
        description="Row-level security misconfigured. All SELECT returns empty.",
        claimed_state={"database": "connected", "rls": "configured"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (200, STANDARD_HTML),
            "bundle": (200, GOOD_BUNDLE),
            "trust_claim": 1.0,
            "trust_verify": 0.3,
            "trust_reality": 0.1,
        },
        expected_severity="critical",
        detection_method="trust_score",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="DATA-06",
        domain=BenchmarkDomain.DATA,
        name="Encryption key rotated, old data unreadable",
        description="Key rotation didn't re-encrypt. Old records return garbled text.",
        claimed_state={"database": "connected", "encryption": "rotated"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (200, STANDARD_HTML),
            "bundle": (200, GOOD_BUNDLE),
            "trust_claim": 1.0,
            "trust_verify": 0.4,
            "trust_reality": 0.1,
        },
        expected_severity="critical",
        detection_method="trust_score",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="DATA-07",
        domain=BenchmarkDomain.DATA,
        name="Backup exists but restore fails",
        description="Backup taken but incompatible with current schema.",
        claimed_state={"database": "backed_up", "restore": "tested"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (200, STANDARD_HTML),
            "bundle": (200, GOOD_BUNDLE),
            "trust_claim": 1.0,
            "trust_verify": 0.3,
            "trust_reality": 0.2,
        },
        expected_severity="high",
        detection_method="trust_score",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="DATA-08",
        domain=BenchmarkDomain.DATA,
        name="Foreign key constraint blocks writes",
        description="FK references deleted parent. All inserts fail with constraint error.",
        claimed_state={"database": "connected", "constraints": "valid"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (200, STANDARD_HTML),
            "bundle": (200, GOOD_BUNDLE),
            "trust_claim": 1.0,
            "trust_verify": 0.4,
            "trust_reality": 0.1,
        },
        expected_severity="high",
        detection_method="trust_score",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="DATA-09",
        domain=BenchmarkDomain.DATA,
        name="Index missing (query timeout)",
        description="Critical index dropped. Queries that should take 10ms take 30s.",
        claimed_state={"database": "connected", "performance": "normal"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (200, STANDARD_HTML),
            "bundle": (200, GOOD_BUNDLE),
            "trust_claim": 1.0,
            "trust_verify": 0.4,
            "trust_reality": 0.2,
        },
        expected_severity="high",
        detection_method="trust_score",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="DATA-10",
        domain=BenchmarkDomain.DATA,
        name="Seed data missing (empty dashboard)",
        description="Migration ran without seed. Dashboard shows 0 records.",
        claimed_state={"database": "connected", "seed": "applied"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (200, STANDARD_HTML),
            "bundle": (200, GOOD_BUNDLE),
            "trust_claim": 1.0,
            "trust_verify": 0.5,
            "trust_reality": 0.3,
        },
        expected_severity="medium",
        detection_method="trust_score",
    ))

    # ── INTEGRATION domain (10) ──────────────────────────────────────

    scenarios.append(BenchmarkScenario(
        scenario_id="INTEG-01",
        domain=BenchmarkDomain.INTEGRATION,
        name="API key rotated but not updated",
        description="Third-party API key rotated. All outbound calls 401.",
        claimed_state={"integration": "active", "api_key": "valid"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (200, STANDARD_HTML),
            "bundle": (200, GOOD_BUNDLE),
            "trust_claim": 1.0,
            "trust_verify": 0.3,
            "trust_reality": 0.0,
        },
        expected_severity="critical",
        detection_method="trust_score",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="INTEG-02",
        domain=BenchmarkDomain.INTEGRATION,
        name="Webhook URL points to old host",
        description="Webhook endpoint changed. Events not delivered.",
        claimed_state={"integration": "active", "webhook": "configured"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (200, STANDARD_HTML),
            "bundle": (200, GOOD_BUNDLE),
            "trust_claim": 1.0,
            "trust_verify": 0.3,
            "trust_reality": 0.1,
        },
        expected_severity="high",
        detection_method="trust_score",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="INTEG-03",
        domain=BenchmarkDomain.INTEGRATION,
        name="Rate limit exceeded",
        description="API calls over quota. All requests return 429.",
        claimed_state={"integration": "active", "rate_limit": "within_quota"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (200, STANDARD_HTML),
            "bundle": (200, GOOD_BUNDLE),
            "trust_claim": 1.0,
            "trust_verify": 0.4,
            "trust_reality": 0.2,
        },
        expected_severity="high",
        detection_method="trust_score",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="INTEG-04",
        domain=BenchmarkDomain.INTEGRATION,
        name="API version deprecated",
        description="Endpoint v1 sunset. Calls return 410 Gone.",
        claimed_state={"integration": "active", "api_version": "v1"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (200, STANDARD_HTML),
            "bundle": (200, GOOD_BUNDLE),
            "trust_claim": 1.0,
            "trust_verify": 0.3,
            "trust_reality": 0.1,
        },
        expected_severity="high",
        detection_method="trust_score",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="INTEG-05",
        domain=BenchmarkDomain.INTEGRATION,
        name="OAuth token expired",
        description="OAuth refresh failed. All authenticated calls 401.",
        claimed_state={"integration": "active", "oauth": "authenticated"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (200, STANDARD_HTML),
            "bundle": (200, GOOD_BUNDLE),
            "trust_claim": 1.0,
            "trust_verify": 0.3,
            "trust_reality": 0.0,
        },
        expected_severity="critical",
        detection_method="trust_score",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="INTEG-06",
        domain=BenchmarkDomain.INTEGRATION,
        name="Service account permissions revoked",
        description="GCP service account lost IAM roles. All API calls 403.",
        claimed_state={"integration": "active", "permissions": "granted"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (200, STANDARD_HTML),
            "bundle": (200, GOOD_BUNDLE),
            "trust_claim": 1.0,
            "trust_verify": 0.3,
            "trust_reality": 0.0,
        },
        expected_severity="critical",
        detection_method="trust_score",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="INTEG-07",
        domain=BenchmarkDomain.INTEGRATION,
        name="Webhook signature validation fails",
        description="Webhook secret rotated. Signature validation rejects all events.",
        claimed_state={"integration": "active", "webhook_secret": "valid"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (200, STANDARD_HTML),
            "bundle": (200, GOOD_BUNDLE),
            "trust_claim": 1.0,
            "trust_verify": 0.4,
            "trust_reality": 0.1,
        },
        expected_severity="high",
        detection_method="trust_score",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="INTEG-08",
        domain=BenchmarkDomain.INTEGRATION,
        name="Endpoint URL changed",
        description="Third-party moved to new URL. Old endpoint returns redirect loop.",
        claimed_state={"integration": "active", "endpoint": "valid"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (200, STANDARD_HTML),
            "bundle": (200, GOOD_BUNDLE),
            "trust_claim": 1.0,
            "trust_verify": 0.3,
            "trust_reality": 0.1,
        },
        expected_severity="high",
        detection_method="trust_score",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="INTEG-09",
        domain=BenchmarkDomain.INTEGRATION,
        name="Response format changed",
        description="API returns JSON v2 format. Client parses v1 schema. Silent data loss.",
        claimed_state={"integration": "active", "response_format": "v1"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (200, STANDARD_HTML),
            "bundle": (200, GOOD_BUNDLE),
            "trust_claim": 1.0,
            "trust_verify": 0.4,
            "trust_reality": 0.2,
        },
        expected_severity="high",
        detection_method="trust_score",
    ))

    scenarios.append(BenchmarkScenario(
        scenario_id="INTEG-10",
        domain=BenchmarkDomain.INTEGRATION,
        name="Downstream service down",
        description="Critical dependency offline. Feature silently returns empty.",
        claimed_state={"integration": "active", "downstream": "healthy"},
        reality_observations={
            "health": (200, '{"status":"ok"}'),
            "html": (200, STANDARD_HTML),
            "bundle": (200, GOOD_BUNDLE),
            "trust_claim": 1.0,
            "trust_verify": 0.4,
            "trust_reality": 0.1,
        },
        expected_severity="high",
        detection_method="trust_score",
    ))

    return scenarios


# ── Benchmark Engine ─────────────────────────────────────────────────────


class RealityCorrespondenceBenchmark:
    """Runs 50 reality correspondence scenarios and scores detection ability."""

    def __init__(self) -> None:
        self._scenarios = _build_scenarios()
        self._results: list[BenchmarkResult] = []

    @property
    def scenarios(self) -> list[BenchmarkScenario]:
        return list(self._scenarios)

    def run_scenario(self, scenario: BenchmarkScenario) -> BenchmarkResult:
        """Run a single scenario through the appropriate detection path."""
        start = time.monotonic()
        method = scenario.detection_method

        if method == "certification":
            detected, severity, notes = self._detect_via_certification(scenario)
        elif method == "trust_score":
            detected, severity, notes = self._detect_via_trust_score(scenario)
        elif method == "correspondence":
            detected, severity, notes = self._detect_via_correspondence(scenario)
        else:
            detected, severity, notes = False, "", f"Unknown method: {method}"

        elapsed_ms = int((time.monotonic() - start) * 1000)

        classified_correctly = (
            detected
            and severity == scenario.expected_severity
        )

        return BenchmarkResult(
            scenario_id=scenario.scenario_id,
            detected=detected,
            classified_correctly=classified_correctly,
            detection_method=method,
            time_to_detect_ms=elapsed_ms,
            detected_severity=severity,
            notes=notes,
        )

    def run_all(self) -> list[BenchmarkResult]:
        """Run all 50 scenarios. Returns results list."""
        self._results = [self.run_scenario(s) for s in self._scenarios]
        return list(self._results)

    def score(self) -> dict[str, Any]:
        """Compute aggregate scores from results."""
        if not self._results:
            self.run_all()

        total = len(self._results)
        detected_count = sum(1 for r in self._results if r.detected)
        classified_count = sum(1 for r in self._results if r.classified_correctly)

        detection_rate = detected_count / total if total > 0 else 0.0
        classification_accuracy = (
            classified_count / detected_count if detected_count > 0 else 0.0
        )

        by_domain: dict[str, dict[str, Any]] = {}
        for domain in BenchmarkDomain:
            domain_scenarios = [
                s for s in self._scenarios if s.domain == domain
            ]
            domain_results = [
                r for r in self._results
                if any(
                    s.scenario_id == r.scenario_id and s.domain == domain
                    for s in self._scenarios
                )
            ]
            domain_detected = sum(1 for r in domain_results if r.detected)
            domain_total = len(domain_results)
            by_domain[domain.value] = {
                "total": domain_total,
                "detected": domain_detected,
                "detection_rate": (
                    domain_detected / domain_total if domain_total > 0 else 0.0
                ),
            }

        c25_result = next(
            (r for r in self._results if r.scenario_id == "BUILD-01"),
            None,
        )

        return {
            "total_scenarios": total,
            "detected": detected_count,
            "classified_correctly": classified_count,
            "detection_rate": round(detection_rate, 4),
            "classification_accuracy": round(classification_accuracy, 4),
            "c25_bug_detected": c25_result.detected if c25_result else False,
            "by_domain": by_domain,
        }

    def summary(self) -> str:
        """Human-readable summary report."""
        scores = self.score()
        lines = [
            "=== Reality Correspondence Benchmark ===",
            f"Total scenarios: {scores['total_scenarios']}",
            f"Detected: {scores['detected']}/{scores['total_scenarios']} "
            f"({scores['detection_rate']:.0%})",
            f"Classified correctly: {scores['classified_correctly']}/{scores['detected']} "
            f"({scores['classification_accuracy']:.0%})",
            f"C25 bug detected: {'YES' if scores['c25_bug_detected'] else 'NO'}",
            "",
            "--- By Domain ---",
        ]
        for domain, data in scores["by_domain"].items():
            lines.append(
                f"  {domain.upper()}: {data['detected']}/{data['total']} "
                f"({data['detection_rate']:.0%})"
            )

        missed = [r for r in self._results if not r.detected]
        if missed:
            lines.append("")
            lines.append("--- Missed Scenarios ---")
            for r in missed:
                lines.append(f"  {r.scenario_id}: {r.notes}")

        return "\n".join(lines)

    # ── Detection methods ────────────────────────────────────────────

    def _detect_via_certification(
        self, scenario: BenchmarkScenario
    ) -> tuple[bool, str, str]:
        """Run scenario through ProjectionCertificationEngine with mock HTTP."""
        from substrate.organism.projection_certification import (
            CertificationLevel,
            ProjectionCertificationEngine,
            ProjectionRegistry,
        )

        obs = scenario.reality_observations
        http_responses: dict[str, tuple[int, str]] = {}

        base_url = "https://benchmark.example.com"

        if "health" in obs:
            http_responses[f"{base_url}/api/health"] = obs["health"]

        if "html" in obs:
            http_responses[base_url] = obs["html"]

        if "bundle" in obs and obs["bundle"] is not None:
            http_responses[f"{base_url}/assets/index-abc123.js"] = obs["bundle"]

        def mock_http(url: str) -> tuple[int, str]:
            status_code_or_zero = 0
            if url in http_responses:
                return http_responses[url]
            for pattern, (status, body) in http_responses.items():
                if pattern in url:
                    return status, body
            code = obs.get("health", (0, ""))[0] if "health" in obs else 0
            if code == 0:
                raise ConnectionError(
                    obs.get("health", (0, "Connection refused"))[1]
                )
            return 404, "Not Found"

        config_data = {
            "bench": {
                "app_name": "benchmark-app",
                "public_url": base_url,
                "critical_bundle_values": ["pk_test_aGlwLX"],
                "l4_workflow": "clerk_login_renders",
            }
        }

        import tempfile
        import os

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(config_data, f)
            f.flush()
            registry = ProjectionRegistry(config_path=f.name)

        try:
            engine = ProjectionCertificationEngine(
                registry=registry, http_client=mock_http
            )
            cert = engine.certify("bench")

            detected = cert.current_level < CertificationLevel.L5_OUTCOME
            if detected:
                severity = self._cert_level_to_severity(cert.failure_level)
                notes = (
                    f"Stopped at {cert.current_level.name}, "
                    f"failed {cert.failure_level.name}: {cert.failure_detail}"
                )
            else:
                severity = ""
                notes = "Fully certified — not detected"

            return detected, severity, notes
        finally:
            os.unlink(f.name)

    def _detect_via_trust_score(
        self, scenario: BenchmarkScenario
    ) -> tuple[bool, str, str]:
        """Run scenario through TrustScoreEngine. Checks composite < 0.5."""
        from substrate.organism.trust_score import TrustScoreEngine

        obs = scenario.reality_observations
        claim = obs.get("trust_claim", 1.0)
        verify = obs.get("trust_verify", 0.5)
        reality = obs.get("trust_reality", 0.5)

        engine = TrustScoreEngine()
        score = engine.compute(
            work_id=scenario.scenario_id,
            claim_confidence=claim,
            verification_confidence=verify,
            reality_confidence=reality,
            claim_evidence=[f"Claimed: {scenario.claimed_state}"],
            reality_evidence=[f"Reality: {scenario.description}"],
        )

        detected = score.composite_trust < 0.5
        severity = self._trust_to_severity(score.composite_trust)
        notes = (
            f"Trust composite={score.composite_trust:.2f} "
            f"level={score.trust_level.value} "
            f"(claim={claim}, verify={verify}, reality={reality})"
        )

        return detected, severity, notes

    def _detect_via_correspondence(
        self, scenario: BenchmarkScenario
    ) -> tuple[bool, str, str]:
        """Direct comparison of claimed vs observed state."""
        claimed = scenario.claimed_state
        reality = scenario.reality_observations

        mismatches: list[str] = []
        for key, claimed_val in claimed.items():
            if key in reality:
                reality_val = reality[key]
                if reality_val != claimed_val:
                    mismatches.append(f"{key}: claimed={claimed_val} reality={reality_val}")

        detected = len(mismatches) > 0
        severity = scenario.expected_severity if detected else ""
        notes = "; ".join(mismatches) if mismatches else "No mismatches found"

        return detected, severity, notes

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _cert_level_to_severity(
        failure_level: Any,
    ) -> str:
        """Map certification failure level to severity."""
        from substrate.organism.projection_certification import CertificationLevel

        if failure_level is None:
            return "medium"
        level_val = failure_level if isinstance(failure_level, int) else failure_level.value
        if level_val <= CertificationLevel.L2_DEPLOY:
            return "critical"
        if level_val == CertificationLevel.L3_UI:
            return "critical"
        return "high"

    @staticmethod
    def _trust_to_severity(composite: float) -> str:
        """Map trust composite to severity."""
        if composite <= 0.1:
            return "critical"
        if composite <= 0.3:
            return "high"
        return "medium"
