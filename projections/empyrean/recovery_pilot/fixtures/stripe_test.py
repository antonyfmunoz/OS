"""C6 — Stripe test-mode fixture for The Job Pipeline System.

Creates the billing objects the offer actually sells, in TEST MODE ONLY:

  1. Product "The Job Pipeline System - Activation" + one-time $5,000 price
  2. Product "The Job Pipeline System - Monthly" + recurring $2,500/mo price
  3. A successful PaymentIntent (pm_card_visa)
  4. A declined PaymentIntent (pm_card_visa_chargeDeclined)
  5. A refund of the successful charge

Every API request and response is written to
fixtures/evidence/stripe_test_log.json.

Key resolution order:
  1. STRIPE_TEST_KEY env var
  2. `op item get Stripe --vault UMH-Production --fields test_key`
  3. no key -> SIMULATION mode: writes the exact calls it WOULD make,
     prints a loud banner, and exits 0.

LIVE-MODE GUARD: the key must start with "sk_test_". Anything else --
including a live key supplied deliberately -- is refused before any
network call. There is no override flag, by design.

stdlib only (urllib). `requests` may not exist in this environment.

Usage:
    python3 stripe_test.py            # run (real or simulated)
    python3 stripe_test.py --simulate # force simulation, ignore any key
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
from typing import Any

API_BASE = "https://api.stripe.com/v1"
EVIDENCE_DIR = Path(__file__).parent / "evidence"
LOG_PATH = EVIDENCE_DIR / "stripe_test_log.json"

TEST_KEY_PREFIX = "sk_test_"

# Offer canon — these figures are the offer, not example values.
ACTIVATION_NAME = "The Job Pipeline System - Activation"
ACTIVATION_AMOUNT_CENTS = 500_000          # $5,000 start (activation + month one)
MONTHLY_NAME = "The Job Pipeline System - Monthly"
MONTHLY_AMOUNT_CENTS = 250_000             # $2,500/mo
CURRENCY = "usd"

SUCCESS_TOKEN = "pm_card_visa"
DECLINE_TOKEN = "pm_card_visa_chargeDeclined"

TIMEOUT_SECONDS = 30


# ------------------------------------------------------------------ log

class EvidenceLog:
    """Accumulates every call/response pair and writes one JSON artifact."""

    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.entries: list[dict[str, Any]] = []

    def record(self, step: str, method: str, path: str,
               params: dict[str, Any], response: Any,
               status: int | None = None, error: str | None = None) -> None:
        self.entries.append({
            "step": step,
            "request": {"method": method, "url": f"{API_BASE}{path}",
                        "params": params},
            "response": response,
            "http_status": status,
            "error": error,
            "at": datetime.now(timezone.utc).isoformat(),
        })
        marker = "OK " if error is None else "ERR"
        print(f"  [{marker}] {step}")

    def write(self, summary: dict[str, Any]) -> None:
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "artifact": "C6 Stripe test-mode fixture",
            "offer": "The Job Pipeline System",
            "mode": self.mode,
            "started_at": self.started_at,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "summary": summary,
            "calls": self.entries,
        }
        with open(LOG_PATH, "w") as fh:
            json.dump(payload, fh, indent=2)
        print(f"\nEvidence written: {LOG_PATH}")


# ------------------------------------------------------------- key load

def _key_from_1password() -> str | None:
    """Best-effort 1Password lookup. The item may not exist — that is fine."""
    try:
        result = subprocess.run(
            ["op", "item", "get", "Stripe",
             "--vault", "UMH-Production", "--fields", "test_key"],
            capture_output=True, text=True, timeout=15, check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        print(f"  1Password lookup unavailable: {type(exc).__name__}")
        return None
    if result.returncode != 0:
        detail = (result.stderr or "").strip().splitlines()
        print(f"  1Password item not found: {detail[0] if detail else 'no detail'}")
        return None
    key = result.stdout.strip()
    return key or None


def resolve_key() -> str | None:
    """Env var first, then 1Password. None means simulation."""
    key = os.environ.get("STRIPE_TEST_KEY", "").strip()
    if key:
        print("  key source: STRIPE_TEST_KEY env var")
        return key
    print("  STRIPE_TEST_KEY not set — trying 1Password")
    key = _key_from_1password()
    if key:
        print("  key source: 1Password UMH-Production/Stripe/test_key")
    return key


def assert_test_mode(key: str) -> None:
    """Refuse anything that is not a test key. No override exists."""
    if not key.startswith(TEST_KEY_PREFIX):
        prefix = key[:8] if len(key) >= 8 else "(too short)"
        print("\n" + "!" * 68)
        print("REFUSED: key does not start with 'sk_test_'.")
        print(f"Key prefix seen: {prefix}...")
        print("This fixture creates products, charges, and refunds.")
        print("It will never run against live mode.")
        print("!" * 68)
        sys.exit(2)


# ------------------------------------------------------------ transport

def _encode(params: dict[str, Any]) -> bytes:
    """Stripe expects form encoding with bracket notation for nesting."""
    flat: list[tuple[str, str]] = []
    for key, value in params.items():
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                flat.append((f"{key}[{sub_key}]", str(sub_value)))
        elif isinstance(value, bool):
            flat.append((key, "true" if value else "false"))
        else:
            flat.append((key, str(value)))
    return urllib.parse.urlencode(flat).encode()


def api_call(key: str, log: EvidenceLog, step: str, path: str,
             params: dict[str, Any]) -> dict[str, Any] | None:
    """POST to Stripe. Returns parsed JSON, or None on error.

    Stripe returns structured JSON on failure too (including card
    declines), so an error body is evidence and gets logged as such.
    """
    request = urllib.request.Request(
        f"{API_BASE}{path}",
        data=_encode(params),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Stripe-Version": "2024-06-20",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as resp:
            body = json.loads(resp.read().decode())
            log.record(step, "POST", path, params, body, status=resp.status)
            return body
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = {"raw": raw}
        err = body.get("error", {}).get("message", f"HTTP {exc.code}")
        log.record(step, "POST", path, params, body, status=exc.code, error=err)
        return body
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        log.record(step, "POST", path, params, None, error=str(exc))
        return None


# ------------------------------------------------------------- the run

def planned_calls() -> list[dict[str, Any]]:
    """The exact call sequence — shared by live and simulated runs."""
    return [
        {"step": "1. create activation product",
         "path": "/products",
         "params": {"name": ACTIVATION_NAME,
                    "description": "Activation + month one. 3-month initial term."}},
        {"step": "2. create activation price ($5,000 one-time)",
         "path": "/prices",
         "params": {"unit_amount": ACTIVATION_AMOUNT_CENTS,
                    "currency": CURRENCY, "product": "<activation_product_id>"}},
        {"step": "3. create monthly product",
         "path": "/products",
         "params": {"name": MONTHLY_NAME,
                    "description": "Ongoing delivery. $2,500/mo."}},
        {"step": "4. create monthly price ($2,500/mo recurring)",
         "path": "/prices",
         "params": {"unit_amount": MONTHLY_AMOUNT_CENTS,
                    "currency": CURRENCY, "product": "<monthly_product_id>",
                    "recurring": {"interval": "month"}}},
        {"step": "5. successful PaymentIntent ($5,000, confirmed)",
         "path": "/payment_intents",
         "params": {"amount": ACTIVATION_AMOUNT_CENTS, "currency": CURRENCY,
                    "payment_method": SUCCESS_TOKEN, "confirm": True,
                    "description": f"{ACTIVATION_NAME} - test charge",
                    "automatic_payment_methods": {"enabled": True,
                                                  "allow_redirects": "never"}}},
        {"step": "6. declined PaymentIntent (expected to fail)",
         "path": "/payment_intents",
         "params": {"amount": ACTIVATION_AMOUNT_CENTS, "currency": CURRENCY,
                    "payment_method": DECLINE_TOKEN, "confirm": True,
                    "description": f"{ACTIVATION_NAME} - decline path",
                    "automatic_payment_methods": {"enabled": True,
                                                  "allow_redirects": "never"}}},
        {"step": "7. refund the successful charge",
         "path": "/refunds",
         "params": {"payment_intent": "<successful_payment_intent_id>",
                    "reason": "requested_by_customer"}},
    ]


def run_simulation(reason: str) -> int:
    """No key: write the exact calls we would make. Always exits 0."""
    banner = "=" * 68
    print(f"\n{banner}\n  TEST-SIMULATION MODE — NO STRIPE CALLS WERE MADE\n{banner}")
    print(f"  Reason: {reason}")
    print("  Writing the exact API call sequence to evidence instead.\n")

    log = EvidenceLog(mode="SIMULATION")
    for call in planned_calls():
        log.record(call["step"], "POST", call["path"], call["params"],
                   response={"simulated": True,
                             "note": "no request sent; no key available"})

    log.write({
        "simulated": True,
        "reason": reason,
        "calls_planned": len(planned_calls()),
        "activation_price_usd": ACTIVATION_AMOUNT_CENTS / 100,
        "monthly_price_usd": MONTHLY_AMOUNT_CENTS / 100,
        "to_run_for_real": (
            "export STRIPE_TEST_KEY=sk_test_... && python3 stripe_test.py"),
    })
    print(f"\n{banner}\n  SIMULATION COMPLETE — this is not proof of a working\n"
          f"  Stripe integration. Rerun with a test key for real evidence.\n{banner}")
    return 0


def run_live(key: str) -> int:
    """Real test-mode run against Stripe."""
    print("\n=== STRIPE TEST MODE — real API calls (test key) ===\n")
    log = EvidenceLog(mode="TEST")
    summary: dict[str, Any] = {"simulated": False}

    activation = api_call(key, log, "1. create activation product", "/products",
                          {"name": ACTIVATION_NAME,
                           "description": "Activation + month one. "
                                          "3-month initial term."})
    if not activation or not activation.get("id"):
        log.write({**summary, "aborted": "could not create activation product"})
        print("\nABORTED: first call failed. See evidence log.")
        return 1
    summary["activation_product_id"] = activation["id"]

    act_price = api_call(key, log, "2. create activation price ($5,000 one-time)",
                         "/prices",
                         {"unit_amount": ACTIVATION_AMOUNT_CENTS,
                          "currency": CURRENCY, "product": activation["id"]})
    if act_price and act_price.get("id"):
        summary["activation_price_id"] = act_price["id"]

    monthly = api_call(key, log, "3. create monthly product", "/products",
                       {"name": MONTHLY_NAME,
                        "description": "Ongoing delivery. $2,500/mo."})
    if monthly and monthly.get("id"):
        summary["monthly_product_id"] = monthly["id"]
        mon_price = api_call(key, log,
                             "4. create monthly price ($2,500/mo recurring)",
                             "/prices",
                             {"unit_amount": MONTHLY_AMOUNT_CENTS,
                              "currency": CURRENCY, "product": monthly["id"],
                              "recurring": {"interval": "month"}})
        if mon_price and mon_price.get("id"):
            summary["monthly_price_id"] = mon_price["id"]

    charged = api_call(key, log, "5. successful PaymentIntent ($5,000, confirmed)",
                       "/payment_intents",
                       {"amount": ACTIVATION_AMOUNT_CENTS, "currency": CURRENCY,
                        "payment_method": SUCCESS_TOKEN, "confirm": True,
                        "description": f"{ACTIVATION_NAME} - test charge",
                        "automatic_payment_methods": {
                            "enabled": True, "allow_redirects": "never"}})
    charge_id = None
    if charged and charged.get("status") == "succeeded":
        charge_id = charged["id"]
        summary["succeeded_payment_intent"] = charge_id
    else:
        summary["succeeded_payment_intent"] = None

    declined = api_call(key, log, "6. declined PaymentIntent (expected to fail)",
                        "/payment_intents",
                        {"amount": ACTIVATION_AMOUNT_CENTS, "currency": CURRENCY,
                         "payment_method": DECLINE_TOKEN, "confirm": True,
                         "description": f"{ACTIVATION_NAME} - decline path",
                         "automatic_payment_methods": {
                             "enabled": True, "allow_redirects": "never"}})
    # A decline is the SUCCESS condition for this step.
    decline_code = (declined or {}).get("error", {}).get("decline_code") \
        or (declined or {}).get("error", {}).get("code")
    summary["decline_observed"] = bool(decline_code)
    summary["decline_code"] = decline_code

    if charge_id:
        refund = api_call(key, log, "7. refund the successful charge", "/refunds",
                          {"payment_intent": charge_id,
                           "reason": "requested_by_customer"})
        summary["refund_id"] = (refund or {}).get("id")
        summary["refund_status"] = (refund or {}).get("status")
    else:
        log.record("7. refund the successful charge", "POST", "/refunds",
                   {"payment_intent": None}, response=None,
                   error="skipped — no successful PaymentIntent to refund")
        summary["refund_id"] = None

    log.write(summary)

    ok = bool(summary.get("activation_product_id")
              and summary.get("succeeded_payment_intent")
              and summary.get("decline_observed")
              and summary.get("refund_id"))
    print("\n=== RESULT ===")
    print(f"  activation product : {summary.get('activation_product_id')}")
    print(f"  monthly product    : {summary.get('monthly_product_id')}")
    print(f"  charge succeeded   : {summary.get('succeeded_payment_intent')}")
    print(f"  decline observed   : {summary.get('decline_code')}")
    print(f"  refund             : {summary.get('refund_id')}")
    print(f"\n  All four rails proven: {'YES' if ok else 'NO — see log'}")
    return 0 if ok else 1


def main() -> int:
    print("C6 — Stripe fixture · The Job Pipeline System")
    print("Offer: $5,000 start + $2,500/mo, 3-month initial term\n")

    if "--simulate" in sys.argv:
        return run_simulation("--simulate flag passed")

    key = resolve_key()
    if not key:
        return run_simulation(
            "no STRIPE_TEST_KEY env var and no 1Password item found")

    assert_test_mode(key)
    return run_live(key)


if __name__ == "__main__":
    sys.exit(main())
