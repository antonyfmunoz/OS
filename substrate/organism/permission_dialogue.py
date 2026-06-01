"""Socratic Permission Engine — ask before expanding context access.

UMH never silently crawls, connects, or infers. Every scope expansion
is presented to the operator as a structured permission request with
clear explanation of what will be accessed, what inferences may be made,
and what will NOT happen. The operator can deny, limit, defer, or revoke.

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
_REQUESTS_PATH = os.path.join(
    _REPO_ROOT, "data", "umh", "context_assimilation", "permission_requests.jsonl"
)
_PREFERENCES_PATH = os.path.join(
    _REPO_ROOT, "data", "umh", "context_assimilation", "permission_preferences.jsonl"
)


class ApprovalOption(str, Enum):
    DENY = "deny"
    METADATA_ONLY = "metadata_only"
    ONE_TIME_READ = "one_time_read"
    LIMITED_FOLDER = "limited_folder"
    LIMITED_ACCOUNT = "limited_account"
    READ_ONLY = "read_only"
    SUGGEST_UPDATES_ONLY = "suggest_updates_only"
    OPERATOR_APPROVED_WRITE = "operator_approved_write"
    REMEMBER_PREFERENCE = "remember_preference"
    ASK_LATER = "ask_later"


class RequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    DEFERRED = "deferred"
    EXPIRED = "expired"
    REVOKED = "revoked"


class Sensitivity(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    SENSITIVE = "sensitive"
    FINANCIAL = "financial"
    PERSONAL = "personal"


@dataclass
class PermissionRequest:
    request_id: str = ""
    requested_action: str = ""
    reason: str = ""
    source_type: str = ""
    source_id: str = ""
    scope: str = ""
    data_requested: str = ""
    risk_class: str = "low"
    sensitivity: str = Sensitivity.INTERNAL.value
    what_umh_will_do: str = ""
    what_umh_will_not_do: str = ""
    possible_inferences: list[str] = field(default_factory=list)
    retention_policy: str = "session_only"
    approval_options: list[str] = field(default_factory=list)
    recommended_option: str = ApprovalOption.METADATA_ONLY.value
    status: str = RequestStatus.PENDING.value
    operator_choice: str = ""
    created_at: float = 0.0
    decided_at: float = 0.0

    def __post_init__(self) -> None:
        if not self.request_id:
            self.request_id = f"perm-{uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = time.time()
        if not self.approval_options:
            self.approval_options = [
                ApprovalOption.DENY.value,
                ApprovalOption.METADATA_ONLY.value,
                ApprovalOption.READ_ONLY.value,
                ApprovalOption.ASK_LATER.value,
            ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "requested_action": self.requested_action,
            "reason": self.reason,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "scope": self.scope,
            "data_requested": self.data_requested,
            "risk_class": self.risk_class,
            "sensitivity": self.sensitivity,
            "what_umh_will_do": self.what_umh_will_do,
            "what_umh_will_not_do": self.what_umh_will_not_do,
            "possible_inferences": self.possible_inferences,
            "retention_policy": self.retention_policy,
            "approval_options": self.approval_options,
            "recommended_option": self.recommended_option,
            "status": self.status,
            "operator_choice": self.operator_choice,
            "created_at": self.created_at,
            "decided_at": self.decided_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PermissionRequest:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def to_dialogue(self) -> dict[str, Any]:
        """Render as a human-readable Socratic dialogue structure."""
        return {
            "question": self.reason,
            "context": {
                "what_will_happen": self.what_umh_will_do,
                "what_will_not_happen": self.what_umh_will_not_do,
                "possible_inferences": self.possible_inferences,
                "data_scope": self.data_requested,
                "sensitivity": self.sensitivity,
                "retention": self.retention_policy,
            },
            "options": self.approval_options,
            "recommended": self.recommended_option,
        }


@dataclass
class PermissionPreference:
    preference_id: str = ""
    source_type: str = ""
    action_pattern: str = ""
    default_choice: str = ApprovalOption.METADATA_ONLY.value
    remember: bool = True
    created_at: float = 0.0

    def __post_init__(self) -> None:
        if not self.preference_id:
            self.preference_id = f"pref-{uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "preference_id": self.preference_id,
            "source_type": self.source_type,
            "action_pattern": self.action_pattern,
            "default_choice": self.default_choice,
            "remember": self.remember,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PermissionPreference:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class SocraticPermissionEngine:
    def __init__(
        self,
        requests_path: str | None = None,
        preferences_path: str | None = None,
    ) -> None:
        self._requests_path = requests_path or _REQUESTS_PATH
        self._preferences_path = preferences_path or _PREFERENCES_PATH
        self._requests: dict[str, PermissionRequest] = {}
        self._preferences: dict[str, PermissionPreference] = {}
        self._load()

    def _load(self) -> None:
        self._load_store(self._requests_path, self._requests, PermissionRequest, "request_id")
        self._load_store(self._preferences_path, self._preferences, PermissionPreference, "preference_id")

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
                    logger.warning("Skipping malformed line in %s", path)

    def _save_requests(self) -> None:
        os.makedirs(os.path.dirname(self._requests_path), exist_ok=True)
        with open(self._requests_path, "w") as f:
            for req in self._requests.values():
                f.write(json.dumps(req.to_dict(), default=str) + "\n")

    def _save_preferences(self) -> None:
        os.makedirs(os.path.dirname(self._preferences_path), exist_ok=True)
        with open(self._preferences_path, "w") as f:
            for pref in self._preferences.values():
                f.write(json.dumps(pref.to_dict(), default=str) + "\n")

    def create_request(
        self,
        requested_action: str,
        reason: str,
        source_type: str = "",
        source_id: str = "",
        scope: str = "",
        data_requested: str = "",
        sensitivity: str = Sensitivity.INTERNAL.value,
        what_umh_will_do: str = "",
        what_umh_will_not_do: str = "",
        possible_inferences: list[str] | None = None,
    ) -> PermissionRequest:
        saved_pref = self._check_saved_preference(source_type, requested_action)
        if saved_pref:
            req = PermissionRequest(
                requested_action=requested_action,
                reason=reason,
                source_type=source_type,
                source_id=source_id,
                scope=scope,
                data_requested=data_requested,
                sensitivity=sensitivity,
                what_umh_will_do=what_umh_will_do,
                what_umh_will_not_do=what_umh_will_not_do,
                possible_inferences=possible_inferences or [],
                status=RequestStatus.APPROVED.value,
                operator_choice=saved_pref.default_choice,
                decided_at=time.time(),
            )
            self._requests[req.request_id] = req
            self._save_requests()
            return req

        risk = self._assess_risk(sensitivity, requested_action)
        options = self._build_options(sensitivity, requested_action)
        recommended = self._recommend_option(sensitivity, requested_action)

        req = PermissionRequest(
            requested_action=requested_action,
            reason=reason,
            source_type=source_type,
            source_id=source_id,
            scope=scope,
            data_requested=data_requested,
            risk_class=risk,
            sensitivity=sensitivity,
            what_umh_will_do=what_umh_will_do,
            what_umh_will_not_do=what_umh_will_not_do or "Will not store raw content. Will not share with external services. Will not auto-canonize.",
            possible_inferences=possible_inferences or [],
            approval_options=options,
            recommended_option=recommended,
        )
        self._requests[req.request_id] = req
        self._save_requests()
        return req

    def decide(self, request_id: str, choice: str, remember: bool = False) -> bool:
        req = self._requests.get(request_id)
        if not req:
            return False
        if choice not in req.approval_options:
            return False

        if choice == ApprovalOption.DENY.value:
            req.status = RequestStatus.DENIED.value
        elif choice == ApprovalOption.ASK_LATER.value:
            req.status = RequestStatus.DEFERRED.value
        else:
            req.status = RequestStatus.APPROVED.value

        req.operator_choice = choice
        req.decided_at = time.time()
        self._save_requests()

        if remember and choice != ApprovalOption.ASK_LATER.value:
            pref = PermissionPreference(
                source_type=req.source_type,
                action_pattern=req.requested_action,
                default_choice=choice,
            )
            self._preferences[pref.preference_id] = pref
            self._save_preferences()

        return True

    def revoke(self, request_id: str) -> bool:
        req = self._requests.get(request_id)
        if not req:
            return False
        req.status = RequestStatus.REVOKED.value
        req.decided_at = time.time()
        self._save_requests()
        return True

    def is_permitted(self, request_id: str) -> bool:
        req = self._requests.get(request_id)
        if not req:
            return False
        return req.status == RequestStatus.APPROVED.value

    def get_request(self, request_id: str) -> PermissionRequest | None:
        return self._requests.get(request_id)

    def list_pending(self) -> list[PermissionRequest]:
        return [
            r for r in self._requests.values()
            if r.status == RequestStatus.PENDING.value
        ]

    def list_requests(self, status: str | None = None) -> list[PermissionRequest]:
        result = list(self._requests.values())
        if status:
            result = [r for r in result if r.status == status]
        return result

    def get_effective_scope(self, request_id: str) -> str:
        req = self._requests.get(request_id)
        if not req or req.status != RequestStatus.APPROVED.value:
            return "none"
        choice = req.operator_choice
        if choice == ApprovalOption.METADATA_ONLY.value:
            return "metadata_only"
        if choice == ApprovalOption.ONE_TIME_READ.value:
            return "one_time_read"
        if choice == ApprovalOption.LIMITED_FOLDER.value:
            return "limited_folder"
        if choice == ApprovalOption.READ_ONLY.value:
            return "read_only"
        return "none"

    def _check_saved_preference(self, source_type: str, action: str) -> PermissionPreference | None:
        for pref in self._preferences.values():
            if pref.source_type == source_type and pref.action_pattern == action and pref.remember:
                return pref
        return None

    def _assess_risk(self, sensitivity: str, action: str) -> str:
        if sensitivity in (Sensitivity.FINANCIAL.value, Sensitivity.PERSONAL.value):
            return "medium"
        if sensitivity == Sensitivity.SENSITIVE.value:
            return "medium"
        if "write" in action.lower() or "delete" in action.lower():
            return "medium"
        return "low"

    def _build_options(self, sensitivity: str, action: str) -> list[str]:
        options = [ApprovalOption.DENY.value, ApprovalOption.METADATA_ONLY.value]
        if sensitivity not in (Sensitivity.FINANCIAL.value, Sensitivity.PERSONAL.value):
            options.append(ApprovalOption.READ_ONLY.value)
        options.extend([
            ApprovalOption.LIMITED_FOLDER.value,
            ApprovalOption.ASK_LATER.value,
            ApprovalOption.REMEMBER_PREFERENCE.value,
        ])
        return options

    def _recommend_option(self, sensitivity: str, action: str) -> str:
        if sensitivity in (Sensitivity.FINANCIAL.value, Sensitivity.PERSONAL.value):
            return ApprovalOption.METADATA_ONLY.value
        if sensitivity == Sensitivity.SENSITIVE.value:
            return ApprovalOption.METADATA_ONLY.value
        return ApprovalOption.READ_ONLY.value

    def count(self) -> int:
        return len(self._requests)

    def pending_count(self) -> int:
        return sum(1 for r in self._requests.values() if r.status == RequestStatus.PENDING.value)

    def summary(self) -> dict[str, Any]:
        by_status: dict[str, int] = {}
        for r in self._requests.values():
            by_status[r.status] = by_status.get(r.status, 0) + 1
        return {
            "total": len(self._requests),
            "by_status": by_status,
            "saved_preferences": len(self._preferences),
        }
