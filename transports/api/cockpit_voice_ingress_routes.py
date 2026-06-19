"""Voice Ingress API routes — Campaign 20.0."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def register_voice_ingress_routes(app: object) -> None:
    """Mount voice ingress routes on the cockpit app."""
    from flask import jsonify

    flask_app: object = app

    @flask_app.route("/voice/ingress/status", methods=["GET"])  # type: ignore[attr-defined]
    def voice_ingress_status() -> tuple:
        try:
            from substrate.workstation.voice_ingress_runtime import (
                VoiceIngressRuntime,
            )
            runtime = VoiceIngressRuntime()
            return jsonify(runtime.snapshot().to_dict()), 200
        except Exception as exc:
            logger.debug("voice ingress status failed: %s", exc)
            return jsonify({"error": str(exc)}), 500

    @flask_app.route("/voice/ingress/sources", methods=["GET"])  # type: ignore[attr-defined]
    def voice_ingress_sources() -> tuple:
        try:
            from substrate.workstation.voice_ingress_runtime import (
                VoiceIngressRuntime,
            )
            runtime = VoiceIngressRuntime()
            return jsonify({"sources": runtime.active_sources()}), 200
        except Exception as exc:
            logger.debug("voice ingress sources failed: %s", exc)
            return jsonify({"error": str(exc)}), 500
