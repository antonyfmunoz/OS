"""
Small helpers for proposing MVP SafeActions to a named station.

Used by smoke tests, admin scripts, and scheduled rituals to drop a single
safe action on the bus without reconstructing the StationContract dance.
Everything here still routes through StationContract.propose() so the
trust gates (control mode + MVP allow-list) cannot be bypassed.
"""

from __future__ import annotations

from typing import Optional

from runtime.transport.actions import ActionKind, SafeAction
from runtime.transport.station import ControlMode, StationContract


def _contract_in_drive(node_id: str) -> StationContract:
    contract = StationContract(node_id=node_id)
    contract.control_mode = ControlMode.DRIVE
    return contract


def propose_speak_text(
    node_id: str,
    text: str,
    *,
    voice: Optional[str] = None,
    issued_by: str = "substrate.helper",
) -> SafeAction:
    """Propose a SPEAK_TEXT action to the given node. Returns the dispatched SafeAction."""
    payload: dict = {"text": text}
    if voice:
        payload["voice"] = voice
    action = SafeAction(
        kind=ActionKind.SPEAK_TEXT,
        payload=payload,
        issued_by=issued_by,
    )
    return _contract_in_drive(node_id).propose(action)


def propose_open_url(
    node_id: str,
    url: str,
    *,
    issued_by: str = "substrate.helper",
) -> SafeAction:
    """Propose an OPEN_URL action. Scheme validation happens at execution time."""
    action = SafeAction(
        kind=ActionKind.OPEN_URL,
        payload={"url": url},
        issued_by=issued_by,
    )
    return _contract_in_drive(node_id).propose(action)


def propose_launch_app(
    node_id: str,
    app_id: str,
    *,
    args: Optional[list] = None,
    issued_by: str = "substrate.helper",
) -> SafeAction:
    """Propose a LAUNCH_APP action. app_id must be in the allow-list."""
    payload: dict = {"app_id": app_id}
    if args:
        payload["args"] = list(args)
    action = SafeAction(
        kind=ActionKind.LAUNCH_APP,
        payload=payload,
        issued_by=issued_by,
    )
    return _contract_in_drive(node_id).propose(action)


def propose_focus_app(
    node_id: str,
    app_id: str,
    *,
    issued_by: str = "substrate.helper",
) -> SafeAction:
    """Propose a FOCUS_APP action. app_id must be in the allow-list."""
    action = SafeAction(
        kind=ActionKind.FOCUS_APP,
        payload={"app_id": app_id},
        issued_by=issued_by,
    )
    return _contract_in_drive(node_id).propose(action)


def propose_open_scene(
    node_id: str,
    scene: str,
    *,
    issued_by: str = "substrate.helper",
) -> SafeAction:
    """Propose an OPEN_SCENE action. Scene must exist in SCENE_REGISTRY."""
    action = SafeAction(
        kind=ActionKind.OPEN_SCENE,
        payload={"scene": scene},
        issued_by=issued_by,
    )
    return _contract_in_drive(node_id).propose(action)


def propose_play_sound(
    node_id: str,
    *,
    sound_id: Optional[str] = None,
    path: Optional[str] = None,
    issued_by: str = "substrate.helper",
) -> SafeAction:
    """Propose a PLAY_SOUND action to the given node. Returns the dispatched SafeAction."""
    if not (sound_id or path):
        raise ValueError("propose_play_sound requires sound_id or path")
    payload: dict = {}
    if sound_id:
        payload["sound_id"] = sound_id
    if path:
        payload["path"] = path
    action = SafeAction(
        kind=ActionKind.PLAY_SOUND,
        payload=payload,
        issued_by=issued_by,
    )
    return _contract_in_drive(node_id).propose(action)
