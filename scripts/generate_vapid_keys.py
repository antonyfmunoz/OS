#!/usr/bin/env python3
"""Generate VAPID key pair for Web Push notifications.

Run once, then add the output to services/.env:
  VAPID_PUBLIC_KEY=<public_key>
  VAPID_PRIVATE_KEY=<private_key>
  VAPID_CLAIMS_EMAIL=<your_email>
"""

from __future__ import annotations

import os

try:
    from py_vapid import Vapid  # type: ignore[import-untyped]
except ImportError:
    print("pip install py-vapid  # then re-run this script")
    raise SystemExit(1)

vapid = Vapid()
vapid.generate_keys()

email = os.environ.get("VAPID_CLAIMS_EMAIL", "admin@example.com")

print("Add these to services/.env:\n")
print(f"VAPID_PUBLIC_KEY={vapid.public_key_urlsafe_base64()}")
print(f"VAPID_PRIVATE_KEY={vapid.private_key_urlsafe_base64()}")
print(f"VAPID_CLAIMS_EMAIL={email}")
