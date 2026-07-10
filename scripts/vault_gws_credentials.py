"""Vault Google Workspace OAuth material into 1Password (WP-P4-PROVIDER-TOKEN-VAULTING-001).

Reads ~/.config/gws/gmail_credentials.json and creates/updates the
`Google-Workspace-OAuth` API_CREDENTIAL item in the tenant's 1Password vault.

Secret-handling contract (Credential Injection Law):
- Values flow file -> python -> `op item create` STDIN only.
- Values NEVER appear in argv, logs, stdout, stderr, or shell history.
- Output is limited to field NAMES and value LENGTHS.
- The short-lived `access_token` is deliberately NOT vaulted — access tokens
  are minted at call time from the refresh token inside the adapter process
  (see docs/audits/2026-07-06_wp_p4_adaptercall_token_seam.md section 2).

Rotation: after a new OAuth grant lands in the credentials file, re-run with
--rotate to update the existing item in place.

Usage:
    python3 scripts/vault_gws_credentials.py            # create (refuses if item exists)
    python3 scripts/vault_gws_credentials.py --rotate   # update existing item fields
"""

from __future__ import annotations

import json
import os
import subprocess  # noqa: S404 — scripts/ is exempt from the CPU gate (see CLAUDE.md)
import sys
from pathlib import Path

VAULT = os.getenv("UMH_OP_VAULT", "UMH-Production")
ITEM_TITLE = "Google-Workspace-OAuth"
CREDENTIALS_PATH = Path.home() / ".config" / "gws" / "gmail_credentials.json"

# Secret fields (CONCEALED) — these back scripts/.env.gws.tpl op:// references.
SECRET_FIELDS = ("client_id", "client_secret", "refresh_token")
# Non-secret context fields (STRING) — aid rotation, carry no credential value.
CONTEXT_FIELDS = ("token_uri",)

NOTES = (
    "Google Workspace OAuth material for the UMH provider-token seam "
    "(substrate/execution/credential_gate.py PROVIDER_TOKEN_REQUIREMENTS "
    "'google_workspace'). Injected at runtime via "
    "`op run --env-file=scripts/.env.gws.tpl`. Source of the grant: "
    "scripts/oauth_grant_gmail.py / services/oauth_device_flow.py. "
    "Rotation: re-grant, then `python3 scripts/vault_gws_credentials.py --rotate`. "
    "Cutover plan: docs/audits/2026-07-06_wp_p4_adaptercall_token_seam.md section 7."
)


def _item_exists() -> bool:
    """Check whether the target item already exists (no values touched)."""
    proc = subprocess.run(
        ["op", "item", "get", ITEM_TITLE, "--vault", VAULT],
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


def _load_material() -> dict:
    """Load credential material from the plaintext file. Values stay in-process."""
    with open(CREDENTIALS_PATH, "r") as f:
        data = json.load(f)
    missing = [k for k in SECRET_FIELDS if not data.get(k)]
    if missing:
        print(f"ERROR: credentials file missing required keys: {', '.join(missing)}")
        sys.exit(1)
    return data


def _create(data: dict) -> int:
    """Create the item by piping a full item template JSON to op via stdin."""
    fields = [
        {
            "id": "notesPlain",
            "type": "STRING",
            "purpose": "NOTES",
            "label": "notesPlain",
            "value": NOTES,
        }
    ]
    for name in SECRET_FIELDS:
        fields.append({"label": name, "type": "CONCEALED", "value": data[name]})
    for name in CONTEXT_FIELDS:
        if data.get(name):
            fields.append({"label": name, "type": "STRING", "value": str(data[name])})
    template = {
        "title": ITEM_TITLE,
        "category": "API_CREDENTIAL",
        "vault": {"name": VAULT},
        "fields": fields,
    }
    proc = subprocess.run(
        ["op", "item", "create", "--format", "json"],
        input=json.dumps(template),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        # stderr from op may echo template context on parse errors — print a
        # fixed message instead of raw stderr to guarantee no value leaks.
        print("ERROR: op item create failed (stderr suppressed to avoid value leak)")
        return proc.returncode
    created = json.loads(proc.stdout)
    print(f"created item: title={created.get('title')} id={created.get('id')} vault={VAULT}")
    return 0


def _rotate(data: dict) -> int:
    """Update secret fields on the existing item. Values pass via stdin template.

    `op item edit` takes assignments on argv (banned), so rotation re-reads the
    item id and uses `op item delete` + create — values still never hit argv.
    """
    proc = subprocess.run(
        ["op", "item", "delete", ITEM_TITLE, "--vault", VAULT],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print("ERROR: could not delete existing item for rotation")
        return proc.returncode
    print("rotation: existing item deleted, recreating with current file material")
    return _create(data)


def main() -> int:
    rotate = "--rotate" in sys.argv
    if not CREDENTIALS_PATH.exists():
        print(f"ERROR: credentials file not found: {CREDENTIALS_PATH}")
        return 1
    data = _load_material()
    for name in SECRET_FIELDS:
        print(f"field {name}: len={len(data[name])} (value not shown)")
    exists = _item_exists()
    if exists and not rotate:
        print(f"item '{ITEM_TITLE}' already exists in vault '{VAULT}' — use --rotate to update")
        return 1
    if exists and rotate:
        return _rotate(data)
    return _create(data)


if __name__ == "__main__":
    sys.exit(main())
