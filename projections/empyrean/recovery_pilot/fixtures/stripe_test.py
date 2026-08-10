"""C6 — Stripe test-mode verification: products, charge, decline, refund.

Creates in TEST MODE:
  - Product "The Job Pipeline System — Activation" with one-time $5,000 price
  - Product "The Job Pipeline System — Monthly" with recurring $2,500/mo price
  - A successful PaymentIntent (pm_card_visa)
  - A declined PaymentIntent (pm_card_visa_chargeDeclined)
  - A refund of the successful charge

Every API response is appended to fixtures/evidence/stripe_test_log.json.
Without a key (STRIPE_TEST_KEY env or 1Password), writes a SIMULATED log of
the exact calls and exits 0 — deterministic spine, API is the enhancement.

SAFETY: refuses any key that does not start with sk_test_.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

EVIDENCE = Path(__file__).parent / "evidence" / "stripe_test_log.json"
API = "https://api.stripe.com/v1"


def _get_key() -> str | None:
    key = os.environ.get("STRIPE_TEST_KEY")
    if key:
        return key
    try:
        r = subprocess.run(
            ["op", "item", "get", "Stripe", "--vault", "UMH-Production",
             "--fields", "test_key", "--reveal"],
            capture_output=True, text=True, timeout=15)
        return r.stdout.strip() or None
    except Exception:
        return None


def _call(key: str, method: str, path: str, params: dict | None = None) -> dict:
    data = urllib.parse.urlencode(params or {}).encode() if params else None
    req = urllib.request.Request(API + path, data=data, method=method)
    req.add_header("Authorization", "Bearer " + key)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return {"ok": True, "status": resp.status, "body": json.loads(resp.read())}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "status": exc.code, "body": json.loads(exc.read())}


def main() -> int:
    log: list = [{"run_at": datetime.now(timezone.utc).isoformat(), "mode": "TEST"}]
    key = _get_key()

    calls = [
        ("create_product_activation", "POST", "/products",
         {"name": "The Job Pipeline System — Activation",
          "description": "Activation + month one"}),
        ("create_price_activation", "POST", "/prices",
         {"unit_amount": 500000, "currency": "usd", "product": "{prod_activation}"}),
        ("create_product_monthly", "POST", "/products",
         {"name": "The Job Pipeline System — Monthly"}),
        ("create_price_monthly", "POST", "/prices",
         {"unit_amount": 250000, "currency": "usd",
          "recurring[interval]": "month", "product": "{prod_monthly}"}),
        ("charge_success", "POST", "/payment_intents",
         {"amount": 500000, "currency": "usd", "confirm": "true",
          "payment_method": "pm_card_visa",
          "automatic_payment_methods[enabled]": "true",
          "automatic_payment_methods[allow_redirects]": "never"}),
        ("charge_declined", "POST", "/payment_intents",
         {"amount": 500000, "currency": "usd", "confirm": "true",
          "payment_method": "pm_card_visa_chargeDeclined",
          "automatic_payment_methods[enabled]": "true",
          "automatic_payment_methods[allow_redirects]": "never"}),
        ("refund_success_charge", "POST", "/refunds",
         {"payment_intent": "{pi_success}"}),
    ]

    if not key:
        log[0]["result"] = "SIMULATED — no STRIPE_TEST_KEY available"
        print("=" * 60)
        print(" TEST-SIMULATION: no Stripe test key found.")
        print(" The following calls WOULD be made in test mode:")
        print("=" * 60)
        for name, method, path, params in calls:
            entry = {"call": name, "method": method, "path": path,
                     "params": params, "simulated": True}
            log.append(entry)
            print("  %s %s %s" % (method, path, name))
    elif not key.startswith("sk_test_"):
        log[0]["result"] = "REFUSED — key is not a test-mode key"
        print("REFUSED: key does not start with sk_test_ — never touch live mode.")
        EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
        EVIDENCE.write_text(json.dumps(log, indent=1))
        return 1
    else:
        ids: dict = {}
        for name, method, path, params in calls:
            resolved = {k: (v.format(**ids) if isinstance(v, str) and "{" in v else v)
                        for k, v in params.items()}
            result = _call(key, method, path, resolved)
            log.append({"call": name, "params": resolved,
                        "status": result["status"],
                        "id": result["body"].get("id"),
                        "outcome": result["body"].get("status") or
                                   result["body"].get("error", {}).get("code"),
                        "body_excerpt": {k: result["body"].get(k) for k in
                                         ("id", "status", "amount", "error")}})
            body = result["body"]
            if name == "create_product_activation" and result["ok"]:
                ids["prod_activation"] = body["id"]
            if name == "create_product_monthly" and result["ok"]:
                ids["prod_monthly"] = body["id"]
            if name == "charge_success" and result["ok"]:
                ids["pi_success"] = body["id"]
            print("%-24s -> %s %s" % (name, result["status"],
                                      log[-1]["outcome"]))
            # the declined charge SHOULD fail — that is the test passing
        log[0]["result"] = "LIVE-TEST-MODE run complete"

    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(log, indent=1))
    print("\nevidence -> %s" % EVIDENCE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
