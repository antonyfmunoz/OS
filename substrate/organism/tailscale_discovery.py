"""Tailscale auto-discovery tick — diffs tailscale peers vs device registry.

Registered as an autonomous tick stage in daemon.py. Each tick:
1. Runs `tailscale status --json` to enumerate peers
2. Diffs against device_registry.json
3. For unregistered peers: diagnoses + creates approval intercept
4. Tracks discovered peers in discovered_peers.json

UMH substrate module. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

from substrate.execution.cpu_gate import gated_subprocess_run
from substrate.state.runtime_paths import runtime_state_path

logger = logging.getLogger(__name__)

_ROOT = os.environ.get("UMH_ROOT") or "/opt/OS"


class TailscaleDiscoveryTick:
    """Discovers unregistered Tailscale peers and creates approval intercepts."""

    def __init__(
        self,
        *,
        registry_path: str | None = None,
        discovered_peers_path: str | None = None,
        interval_seconds: int | None = None,
    ) -> None:
        self._registry_path = registry_path or os.path.join(
            _ROOT, "infra", "device_registry.json",
        )
        self._discovered_peers_path = discovered_peers_path or str(
            runtime_state_path("discovery", "discovered_peers.json")
        )
        self._interval = interval_seconds or int(
            os.environ.get("UMH_DISCOVERY_INTERVAL_SECONDS", "300"),
        )
        self._last_tick = 0.0
        # Hostnames to exclude from discovery (infra nodes, etc.)
        self._exclude_patterns = [
            p.strip()
            for p in os.environ.get("UMH_DISCOVERY_EXCLUDE", "").split(",")
            if p.strip()
        ]

    def tick(self) -> None:
        """Run one discovery cycle if interval has elapsed."""
        now = time.time()
        if now - self._last_tick < self._interval:
            return
        self._last_tick = now

        try:
            self._run_discovery()
        except Exception as exc:
            logger.error("tailscale discovery tick failed: %s", exc)

    def _run_discovery(self) -> None:
        peers = self._get_tailscale_peers()
        if not peers:
            return

        registry = self._load_registry()
        registered_names = {
            d.get("tailscale_name", "").lower() for d in registry
        }
        registered_ips = {
            d.get("tailscale_ip", "") for d in registry if d.get("tailscale_ip")
        }

        tracked = self._load_tracked()

        new_peers: list[dict[str, Any]] = []
        for peer in peers:
            dns_name = peer.get("dns_name", "").lower()
            hostname = peer.get("hostname", "").lower()
            ips = peer.get("tailscale_ips", [])

            if dns_name in registered_names or hostname in registered_names:
                continue
            if any(ip in registered_ips for ip in ips):
                continue
            if self._is_excluded(hostname, dns_name):
                continue

            tracking_key = dns_name or hostname
            existing = tracked.get(tracking_key, {})
            status = existing.get("status", "")
            if status == "ignored":
                continue
            if status == "pending_approval":
                resolved = self._check_approval_resolved(existing.get("approval_id", ""))
                if resolved == "rejected":
                    tracked[tracking_key]["status"] = "ignored"
                    logger.info("peer %s rejected by operator → ignored", tracking_key)
                elif resolved == "approved":
                    tracked[tracking_key]["status"] = "approved"
                # still pending or unknown → skip
                continue
            if status == "expired":
                pass  # re-create approval

            new_peers.append(peer)

        for peer in new_peers:
            self._handle_new_peer(peer, tracked)

        self._save_tracked(tracked)

    def _get_tailscale_peers(self) -> list[dict[str, Any]]:
        result = gated_subprocess_run(
            ["tailscale", "status", "--json"],
            caller="tailscale_discovery.tick",
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result is None or result.returncode != 0:
            return []
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            return []

        peers: list[dict[str, Any]] = []
        for _key, peer in data.get("Peer", {}).items():
            peers.append({
                "hostname": peer.get("HostName", ""),
                "dns_name": peer.get("DNSName", "").split(".")[0],
                "os": peer.get("OS", "").lower(),
                "tailscale_ips": peer.get("TailscaleIPs", []),
                "online": peer.get("Online", False),
            })
        return peers

    def _handle_new_peer(
        self,
        peer: dict[str, Any],
        tracked: dict[str, Any],
    ) -> None:
        dns_name = peer.get("dns_name", "")
        hostname = peer.get("hostname", "")
        os_name = peer.get("os", "")
        ips = peer.get("tailscale_ips", [])
        ip = ips[0] if ips else ""
        tracking_key = dns_name or hostname

        # Diagnose
        diag_dict = self._diagnose(hostname, ip, os_name, dns_name)

        # Create approval intercept
        approval_id = self._create_approval(
            hostname=hostname,
            dns_name=dns_name,
            os_name=os_name,
            ip=ip,
            diagnosis=diag_dict,
        )

        tracked[tracking_key] = {
            "hostname": hostname,
            "dns_name": dns_name,
            "os": os_name,
            "tailscale_ip": ip,
            "status": "pending_approval" if approval_id else "failed",
            "approval_id": approval_id or "",
            "discovered_at": time.time(),
            "diagnosis": diag_dict,
        }

        logger.info(
            "new device discovered: %s (%s) → approval %s",
            hostname, os_name, approval_id or "FAILED",
        )

    def _diagnose(
        self,
        hostname: str,
        ip: str,
        os_name: str,
        dns_name: str,
    ) -> dict[str, Any]:
        """Run device diagnosis. Returns diagnosis dict."""
        if os_name in ("ios", "android"):
            return {
                "hostname": hostname,
                "dns_name": dns_name,
                "os": os_name,
                "ssh_reachable": False,
                "recommended_role": "controller",
                "recommended_type": os_name,
                "confidence": "high",
            }

        if not ip:
            return {
                "hostname": hostname,
                "dns_name": dns_name,
                "os": os_name,
                "ssh_reachable": False,
                "recommended_role": "controller",
                "recommended_type": "unknown",
                "confidence": "low",
            }

        try:
            from substrate.organism.device_provisioner import diagnose_device
            diag = diagnose_device(
                hostname=hostname,
                tailscale_ip=ip,
                os_hint=os_name,
                dns_name=dns_name,
            )
            return diag.to_dict()
        except Exception as exc:
            logger.debug("diagnosis failed for %s: %s", hostname, exc)
            return {
                "hostname": hostname,
                "dns_name": dns_name,
                "os": os_name,
                "ssh_reachable": False,
                "recommended_role": "controller",
                "recommended_type": "unknown",
                "confidence": "low",
                "error": str(exc),
            }

    def _create_approval(
        self,
        *,
        hostname: str,
        dns_name: str,
        os_name: str,
        ip: str,
        diagnosis: dict[str, Any],
    ) -> str | None:
        """Create an approval intercept for the new device."""
        try:
            from substrate.organism.executors.approval_intercept import (
                get_approval_intercept_service,
            )

            svc = get_approval_intercept_service()
            role = diagnosis.get("recommended_role", "controller")
            confidence = diagnosis.get("confidence", "low")
            specs = []
            if diagnosis.get("cpu_cores"):
                specs.append(f"{diagnosis['cpu_cores']} cores")
            if diagnosis.get("ram_mb"):
                specs.append(f"{diagnosis['ram_mb']}MB RAM")
            if diagnosis.get("gpu"):
                specs.append(diagnosis["gpu"])

            specs_str = ", ".join(specs) if specs else "unknown hardware"
            reason = (
                f"New device: {hostname} ({os_name}, {specs_str}). "
                f"Recommended: {role} ({confidence} confidence)"
            )

            intercept = svc.request_approval(
                execution_id=f"discovery-{dns_name or hostname}",
                executor_type="tailscale_discovery",
                operation="device_onboarding",
                risk_class="LOW",
                reason=reason,
                details=diagnosis,
            )
            return intercept.approval_id if intercept else None
        except Exception as exc:
            logger.error("failed to create approval for %s: %s", hostname, exc)
            return None

    def _check_approval_resolved(self, approval_id: str) -> str:
        """Check if an approval intercept has been resolved. Returns status."""
        if not approval_id:
            return "unknown"
        try:
            from substrate.organism.executors.approval_intercept import (
                get_approval_intercept_service,
            )
            svc = get_approval_intercept_service()
            intercept = svc.get(approval_id)
            if intercept is None:
                return "unknown"
            return intercept.status
        except Exception:
            return "unknown"

    def _is_excluded(self, hostname: str, dns_name: str) -> bool:
        for pattern in self._exclude_patterns:
            if pattern in hostname or pattern in dns_name:
                return True
        return False

    def _load_registry(self) -> list[dict[str, Any]]:
        try:
            with open(self._registry_path) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _load_tracked(self) -> dict[str, Any]:
        try:
            with open(self._discovered_peers_path) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_tracked(self, tracked: dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(self._discovered_peers_path), exist_ok=True)
        tmp = self._discovered_peers_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(tracked, f, indent=2)
        os.replace(tmp, self._discovered_peers_path)
