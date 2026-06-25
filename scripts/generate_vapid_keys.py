#!/usr/bin/env python3
"""Generate VAPID key pair for Web Push notifications.

Run once, then add the output to services/.env:
  VAPID_PUBLIC_KEY=<public_key>
  VAPID_PRIVATE_KEY=<private_key>
  VAPID_CLAIMS_EMAIL=<your_email>
"""

from __future__ import annotations

import base64
import os

try:
    from py_vapid import Vapid  # type: ignore[import-untyped]
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
except ImportError:
    print("pip install py-vapid cryptography  # then re-run this script")
    raise SystemExit(1)

vapid = Vapid()
vapid.generate_keys()

raw_pub = vapid.public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
pub_b64 = base64.urlsafe_b64encode(raw_pub).rstrip(b"=").decode()
priv_raw = vapid.private_key.private_numbers().private_value.to_bytes(32, "big")
priv_b64 = base64.urlsafe_b64encode(priv_raw).rstrip(b"=").decode()

email = os.environ.get("VAPID_CLAIMS_EMAIL", "admin@example.com")

print("Add these to services/.env:\n")
print(f"VAPID_PUBLIC_KEY={pub_b64}")
print(f"VAPID_PRIVATE_KEY={priv_b64}")
print(f"VAPID_CLAIMS_EMAIL={email}")
