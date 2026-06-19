"""Voice Operations API routes — Campaign 20.4."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def register_voice_ops_routes(app: object) -> None:
    """Mount voice operations routes on the cockpit app."""
    from flask import jsonify, request

    flask_app: object = app

    @flask_app.route("/voice/operations/snapshot", methods=["GET"])  # type: ignore[attr-defined]
    def voice_operations_snapshot() -> tuple:
        try:
            from substrate.workstation.voice_operations_runtime import (
                VoiceOperationsRuntime,
            )
            runtime = VoiceOperationsRuntime()
            return jsonify(runtime.snapshot().to_dict()), 200
        except Exception as exc:
            logger.debug("voice operations snapshot failed: %s", exc)
            return jsonify({"error": str(exc)}), 500

    @flask_app.route("/voice/operations/health", methods=["GET"])  # type: ignore[attr-defined]
    def voice_operations_health() -> tuple:
        try:
            from substrate.workstation.voice_operations_runtime import (
                VoiceOperationsRuntime,
            )
            runtime = VoiceOperationsRuntime()
            return jsonify({"health": runtime.health().value}), 200
        except Exception as exc:
            logger.debug("voice operations health failed: %s", exc)
            return jsonify({"error": str(exc)}), 500

    @flask_app.route("/voice/operations/process", methods=["POST"])  # type: ignore[attr-defined]
    def voice_operations_process() -> tuple:
        try:
            from substrate.workstation.voice_operations_runtime import (
                VoiceOperationsRuntime,
            )
            body = request.get_json(silent=True) or {}
            text = body.get("text", "")
            source_event = body.get("source_event", body)
            runtime = VoiceOperationsRuntime()
            result = runtime.process_utterance(source_event, text)
            return jsonify(result), 200
        except Exception as exc:
            logger.debug("voice operations process failed: %s", exc)
            return jsonify({"error": str(exc)}), 500
