"""Voice Output API routes — Campaign 20.3."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def register_voice_output_routes(app: object) -> None:
    """Mount voice output routes on the cockpit app."""
    from flask import jsonify

    flask_app: object = app

    @flask_app.route("/voice/output/status", methods=["GET"])  # type: ignore[attr-defined]
    def voice_output_status() -> tuple:
        try:
            from substrate.workstation.voice_output_runtime import (
                VoiceOutputRuntime,
            )
            runtime = VoiceOutputRuntime()
            return jsonify(runtime.snapshot().to_dict()), 200
        except Exception as exc:
            logger.debug("voice output status failed: %s", exc)
            return jsonify({"error": str(exc)}), 500
