"""Cockpit voice consent routes — P4S-31D-1 (VoiceConsentGrant surface).

Covers:
- GET  /voice/consent          (read: is there an active grant for device+mode)
- POST /voice/consent/grant    (governed write: record explicit operator consent)
- POST /voice/consent/revoke   (governed write: revoke; capture refused after)

Doctrine (docs/VOICE_INTENT_CONTRACT.md):
- Consent is PER-MODE, PER-DEVICE, PER-PRINCIPAL, stored and revocable.
- The operator principal comes from the authenticated dependency
  (``_require_operator_role`` return value) — NEVER from the request body.
  Voice mints no identity.
- Writes route through the registered ``voice_consent_grant`` /
  ``voice_consent_revoke`` MutationSpecs (no ungoverned append).
- P4S-31D-1 grants only ``push_to_talk``; other modes are refused typed
  (``MODE_NOT_GRANTABLE``) until their packets (P4S-31D-3/6).
- Read surface never 500s; refusals return stable dicts, not exceptions.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_SURFACE = "voice_consent"


def _grant_payload(grant) -> dict | None:
    return grant.to_dict() if grant is not None else None


def governed_consent_grant(
    operator_principal: str,
    device_registry_id: str,
    activation_mode: str,
    mutation_runner=None,
) -> dict:
    """The ONE governed consent-grant write. Returns a stable dict; never raises."""
    try:
        from substrate.workstation.voice_consent import (
            GRANT_MUTATION_NAME,
            VoiceConsentRefused,
            VoiceConsentStore,
        )

        if mutation_runner is None:
            from transports.api.governed import governed_mutation

            mutation_runner = governed_mutation

        store = VoiceConsentStore()
        result: dict = {}

        def _execute() -> tuple[str, bool]:
            grant = store.grant(operator_principal, device_registry_id, activation_mode)
            result["grant"] = grant.to_dict()
            return (f"voice consent granted: {grant.grant_id}", True)

        try:
            response = mutation_runner(
                mutation_name=GRANT_MUTATION_NAME,
                intent=(
                    f"grant voice capture consent mode={activation_mode} "
                    f"device={device_registry_id}"
                ),
                execute_fn=_execute,
                source="cockpit",
            )
        except VoiceConsentRefused as refusal:
            return {
                "surface": _SURFACE,
                "granted": False,
                "active": False,
                "error": refusal.reason,
                "code": refusal.code,
            }

        # MutationResponse contract field is `success` (substrate/organism/
        # mutation_router.py) — same check IntentLoop uses. #230 shipped
        # checking a nonexistent `executed` attr, so successful governed
        # grants reported as refusals.
        succeeded = bool(getattr(response, "success", False))
        if not succeeded or "grant" not in result:
            return {
                "surface": _SURFACE,
                "granted": False,
                "active": False,
                "error": getattr(response, "rejected_reason", "")
                or getattr(response, "output", "")
                or "governed grant did not execute",
                "code": "GOVERNED_REFUSAL",
            }
        return {
            "surface": _SURFACE,
            "granted": True,
            "active": True,
            "grant": result["grant"],
            "error": None,
        }
    except Exception as e:
        # VoiceConsentRefused raised inside execute_fn surfaces via the runner;
        # anything else degrades to a stable refusal (fail-closed).
        logger.debug("governed consent grant failed: %s", e)
        return {
            "surface": _SURFACE,
            "granted": False,
            "active": False,
            "error": str(e),
            "code": "GRANT_FAILED",
        }


def governed_consent_revoke(
    operator_principal: str,
    device_registry_id: str,
    activation_mode: str,
    mutation_runner=None,
) -> dict:
    """The ONE governed consent-revoke write. Returns a stable dict; never raises."""
    try:
        from substrate.workstation.voice_consent import (
            REVOKE_MUTATION_NAME,
            VoiceConsentStore,
        )

        if mutation_runner is None:
            from transports.api.governed import governed_mutation

            mutation_runner = governed_mutation

        store = VoiceConsentStore()
        result: dict = {"revoked": False}

        def _execute() -> tuple[str, bool]:
            result["revoked"] = store.revoke(
                operator_principal, device_registry_id, activation_mode
            )
            return (
                f"voice consent revoke mode={activation_mode}: revoked={result['revoked']}",
                True,
            )

        response = mutation_runner(
            mutation_name=REVOKE_MUTATION_NAME,
            intent=(
                f"revoke voice capture consent mode={activation_mode} device={device_registry_id}"
            ),
            execute_fn=_execute,
            source="cockpit",
        )
        succeeded = bool(getattr(response, "success", False))
        return {
            "surface": _SURFACE,
            "revoked": bool(result["revoked"]) and succeeded,
            "active": False,
            "error": None
            if succeeded
            else (
                getattr(response, "rejected_reason", "")
                or getattr(response, "output", "")
                or "governed revoke did not execute"
            ),
        }
    except Exception as e:
        logger.debug("governed consent revoke failed: %s", e)
        return {"surface": _SURFACE, "revoked": False, "active": False, "error": str(e)}


def read_consent_state(
    operator_principal: str, device_registry_id: str, activation_mode: str
) -> dict:
    """Read-only consent state. Stable dict; never raises, never mutates."""
    try:
        from substrate.workstation.voice_consent import VoiceConsentStore

        grant = VoiceConsentStore().active_grant(
            operator_principal, device_registry_id, activation_mode
        )
        return {
            "surface": _SURFACE,
            "active": grant is not None,
            "grant": _grant_payload(grant),
            "activation_mode": activation_mode,
            "device_registry_id": device_registry_id,
            "error": None,
        }
    except Exception as e:
        logger.debug("consent state read failed: %s", e)
        # Fail-closed: an unreadable store means NO consent.
        return {
            "surface": _SURFACE,
            "active": False,
            "grant": None,
            "activation_mode": activation_mode,
            "device_registry_id": device_registry_id,
            "error": str(e),
        }


def register_voice_consent_routes(router, _require_operator_role, helpers) -> None:
    """Register the voice consent surfaces onto the given router."""

    from fastapi import Body, Depends, Query

    @router.get("/voice/consent")
    def voice_consent_state(
        device_registry_id: str = Query(...),
        mode: str = Query("push_to_talk"),
        principal: str = Depends(_require_operator_role),
    ) -> dict:
        return read_consent_state(principal, device_registry_id, mode)

    @router.post("/voice/consent/grant")
    def voice_consent_grant(
        payload: dict = Body(...),
        principal: str = Depends(_require_operator_role),
    ) -> dict:
        device = str(payload.get("device_registry_id") or "").strip()
        mode = str(payload.get("mode") or "push_to_talk").strip()
        if not device:
            return {
                "surface": _SURFACE,
                "granted": False,
                "active": False,
                "error": "device_registry_id is required",
                "code": "DEVICE_REQUIRED",
            }
        return governed_consent_grant(principal, device, mode)

    @router.post("/voice/consent/revoke")
    def voice_consent_revoke(
        payload: dict = Body(...),
        principal: str = Depends(_require_operator_role),
    ) -> dict:
        device = str(payload.get("device_registry_id") or "").strip()
        mode = str(payload.get("mode") or "push_to_talk").strip()
        if not device:
            return {
                "surface": _SURFACE,
                "revoked": False,
                "active": False,
                "error": "device_registry_id is required",
            }
        return governed_consent_revoke(principal, device, mode)
