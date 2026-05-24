"""Permission model — granular consent for UMH instance instantiation.

Foundation for Phase 5 (Discovery Permission Gate) of the 13-phase
onboarding flow. Each permission grant records:
  - What was approved (scope)
  - When it expires (expiry)
  - Who/what requested it (requester)
  - How to revoke it (always instant, human supremacy principle)

Permissions are per-integration, per-device, per-sensor. The operator
can revoke any permission instantly at any time.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

UMH_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
PERMISSIONS_FILE = os.path.join(UMH_ROOT, "data", "permissions", "grants.json")


class PermissionScope(str, Enum):
    """What the permission covers."""

    CALENDAR_READ = "calendar_read"
    CALENDAR_WRITE = "calendar_write"
    EMAIL_READ = "email_read"
    EMAIL_SEND = "email_send"
    GITHUB_READ = "github_read"
    GITHUB_WRITE = "github_write"
    DRIVE_READ = "drive_read"
    DRIVE_WRITE = "drive_write"
    SLACK_READ = "slack_read"
    SLACK_WRITE = "slack_write"
    DISCORD_READ = "discord_read"
    DISCORD_WRITE = "discord_write"
    WEBCAM = "webcam"
    MICROPHONE = "microphone"
    SCREEN_CAPTURE = "screen_capture"
    CLIPBOARD = "clipboard"
    DESKTOP_AUTOMATION = "desktop_automation"
    BROWSER_CONTROL = "browser_control"
    SYSTEM_METRICS = "system_metrics"
    FILE_SYSTEM = "file_system"
    SHELL_EXECUTION = "shell_execution"
    NETWORK_REQUESTS = "network_requests"


class PermissionStatus(str, Enum):
    GRANTED = "granted"
    DENIED = "denied"
    REVOKED = "revoked"
    EXPIRED = "expired"


@dataclass
class PermissionGrant:
    """A single permission grant from the operator."""

    scope: PermissionScope
    status: PermissionStatus = PermissionStatus.GRANTED
    granted_at: str = ""
    expires_at: str | None = None
    revoked_at: str | None = None
    requester: str = "system"
    reason: str = ""
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.granted_at:
            self.granted_at = datetime.now(timezone.utc).isoformat()

    @property
    def is_active(self) -> bool:
        if self.status != PermissionStatus.GRANTED:
            return False
        if self.expires_at:
            try:
                expiry = datetime.fromisoformat(self.expires_at)
                if datetime.now(timezone.utc) > expiry:
                    return False
            except ValueError:
                pass
        return True

    def revoke(self) -> None:
        self.status = PermissionStatus.REVOKED
        self.revoked_at = datetime.now(timezone.utc).isoformat()

    def as_dict(self) -> dict:
        d = asdict(self)
        d["scope"] = self.scope.value
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> PermissionGrant:
        try:
            scope = PermissionScope(d["scope"])
        except (KeyError, ValueError):
            scope = PermissionScope.SYSTEM_METRICS
        try:
            status = PermissionStatus(d.get("status", "granted"))
        except ValueError:
            status = PermissionStatus.GRANTED
        return cls(
            scope=scope,
            status=status,
            granted_at=d.get("granted_at", ""),
            expires_at=d.get("expires_at"),
            revoked_at=d.get("revoked_at"),
            requester=d.get("requester", "system"),
            reason=d.get("reason", ""),
            metadata=d.get("metadata", {}),
        )


class PermissionStore:
    """Persistent permission grant storage."""

    def __init__(self, path: str = PERMISSIONS_FILE) -> None:
        self._path = path
        self._grants: dict[str, PermissionGrant] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path) as f:
                data = json.load(f)
            for scope_val, grant_data in data.get("grants", {}).items():
                self._grants[scope_val] = PermissionGrant.from_dict(grant_data)
        except Exception as exc:
            logger.debug("Failed to load permissions: %s", exc)

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        try:
            data = {
                "grants": {k: v.as_dict() for k, v in self._grants.items()},
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            with open(self._path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as exc:
            logger.debug("Failed to save permissions: %s", exc)

    def grant(
        self,
        scope: PermissionScope,
        requester: str = "system",
        reason: str = "",
        expires_at: str | None = None,
    ) -> PermissionGrant:
        """Grant a permission. Overwrites any existing grant for this scope."""
        perm = PermissionGrant(
            scope=scope,
            status=PermissionStatus.GRANTED,
            requester=requester,
            reason=reason,
            expires_at=expires_at,
        )
        self._grants[scope.value] = perm
        self._save()
        return perm

    def deny(self, scope: PermissionScope, reason: str = "") -> PermissionGrant:
        """Explicitly deny a permission."""
        perm = PermissionGrant(
            scope=scope,
            status=PermissionStatus.DENIED,
            reason=reason,
        )
        self._grants[scope.value] = perm
        self._save()
        return perm

    def revoke(self, scope: PermissionScope) -> bool:
        """Revoke a granted permission. Returns True if it was active."""
        perm = self._grants.get(scope.value)
        if perm is None:
            return False
        was_active = perm.is_active
        perm.revoke()
        self._save()
        return was_active

    def is_allowed(self, scope: PermissionScope) -> bool:
        """Check if a permission is currently active."""
        perm = self._grants.get(scope.value)
        if perm is None:
            return False
        return perm.is_active

    def get(self, scope: PermissionScope) -> PermissionGrant | None:
        return self._grants.get(scope.value)

    def list_active(self) -> list[PermissionGrant]:
        return [p for p in self._grants.values() if p.is_active]

    def list_all(self) -> list[PermissionGrant]:
        return list(self._grants.values())

    def revoke_all(self) -> int:
        """Revoke all active permissions. Returns count revoked."""
        count = 0
        for perm in self._grants.values():
            if perm.is_active:
                perm.revoke()
                count += 1
        if count:
            self._save()
        return count

    def display(self) -> None:
        """Print current permission status."""
        active = self.list_active()
        print()
        print("Permission Grants")
        print("-" * 40)
        if not active:
            print("  No active permissions.")
        else:
            for p in active:
                exp = f" (expires {p.expires_at})" if p.expires_at else ""
                print(f"  [+] {p.scope.value}{exp}")
        denied = [p for p in self._grants.values() if p.status == PermissionStatus.DENIED]
        if denied:
            print()
            for p in denied:
                print(f"  [-] {p.scope.value} (denied)")
        print()
