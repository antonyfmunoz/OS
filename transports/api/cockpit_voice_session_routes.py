"""Voice Session API routes — Campaign 20.1."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def register_voice_session_routes(app: object) -> None:
    """Mount voice session routes on the cockpit app."""
    from flask import jsonify, request

    flask_app: object = app

    @flask_app.route("/voice/sessions", methods=["GET"])  # type: ignore[attr-defined]
    def voice_sessions_list() -> tuple:
        try:
            from substrate.workstation.voice_session_manager import (
                VoiceSessionManager,
            )
            mgr = VoiceSessionManager()
            return jsonify(mgr.snapshot().to_dict()), 200
        except Exception as exc:
            logger.debug("voice sessions list failed: %s", exc)
            return jsonify({"error": str(exc)}), 500

    @flask_app.route("/voice/sessions/start", methods=["POST"])  # type: ignore[attr-defined]
    def voice_session_start() -> tuple:
        try:
            from substrate.workstation.voice_ingress_runtime import (
                VoiceIngressEvent,
            )
            from substrate.workstation.voice_session_manager import (
                VoiceSessionManager,
            )
            body = request.get_json(silent=True) or {}
            event = VoiceIngressEvent(
                source_type=body.get("source_type", "right_rail"),
                device_id=body.get("device_id", ""),
                speaker_id=body.get("speaker_id", ""),
                activation_mode=body.get("activation_mode", "push_to_talk"),
            )
            mgr = VoiceSessionManager()
            session = mgr.start_session(event)
            return jsonify(session.to_dict()), 201
        except Exception as exc:
            logger.debug("voice session start failed: %s", exc)
            return jsonify({"error": str(exc)}), 500

    @flask_app.route("/voice/sessions/<session_id>/end", methods=["POST"])  # type: ignore[attr-defined]
    def voice_session_end(session_id: str) -> tuple:
        try:
            from substrate.workstation.voice_session_manager import (
                VoiceSessionManager,
            )
            mgr = VoiceSessionManager()
            success = mgr.end_session(session_id)
            return jsonify({"ended": success, "session_id": session_id}), 200
        except Exception as exc:
            logger.debug("voice session end failed: %s", exc)
            return jsonify({"error": str(exc)}), 500
