"""Diagnostic scan orchestrator for UMH reality model population.

Phase 6 deep scan — extends the basic discovery.py with per-domain
analysis when adapters and permissions are available. Each domain
scan is gated by the permission system (umh/permissions.py).

Without adapters: runs basic environment discovery (same as discovery.py)
With adapters:    runs deep per-domain analysis (calendar, email, code, etc.)

The scan orchestrator manages progress tracking, domain prioritization,
and result aggregation. Individual domain scans are delegated to their
respective adapters when available.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

UMH_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
SCAN_DIR = os.path.join(UMH_ROOT, "data", "diagnostic_scans")


class ScanDomain(str, Enum):
    """Domains that the diagnostic scan covers."""

    CALENDAR = "calendar"
    COMMUNICATIONS = "communications"
    CODE = "code"
    DOCUMENTS = "documents"
    FINANCIAL = "financial"
    PHYSICAL_ENVIRONMENT = "physical_environment"


class DomainScanStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"
    NO_PERMISSION = "no_permission"
    NO_ADAPTER = "no_adapter"


@dataclass
class DomainScanResult:
    """Result of scanning a single domain."""

    domain: ScanDomain
    status: DomainScanStatus = DomainScanStatus.PENDING
    entities_found: int = 0
    relationships_found: int = 0
    observations: list[str] = field(default_factory=list)
    error: str = ""
    started_at: str = ""
    completed_at: str = ""
    duration_seconds: float = 0.0

    def to_dict(self) -> dict:
        return {
            "domain": self.domain.value,
            "status": self.status.value,
            "entities_found": self.entities_found,
            "relationships_found": self.relationships_found,
            "observations": self.observations,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_seconds": self.duration_seconds,
        }


DOMAIN_PERMISSION_MAP: dict[ScanDomain, list[str]] = {
    ScanDomain.CALENDAR: ["calendar_read"],
    ScanDomain.COMMUNICATIONS: ["email_read", "slack_read", "discord_read"],
    ScanDomain.CODE: ["github_read", "file_system"],
    ScanDomain.DOCUMENTS: ["drive_read", "file_system"],
    ScanDomain.FINANCIAL: ["network_requests"],
    ScanDomain.PHYSICAL_ENVIRONMENT: ["webcam", "system_metrics"],
}


@dataclass
class DiagnosticScanResult:
    """Aggregated result of the full diagnostic scan."""

    domains_scanned: int = 0
    domains_completed: int = 0
    domains_skipped: int = 0
    total_entities: int = 0
    total_relationships: int = 0
    domain_results: dict[str, DomainScanResult] = field(default_factory=dict)
    maturity_level: str = "L0_NO_SCAN"
    started_at: str = ""
    completed_at: str = ""
    duration_seconds: float = 0.0
    includes_basic_discovery: bool = False

    def to_dict(self) -> dict:
        return {
            "domains_scanned": self.domains_scanned,
            "domains_completed": self.domains_completed,
            "domains_skipped": self.domains_skipped,
            "total_entities": self.total_entities,
            "total_relationships": self.total_relationships,
            "domain_results": {k: v.to_dict() for k, v in self.domain_results.items()},
            "maturity_level": self.maturity_level,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_seconds": self.duration_seconds,
            "includes_basic_discovery": self.includes_basic_discovery,
        }


class DiagnosticScanner:
    """Orchestrates deep diagnostic scans across all domains.

    Checks permissions before scanning each domain. Falls back to
    basic discovery (umh/discovery.py) when no adapters are available.
    """

    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._result: DiagnosticScanResult | None = None
        self._running = False
        self._progress: dict[str, str] = {}

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def result(self) -> DiagnosticScanResult | None:
        return self._result

    @property
    def progress(self) -> dict[str, str]:
        return dict(self._progress)

    def start_scan(self, background: bool = True) -> bool:
        """Start the diagnostic scan.

        If background=True, runs in a daemon thread.
        If background=False, runs synchronously (blocking).
        """
        if self._running:
            return False
        self._running = True
        self._result = None
        self._progress = {}

        if background:
            self._thread = threading.Thread(
                target=self._run_scan, daemon=True, name="umh-diagnostic-scan"
            )
            self._thread.start()
        else:
            self._run_scan()
        return True

    def _run_scan(self) -> None:
        result = DiagnosticScanResult(
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        start = datetime.now(timezone.utc)

        try:
            # Run basic discovery first
            self._progress["basic_discovery"] = "running"
            basic = self._run_basic_discovery()
            if basic:
                result.includes_basic_discovery = True
                result.total_entities += basic.get("platforms_found", 0)
            self._progress["basic_discovery"] = "completed"

            # Scan each domain
            for domain in ScanDomain:
                self._progress[domain.value] = "checking_permissions"
                domain_result = self._scan_domain(domain)
                result.domain_results[domain.value] = domain_result
                result.domains_scanned += 1

                if domain_result.status == DomainScanStatus.COMPLETED:
                    result.domains_completed += 1
                    result.total_entities += domain_result.entities_found
                    result.total_relationships += domain_result.relationships_found
                elif domain_result.status in (
                    DomainScanStatus.SKIPPED,
                    DomainScanStatus.NO_PERMISSION,
                    DomainScanStatus.NO_ADAPTER,
                ):
                    result.domains_skipped += 1

                self._progress[domain.value] = domain_result.status.value

            end = datetime.now(timezone.utc)
            result.duration_seconds = (end - start).total_seconds()
            result.completed_at = end.isoformat()
            result.maturity_level = self._calculate_maturity(result)

            self._save_result(result)
            self._result = result

            logger.info(
                "Diagnostic scan complete: %d/%d domains, %d entities (%.1fs)",
                result.domains_completed,
                result.domains_scanned,
                result.total_entities,
                result.duration_seconds,
            )
        except Exception as exc:
            logger.debug("Diagnostic scan failed: %s", exc)
        finally:
            self._running = False

    def _scan_domain(self, domain: ScanDomain) -> DomainScanResult:
        """Scan a single domain, checking permissions first."""
        dr = DomainScanResult(
            domain=domain,
            started_at=datetime.now(timezone.utc).isoformat(),
        )

        if not self._has_permission(domain):
            dr.status = DomainScanStatus.NO_PERMISSION
            return dr

        start = datetime.now(timezone.utc)

        try:
            if domain == ScanDomain.CODE:
                dr = self._scan_code(dr)
            elif domain == ScanDomain.PHYSICAL_ENVIRONMENT:
                dr = self._scan_physical(dr)
            else:
                dr.status = DomainScanStatus.NO_ADAPTER
                dr.observations.append(
                    f"No adapter available for {domain.value} — will scan when adapter is registered"
                )
        except Exception as exc:
            dr.status = DomainScanStatus.FAILED
            dr.error = str(exc)
            logger.debug("Domain scan failed for %s: %s", domain.value, exc)

        end = datetime.now(timezone.utc)
        dr.duration_seconds = (end - start).total_seconds()
        dr.completed_at = end.isoformat()
        return dr

    def _has_permission(self, domain: ScanDomain) -> bool:
        """Check if we have permission to scan this domain."""
        required = DOMAIN_PERMISSION_MAP.get(domain, [])
        if not required:
            return True

        try:
            from umh.permissions import PermissionScope, PermissionStore

            store = PermissionStore()
            for scope_name in required:
                try:
                    scope = PermissionScope(scope_name)
                    if store.is_allowed(scope):
                        return True
                except ValueError:
                    continue
            return False
        except Exception as exc:
            logger.debug("Permission check failed for %s: %s", domain.value, exc)
            return False

    def _scan_code(self, dr: DomainScanResult) -> DomainScanResult:
        """Scan code repositories — works without external adapters."""
        import subprocess

        repos: list[str] = []
        search_dirs = [
            os.path.expanduser("~"),
            "/opt",
        ]

        for base in search_dirs:
            if not os.path.isdir(base):
                continue
            try:
                result = subprocess.run(
                    ["find", base, "-maxdepth", "3", "-name", ".git", "-type", "d"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    for line in result.stdout.strip().split("\n"):
                        if line:
                            repos.append(os.path.dirname(line))
            except Exception as exc:
                logger.debug("Git repo discovery failed for %s: %s", base, exc)

        dr.entities_found = len(repos)
        for repo in repos[:10]:
            dr.observations.append(f"repo: {repo}")

        languages: set[str] = set()
        for repo in repos[:5]:
            for ext, lang in {
                ".py": "Python",
                ".ts": "TypeScript",
                ".js": "JavaScript",
                ".go": "Go",
                ".rs": "Rust",
            }.items():
                try:
                    result = subprocess.run(
                        ["find", repo, "-maxdepth", "2", "-name", f"*{ext}", "-type", "f"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        languages.add(lang)
                except Exception as exc:
                    logger.debug("Language scan failed for %s in %s: %s", ext, repo, exc)

        if languages:
            dr.observations.append(f"languages: {', '.join(sorted(languages))}")
            dr.relationships_found = len(languages)

        dr.status = DomainScanStatus.COMPLETED
        return dr

    def _scan_physical(self, dr: DomainScanResult) -> DomainScanResult:
        """Scan physical environment — system info, hardware."""
        import platform

        observations = [
            f"os: {platform.system()} {platform.release()}",
            f"machine: {platform.machine()}",
            f"hostname: {platform.node()}",
        ]

        try:
            import psutil

            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            observations.append(f"ram: {mem.total // (1024**3)} GB")
            observations.append(f"disk: {disk.total // (1024**3)} GB ({disk.percent}% used)")
            observations.append(f"cpu_cores: {psutil.cpu_count()}")
            dr.entities_found = 3
        except ImportError as exc:
            logger.debug("psutil not available: %s", exc)

        dr.observations = observations
        dr.status = DomainScanStatus.COMPLETED
        return dr

    def _run_basic_discovery(self) -> dict | None:
        """Run the basic discovery scanner as a foundation."""
        try:
            from umh.discovery import DiscoveryScanner

            scanner = DiscoveryScanner()
            scanner.start_background_scan()
            import time

            timeout = 30
            while scanner.is_running and timeout > 0:
                time.sleep(0.5)
                timeout -= 0.5

            if scanner.result:
                return scanner.result.as_dict()
            return None
        except Exception as exc:
            logger.debug("Basic discovery failed: %s", exc)
            return None

    def _calculate_maturity(self, result: DiagnosticScanResult) -> str:
        if result.domains_completed == 0:
            return "L0_NO_SCAN" if not result.includes_basic_discovery else "L1_BASIC_SCAN"
        if result.domains_completed <= 2:
            return "L2_PARTIAL_SCAN"
        if result.domains_completed <= 4:
            return "L3_MODERATE_SCAN"
        return "L4_COMPREHENSIVE_SCAN"

    def _save_result(self, result: DiagnosticScanResult) -> None:
        os.makedirs(SCAN_DIR, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
        path = os.path.join(SCAN_DIR, f"diagnostic_{timestamp}.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(result.to_dict(), f, indent=2)
        except Exception as exc:
            logger.debug("Failed to save diagnostic scan: %s", exc)

    def get_latest_result(self) -> DiagnosticScanResult | None:
        if not os.path.isdir(SCAN_DIR):
            return None
        files = sorted(
            (f for f in os.listdir(SCAN_DIR) if f.startswith("diagnostic_")),
            reverse=True,
        )
        if not files:
            return None
        try:
            path = os.path.join(SCAN_DIR, files[0])
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            result = DiagnosticScanResult(
                domains_scanned=data.get("domains_scanned", 0),
                domains_completed=data.get("domains_completed", 0),
                domains_skipped=data.get("domains_skipped", 0),
                total_entities=data.get("total_entities", 0),
                total_relationships=data.get("total_relationships", 0),
                maturity_level=data.get("maturity_level", "L0_NO_SCAN"),
                started_at=data.get("started_at", ""),
                completed_at=data.get("completed_at", ""),
                duration_seconds=data.get("duration_seconds", 0.0),
                includes_basic_discovery=data.get("includes_basic_discovery", False),
            )
            for k, v in data.get("domain_results", {}).items():
                result.domain_results[k] = DomainScanResult(
                    domain=ScanDomain(v["domain"]),
                    status=DomainScanStatus(v["status"]),
                    entities_found=v.get("entities_found", 0),
                    relationships_found=v.get("relationships_found", 0),
                    observations=v.get("observations", []),
                    error=v.get("error", ""),
                )
            return result
        except Exception as exc:
            logger.debug("Failed to load diagnostic scan: %s", exc)
            return None

    def display_result(self, result: DiagnosticScanResult | None = None) -> None:
        r = result or self._result
        if r is None:
            r = self.get_latest_result()
        if r is None:
            print("  No diagnostic scan results available.")
            print("  Run `umh scan` to start one.")
            return

        print()
        print("=" * 50)
        print("  UMH Diagnostic Scan Results")
        print("=" * 50)
        print(f"  Maturity:       {r.maturity_level}")
        print(f"  Domains:        {r.domains_completed}/{r.domains_scanned} completed")
        print(f"  Entities:       {r.total_entities}")
        print(f"  Relationships:  {r.total_relationships}")
        print(f"  Duration:       {r.duration_seconds:.1f}s")
        print()

        status_icons = {
            "completed": "+",
            "skipped": "~",
            "failed": "!",
            "no_permission": "-",
            "no_adapter": ".",
            "pending": " ",
            "running": ">",
        }

        for domain in ScanDomain:
            dr = r.domain_results.get(domain.value)
            if dr:
                icon = status_icons.get(dr.status.value, "?")
                detail = ""
                if dr.status == DomainScanStatus.COMPLETED:
                    detail = f" ({dr.entities_found} entities)"
                elif dr.status == DomainScanStatus.NO_PERMISSION:
                    detail = " (no permission)"
                elif dr.status == DomainScanStatus.NO_ADAPTER:
                    detail = " (no adapter yet)"
                elif dr.status == DomainScanStatus.FAILED:
                    detail = f" (error: {dr.error[:30]})"
                print(f"  [{icon}] {domain.value:<25s}{detail}")

        print()
        print("  Legend: [+] done  [~] skipped  [!] error  [-] no permission  [.] no adapter")
        print("=" * 50)
        print()


def show_diagnostic_scan() -> int:
    scanner = DiagnosticScanner()
    scanner.display_result()
    return 0
