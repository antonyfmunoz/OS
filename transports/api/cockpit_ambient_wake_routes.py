"""Ambient Wake API routes — Campaign 20.2."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def register_ambient_wake_routes(app: object) -> None:
    """Mount ambient wake routes on the cockpit app."""
    from flask import jsonify, request

    flask_app: object = app

    @flask_app.route("/voice/ambient/status", methods=["GET"])  # type: ignore[attr-defined]
    def voice_ambient_status() -> tuple:
        try:
            from substrate.workstation.ambient_wake_runtime import (
                AmbientWakeRuntime,
            )
            runtime = AmbientWakeRuntime()
            return jsonify(runtime.snapshot().to_dict()), 200
        except Exception as exc:
            logger.debug("ambient wake status failed: %s", exc)
            return jsonify({"error": str(exc)}), 500

    @flask_app.route("/voice/ambient/wake", methods=["POST"])  # type: ignore[attr-defined]
    def voice_ambient_wake() -> tuple:
        try:
            from substrate.workstation.ambient_wake_runtime import (
                AmbientWakeRuntime,
            )
            body = request.get_json(silent=True) or {}
            runtime = AmbientWakeRuntime()
            runtime.activate()
            transition = runtime.on_wake_detected(
                device_id=body.get("device_id", "local"),
                phrase=body.get("phrase", ""),
            )
            return jsonify(transition.to_dict()), 200
        except Exception as exc:
            logger.debug("ambient wake trigger failed: %s", exc)
            return jsonify({"error": str(exc)}), 500
