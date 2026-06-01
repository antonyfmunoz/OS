"""Environment Discovery — device, filesystem, application, account inventory.

Models the operator's computing environment: devices, filesystem scopes,
installed applications, connected accounts, and subscriptions. Discovery
defaults to metadata-only — filesystem scanning and content access require
explicit operator permission via the Socratic Permission Engine.

Phase 13.3. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
_DEVICES_PATH = os.path.join(
    _REPO_ROOT, "data", "umh", "context_assimilation", "devices.jsonl"
)
_APPS_PATH = os.path.join(
    _REPO_ROOT, "data", "umh", "context_assimilation", "applications.jsonl"
)
_SCOPES_PATH = os.path.join(
    _REPO_ROOT, "data", "umh", "context_assimilation", "filesystem_scopes.jsonl"
)


class DeviceType(str, Enum):
    VPS = "vps"
    DESKTOP = "desktop"
    LAPTOP = "laptop"
    PHONE = "phone"
    TABLET = "tablet"
    SERVER = "server"
    VIRTUAL_MACHINE = "virtual_machine"
    CONTAINER = "container"
    UNKNOWN = "unknown"


class DiscoveryStatus(str, Enum):
    UNKNOWN = "unknown"
    METADATA_ONLY = "metadata_only"
    PARTIAL_SCAN = "partial_scan"
    FULL_SCAN = "full_scan"
    PERMISSION_DENIED = "permission_denied"
    STALE = "stale"


class PermissionState(str, Enum):
    UNKNOWN = "unknown"
    REQUESTED = "requested"
    GRANTED_READ_ONLY = "granted_read_only"
    GRANTED_METADATA_ONLY = "granted_metadata_only"
    GRANTED_LIMITED_SCOPE = "granted_limited_scope"
    DENIED = "denied"
    EXPIRED = "expired"
    REVOKED = "revoked"


class AppType(str, Enum):
    LOCAL_APP = "local_app"
    WEB_APP = "web_app"
    BROWSER_EXTENSION = "browser_extension"
    SAAS = "saas"
    DEVELOPER_TOOL = "developer_tool"
    COMMUNICATION_TOOL = "communication_tool"
    DESIGN_TOOL = "design_tool"
    FINANCE_TOOL = "finance_tool"
    AUTOMATION_TOOL = "automation_tool"
    STORAGE_TOOL = "storage_tool"
    AI_TOOL = "ai_tool"
    UNKNOWN = "unknown"


class UsageStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPECTED_ACTIVE = "suspected_active"
    SUSPECTED_UNUSED = "suspected_unused"
    UNKNOWN = "unknown"


class ScopeStatus(str, Enum):
    PENDING_PERMISSION = "pending_permission"
    APPROVED = "approved"
    INDEXED = "indexed"
    DENIED = "denied"
    BLOCKED = "blocked"
    EXPIRED = "expired"


@dataclass
class FilesystemScope:
    scope_id: str = ""
    device_id: str = ""
    path: str = ""
    label: str = ""
    allowed: bool = False
    recursive: bool = False
    max_depth: int = 1
    allowed_extensions: list[str] = field(default_factory=list)
    blocked_patterns: list[str] = field(default_factory=list)
    contains_sensitive_data: bool = False
    permission_required: bool = True
    last_indexed_at: float = 0.0
    status: str = ScopeStatus.PENDING_PERMISSION.value

    def __post_init__(self) -> None:
        if not self.scope_id:
            self.scope_id = f"scope-{uuid4().hex[:8]}"
        if not self.blocked_patterns:
            self.blocked_patterns = [".env", "credentials", "secret", "private_key", "token"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "scope_id": self.scope_id,
            "device_id": self.device_id,
            "path": self.path,
            "label": self.label,
            "allowed": self.allowed,
            "recursive": self.recursive,
            "max_depth": self.max_depth,
            "allowed_extensions": self.allowed_extensions,
            "blocked_patterns": self.blocked_patterns,
            "contains_sensitive_data": self.contains_sensitive_data,
            "permission_required": self.permission_required,
            "last_indexed_at": self.last_indexed_at,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> FilesystemScope:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ApplicationInventoryItem:
    app_id: str = ""
    app_name: str = ""
    app_type: str = AppType.UNKNOWN.value
    install_path: str = ""
    detected_from: str = ""
    account_refs: list[str] = field(default_factory=list)
    subscription_refs: list[str] = field(default_factory=list)
    related_projects: list[str] = field(default_factory=list)
    related_companies: list[str] = field(default_factory=list)
    usage_status: str = UsageStatus.UNKNOWN.value
    canonicality: str = "unknown"
    confidence: float = 0.5
    evidence: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.app_id:
            self.app_id = f"app-{uuid4().hex[:8]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "app_id": self.app_id,
            "app_name": self.app_name,
            "app_type": self.app_type,
            "install_path": self.install_path,
            "detected_from": self.detected_from,
            "account_refs": self.account_refs,
            "subscription_refs": self.subscription_refs,
            "related_projects": self.related_projects,
            "related_companies": self.related_companies,
            "usage_status": self.usage_status,
            "canonicality": self.canonicality,
            "confidence": self.confidence,
            "evidence": self.evidence,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ApplicationInventoryItem:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class DeviceEnvironment:
    device_id: str = ""
    device_name: str = ""
    device_type: str = DeviceType.UNKNOWN.value
    operating_system: str = ""
    user_label: str = ""
    trust_level: float = 0.5
    discovery_status: str = DiscoveryStatus.UNKNOWN.value
    filesystem_roots: list[str] = field(default_factory=list)
    application_inventory: list[str] = field(default_factory=list)
    connected_accounts: list[str] = field(default_factory=list)
    permission_state: str = PermissionState.UNKNOWN.value
    last_scanned_at: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.device_id:
            self.device_id = f"dev-{uuid4().hex[:8]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "device_name": self.device_name,
            "device_type": self.device_type,
            "operating_system": self.operating_system,
            "user_label": self.user_label,
            "trust_level": self.trust_level,
            "discovery_status": self.discovery_status,
            "filesystem_roots": self.filesystem_roots,
            "application_inventory": self.application_inventory,
            "connected_accounts": self.connected_accounts,
            "permission_state": self.permission_state,
            "last_scanned_at": self.last_scanned_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DeviceEnvironment:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class EnvironmentDiscoveryStore:
    def __init__(
        self,
        devices_path: str | None = None,
        apps_path: str | None = None,
        scopes_path: str | None = None,
    ) -> None:
        self._devices_path = devices_path or _DEVICES_PATH
        self._apps_path = apps_path or _APPS_PATH
        self._scopes_path = scopes_path or _SCOPES_PATH
        self._devices: dict[str, DeviceEnvironment] = {}
        self._apps: dict[str, ApplicationInventoryItem] = {}
        self._scopes: dict[str, FilesystemScope] = {}
        self._load()

    def _load(self) -> None:
        self._load_store(self._devices_path, self._devices, DeviceEnvironment, "device_id")
        self._load_store(self._apps_path, self._apps, ApplicationInventoryItem, "app_id")
        self._load_store(self._scopes_path, self._scopes, FilesystemScope, "scope_id")

    def _load_store(self, path: str, store: dict, cls: type, id_field: str) -> None:
        if not os.path.exists(path):
            return
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    obj = cls.from_dict(d)
                    store[getattr(obj, id_field)] = obj
                except (json.JSONDecodeError, TypeError):
                    logger.warning("Skipping malformed %s line", cls.__name__)

    def _save_store(self, path: str, store: dict) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            for obj in store.values():
                f.write(json.dumps(obj.to_dict(), default=str) + "\n")

    def register_device(self, device: DeviceEnvironment) -> DeviceEnvironment:
        self._devices[device.device_id] = device
        self._save_store(self._devices_path, self._devices)
        return device

    def get_device(self, device_id: str) -> DeviceEnvironment | None:
        return self._devices.get(device_id)

    def list_devices(self) -> list[DeviceEnvironment]:
        return list(self._devices.values())

    def register_app(self, app: ApplicationInventoryItem) -> ApplicationInventoryItem:
        for existing in self._apps.values():
            if existing.app_name.lower() == app.app_name.lower():
                existing.evidence.extend(e for e in app.evidence if e not in existing.evidence)
                existing.confidence = max(existing.confidence, app.confidence)
                self._save_store(self._apps_path, self._apps)
                return existing
        self._apps[app.app_id] = app
        self._save_store(self._apps_path, self._apps)
        return app

    def get_app(self, app_id: str) -> ApplicationInventoryItem | None:
        return self._apps.get(app_id)

    def list_apps(
        self, app_type: str | None = None, usage_status: str | None = None
    ) -> list[ApplicationInventoryItem]:
        result = list(self._apps.values())
        if app_type:
            result = [a for a in result if a.app_type == app_type]
        if usage_status:
            result = [a for a in result if a.usage_status == usage_status]
        return result

    def register_scope(self, scope: FilesystemScope) -> FilesystemScope:
        self._scopes[scope.scope_id] = scope
        self._save_store(self._scopes_path, self._scopes)
        return scope

    def get_scope(self, scope_id: str) -> FilesystemScope | None:
        return self._scopes.get(scope_id)

    def list_scopes(self, device_id: str | None = None) -> list[FilesystemScope]:
        result = list(self._scopes.values())
        if device_id:
            result = [s for s in result if s.device_id == device_id]
        return result

    def grant_scope(self, scope_id: str) -> bool:
        scope = self._scopes.get(scope_id)
        if not scope:
            return False
        scope.allowed = True
        scope.status = ScopeStatus.APPROVED.value
        self._save_store(self._scopes_path, self._scopes)
        return True

    def deny_scope(self, scope_id: str) -> bool:
        scope = self._scopes.get(scope_id)
        if not scope:
            return False
        scope.allowed = False
        scope.status = ScopeStatus.DENIED.value
        self._save_store(self._scopes_path, self._scopes)
        return True

    def summary(self) -> dict[str, Any]:
        return {
            "devices": len(self._devices),
            "applications": len(self._apps),
            "filesystem_scopes": len(self._scopes),
            "approved_scopes": sum(1 for s in self._scopes.values() if s.allowed),
            "denied_scopes": sum(
                1 for s in self._scopes.values()
                if s.status == ScopeStatus.DENIED.value
            ),
        }
