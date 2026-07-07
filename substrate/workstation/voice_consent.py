"""Voice consent grants — P4S-31D-1 (VoiceIntentContract consent gate).

Stored, revocable records that an operator authorized voice capture on a
specific device in a specific activation mode. Contract source:
``docs/VOICE_INTENT_CONTRACT.md`` §Permission/consent model and the
``VoiceConsentGrant`` shape in ``data/umh/voice/voice_intent_contract_types.json``.

Hard semantics (all fail-closed):

- ``active = granted AND NOT revoked``.
- Consent is PER-MODE: a ``push_to_talk`` grant never authorizes ``wake_word``
  or ``always_on``. Lookup is exact-mode, exact-device, exact-principal.
- Absent an active grant, ``require_active_grant`` raises the typed
  ``VoiceConsentRefused`` — capture must not open.
- This module owns substrate JSON state only (``data/umh/voice/``). Writes are
  wrapped in the registered ``voice_consent_grant`` / ``voice_consent_revoke``
  MutationSpecs by the transport layer — never called ungoverned from routes.

The UMH grant is the SECOND consent layer; the browser/OS mic permission is the
first. Both are required; either missing means refusal.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from substrate.workstation.voice_ingress_runtime import ActivationMode

logger = logging.getLogger(__name__)

_DEFAULT_STORE_PATH = os.path.join(
    os.environ.get("UMH_ROOT", "/opt/OS"), "data", "umh", "voice", "consent_grants.json"
)

# P4S-31D-1 scope: only push-to-talk consent is grantable. Wake-word and
# always-on grants become grantable in their own packets (P4S-31D-3/6) —
# refusing them here is the mechanical guard against ambient scope creep.
GRANTABLE_MODES: frozenset[str] = frozenset({ActivationMode.PUSH_TO_TALK.value})

GRANT_MUTATION_NAME = "voice_consent_grant"
REVOKE_MUTATION_NAME = "voice_consent_revoke"


class VoiceConsentRefused(Exception):
    """Typed fail-closed refusal: no active grant for (principal, device, mode)."""

    def __init__(self, reason: str, code: str = "CONSENT_REQUIRED") -> None:
        super().__init__(reason)
        self.code = code
        self.reason = reason


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class VoiceConsentGrant:
    """One operator's authorization for one capture mode on one device."""

    operator_principal: str
    device_registry_id: str
    activation_mode: str
    grant_id: str = field(default_factory=lambda: f"vcg-{uuid.uuid4().hex[:12]}")
    granted_at: str = field(default_factory=_utc_now)
    revoked_at: str | None = None

    @property
    def active(self) -> bool:
        return self.revoked_at is None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["active"] = self.active
        return d


class VoiceConsentStore:
    """Substrate-owned JSON store for consent grants (thread-safe, atomic write)."""

    def __init__(self, store_path: str | None = None) -> None:
        self._path = store_path or _DEFAULT_STORE_PATH
        self._lock = threading.Lock()

    def _load(self) -> list[dict]:
        try:
            with open(self._path, encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, list) else []
        except FileNotFoundError:
            return []
        except Exception as exc:
            logger.debug("consent store read failed (%s): %s", self._path, exc)
            return []

    def _save(self, grants: list[dict]) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        tmp = f"{self._path}.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(grants, fh, indent=1)
        os.replace(tmp, self._path)

    @staticmethod
    def _matches(raw: dict, principal: str, device: str, mode: str) -> bool:
        return (
            raw.get("operator_principal") == principal
            and raw.get("device_registry_id") == device
            and raw.get("activation_mode") == mode
        )

    def active_grant(
        self, operator_principal: str, device_registry_id: str, activation_mode: str
    ) -> VoiceConsentGrant | None:
        """Exact-mode, exact-device, exact-principal lookup. None = no consent."""
        with self._lock:
            for raw in self._load():
                if (
                    self._matches(raw, operator_principal, device_registry_id, activation_mode)
                    and raw.get("revoked_at") is None
                ):
                    raw = {k: v for k, v in raw.items() if k != "active"}
                    return VoiceConsentGrant(**raw)
        return None

    def grant(
        self, operator_principal: str, device_registry_id: str, activation_mode: str
    ) -> VoiceConsentGrant:
        """Create (or return the existing) active grant. Refuses non-grantable modes."""
        if activation_mode not in GRANTABLE_MODES:
            raise VoiceConsentRefused(
                f"activation mode '{activation_mode}' is not grantable in this packet "
                f"(grantable: {sorted(GRANTABLE_MODES)})",
                code="MODE_NOT_GRANTABLE",
            )
        existing = self.active_grant(operator_principal, device_registry_id, activation_mode)
        if existing is not None:
            return existing
        record = VoiceConsentGrant(
            operator_principal=operator_principal,
            device_registry_id=device_registry_id,
            activation_mode=activation_mode,
        )
        with self._lock:
            grants = self._load()
            grants.append(record.to_dict())
            self._save(grants)
        logger.info(
            "voice consent granted: %s mode=%s device=%s",
            record.grant_id,
            activation_mode,
            device_registry_id,
        )
        return record

    def revoke(
        self, operator_principal: str, device_registry_id: str, activation_mode: str
    ) -> bool:
        """Revoke every active matching grant. Returns True if anything was revoked."""
        revoked = False
        with self._lock:
            grants = self._load()
            for raw in grants:
                if (
                    self._matches(raw, operator_principal, device_registry_id, activation_mode)
                    and raw.get("revoked_at") is None
                ):
                    raw["revoked_at"] = _utc_now()
                    raw["active"] = False
                    revoked = True
            if revoked:
                self._save(grants)
        if revoked:
            logger.info(
                "voice consent revoked: mode=%s device=%s", activation_mode, device_registry_id
            )
        return revoked

    def require_active_grant(
        self, operator_principal: str, device_registry_id: str, activation_mode: str
    ) -> VoiceConsentGrant:
        """Fail-closed consent gate: return the active grant or raise typed refusal."""
        grant = self.active_grant(operator_principal, device_registry_id, activation_mode)
        if grant is None:
            raise VoiceConsentRefused(
                f"no active VoiceConsentGrant for mode='{activation_mode}' on "
                f"device='{device_registry_id}' — capture refused"
            )
        return grant
