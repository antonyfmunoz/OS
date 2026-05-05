"""Higgsfield Cloud API webhook receiver.

Flask endpoint at POST /webhooks/higgsfield that:

1. Validates the incoming request_id exists in higgsfield_jobs and is
   still unfinished (idempotency + EOS-issued validation in one query).
2. Downloads the generated image/video to /opt/OS/media/higgsfield/
   immediately on Completed status (Higgsfield has 7-day file retention).
3. Updates the job row with terminal status and local path.

No signature verification — Higgsfield does not document one. The
combination of "request_id must exist in our DB as unfinished" and
"request_id is an opaque UUID" provides practical protection.

Run standalone:
    python3 /opt/OS/umh/interfaces/webhooks/higgsfield.py
Or mount /webhooks/higgsfield on an existing Flask app via the
`register(app)` helper.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

import requests
from flask import Flask, jsonify, request

sys.path.insert(0, "/opt/OS")
from umh.storage.adapters.neon import get_conn  # noqa: E402

MEDIA_ROOT = Path("/opt/OS/media/higgsfield")
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 16):
                f.write(chunk)


def _extract_output_url(payload: dict) -> tuple[str | None, str]:
    """Return (url, ext) for the completed media, or (None, '')."""
    imgs = payload.get("images") or []
    if imgs and imgs[0].get("url"):
        return imgs[0]["url"], "jpg"
    video = payload.get("video") or {}
    if video.get("url"):
        return video["url"], "mp4"
    return None, ""


def handle_webhook(payload: dict) -> tuple[dict, int]:
    """Pure function — useful for tests. Called by the Flask route."""
    rid = payload.get("request_id")
    status = payload.get("status", "")
    if not rid:
        return {"error": "missing request_id"}, 400

    with get_conn() as cur:
        cur.execute(
            "SELECT id, venture, model_id, finished_at "
            "FROM higgsfield_jobs WHERE request_id=%s",
            (rid,),
        )
        row = cur.fetchone()

        if row is None:
            # Unknown request_id — not issued by EOS. Ack to prevent
            # Higgsfield retrying for 2 hours, but do nothing.
            print(f"[higgsfield_webhook] unknown request_id={rid}, acking")
            return {"ok": True, "unknown": True}, 200

        if row["finished_at"] is not None:
            # Already processed — Higgsfield redelivery. Ack.
            return {"ok": True, "duplicate": True}, 200

        local_path: str | None = None
        error: str | None = None

        if status == "Completed":
            url, ext = _extract_output_url(payload)
            if url:
                date = datetime.utcnow().strftime("%Y-%m-%d")
                dest = MEDIA_ROOT / row["venture"] / date / f"{rid}.{ext}"
                try:
                    _download(url, dest)
                    local_path = str(dest)
                except Exception as e:
                    error = f"download failed: {e}"
                    print(f"[higgsfield_webhook] {error} rid={rid}")
        elif status in ("Failed", "NSFW", "Cancelled"):
            error = payload.get("error") or status

        cur.execute(
            """
            UPDATE higgsfield_jobs
               SET status=%s,
                   output_url=%s,
                   local_path=%s,
                   error=%s,
                   finished_at=now()
             WHERE request_id=%s
            """,
            (
                status,
                _extract_output_url(payload)[0],
                local_path,
                error,
                rid,
            ),
        )

    return {"ok": True, "status": status, "local_path": local_path}, 200


def register(app: Flask) -> None:
    """Mount /webhooks/higgsfield on an existing Flask app."""

    @app.post("/webhooks/higgsfield")
    def _higgsfield_webhook_route():  # type: ignore[unused-ignore]
        payload = request.get_json(silent=True) or {}
        body, code = handle_webhook(payload)
        return jsonify(body), code


if __name__ == "__main__":
    app = Flask(__name__)
    register(app)

    @app.get("/health")
    def _health():
        return jsonify({"ok": True, "service": "higgsfield_webhook"})

    port = int(os.getenv("HIGGSFIELD_WEBHOOK_PORT", "5055"))
    app.run(host="0.0.0.0", port=port)
