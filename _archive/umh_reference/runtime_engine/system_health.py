"""
System health check for EOS session startup and heartbeat.

Provides quick container and service status used by:
- tools/session_start_context.py (SessionStart hook)
- tools/heartbeat.py (periodic health check)
"""

import subprocess
from dataclasses import dataclass, field


@dataclass
class ServiceStatus:
    """Status of a single Docker container/service."""
    name: str
    running: bool
    status: str = ""


@dataclass
class SystemHealth:
    """Aggregated system health snapshot."""
    services: list[ServiceStatus] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def system_check(self) -> str:
        """Return a one-line health summary string."""
        if self.errors:
            return f"degraded — {'; '.join(self.errors)}"
        running = [s for s in self.services if s.running]
        total = len(self.services)
        if total == 0:
            return "no services detected"
        if len(running) == total:
            return f"healthy — {total}/{total} services running"
        down = [s.name for s in self.services if not s.running]
        return f"degraded — {len(running)}/{total} running, down: {', '.join(down)}"


def _check_docker_services() -> list[ServiceStatus]:
    """Check Docker container status via docker ps."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return []
        services = []
        for line in result.stdout.strip().splitlines():
            if not line.strip():
                continue
            parts = line.split("\t", 1)
            name = parts[0]
            status_text = parts[1] if len(parts) > 1 else ""
            running = "Up" in status_text
            services.append(ServiceStatus(name=name, running=running, status=status_text))
        return services
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return []


def get_system_health() -> SystemHealth:
    """Build a SystemHealth snapshot. Primary entry point."""
    health = SystemHealth()
    try:
        health.services = _check_docker_services()
    except Exception as e:
        health.errors.append(f"docker check failed: {e}")
    return health
