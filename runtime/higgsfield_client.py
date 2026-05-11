"""Higgsfield Cloud API wrapper for EOS.

Thin layer over the first-party `higgsfield-client` Python SDK that:

- reads `HIGGSFIELD_API_KEY` + `HIGGSFIELD_API_KEY_SECRET` from /opt/OS/runtime/.env
- shims them to the env var names the SDK actually wants (`HF_API_KEY`,
  `HF_API_SECRET`) so the rest of EOS can use the verbose names
- inserts a `higgsfield_jobs` row in Neon on every submit so the webhook
  handler can validate that a given `request_id` was issued by EOS
- registers a single webhook URL for every call (HIGGSFIELD_WEBHOOK_URL)
- exposes one entry point: `generate(venture, model_id, **arguments)`

See /opt/OS/skills/tools/higgsfield/ for the full skill reference.
"""
from __future__ import annotations

import json
import os
import sys
from dotenv import load_dotenv

# /opt/OS on sys.path so we can import runtime.db
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'))

# Shim the verbose EOS env var names to the SDK's expected names BEFORE
# importing the SDK (the SDK reads env vars at call time, not import time,
# but we do it at import for belt-and-braces).
_EOS_KEY = os.getenv("HIGGSFIELD_API_KEY")
_EOS_SECRET = os.getenv("HIGGSFIELD_API_KEY_SECRET")
if _EOS_KEY and _EOS_SECRET:
    os.environ.setdefault("HF_API_KEY", _EOS_KEY)
    os.environ.setdefault("HF_API_SECRET", _EOS_SECRET)

import higgsfield_client as hf  # noqa: E402

from runtime.db import get_conn  # noqa: E402

WEBHOOK_URL = os.getenv(
    "HIGGSFIELD_WEBHOOK_URL",
    "https://eos.munozconglomerate.com/webhooks/higgsfield",
)


def generate(
    venture: str,
    model_id: str,
    *,
    register_webhook: bool = True,
    **arguments,
) -> str:
    """Submit a Higgsfield generation and return the request_id.

    Writes a row into `higgsfield_jobs` before submitting so the webhook
    handler can validate the `request_id` belongs to EOS. Caller should
    NOT poll — the webhook handler owns terminal state.

    Args:
        venture: short slug ('personal_brand', 'lyfe_spectrum',
                 'empyrean_studio', 'initiate_arena').
        model_id: full Higgsfield model path, e.g.
                  'higgsfield-ai/soul/standard',
                  'higgsfield-ai/dop/standard',
                  'bytedance/seedream/v4/text-to-image',
                  'kling-video/v2.1/pro/image-to-video'.
        register_webhook: if True (default), pass WEBHOOK_URL to the SDK.
        **arguments: model-specific arguments (prompt, image_url,
                     aspect_ratio, resolution, duration, etc.).

    Returns:
        The `request_id` UUID string.
    """
    controller = hf.submit(
        model_id,
        arguments=arguments,
        webhook_url=WEBHOOK_URL if register_webhook else None,
    )
    # The SDK 0.1.0 SyncRequestController does not expose `.request_id` as
    # a public attribute in every version — read from build_urls() output
    # which returns the status url, then derive the id from the path tail.
    try:
        request_id = controller.request_id  # type: ignore[attr-defined]
    except AttributeError:
        urls = controller.build_urls()
        # status url format: .../requests/{request_id}/status
        request_id = urls["status_url"].rstrip("/").rsplit("/", 2)[-2]

    with get_conn() as cur:
        cur.execute(
            """
            INSERT INTO higgsfield_jobs
                (request_id, venture, model_id, arguments, status, submitted_at)
            VALUES (%s, %s, %s, %s::jsonb, 'queued', now())
            ON CONFLICT (request_id) DO NOTHING
            """,
            (request_id, venture, model_id, json.dumps(arguments)),
        )

    return request_id


def get_status(request_id: str) -> str:
    """One-shot status read for a known request_id. Webhook is preferred."""
    s = hf.status(request_id)
    return s.__class__.__name__  # Queued | InProgress | Completed | Failed | NSFW | Cancelled


def cancel(request_id: str) -> None:
    """Cancel a queued request."""
    hf.cancel(request_id)
    with get_conn() as cur:
        cur.execute(
            "UPDATE higgsfield_jobs SET status='Cancelled', finished_at=now() "
            "WHERE request_id=%s",
            (request_id,),
        )


__all__ = ["generate", "get_status", "cancel", "WEBHOOK_URL"]
