"""C1 — THE calculation engine. Pipeline math exists exactly once.

Both the Pipeline Snapshot (self-reported inputs, outside-in) and the
Job Pipeline Audit (CRM export, inside) call these functions. If the two
surfaces ever disagree on identical inputs, that is a defect in the
caller, never a second formula.

All dollar outputs are ESTIMATES. The offer guarantees activated
qualified opportunities, never revenue — every rendering surface must
print the assumptions this module returns alongside the numbers.
"""
from __future__ import annotations

from datetime import date, datetime

from ..runtime.notion_schema import (
    CONDITION_MIN_OPEN_ESTIMATES,
    CONDITION_MIN_PAST_CUSTOMERS,
    GUARANTEE_MAX_OPPORTUNITIES,
    GUARANTEE_MIN_OPPORTUNITIES,
    OPEN_ESTIMATE_MAX_AGE_MONTHS,
)

# Canonical assumptions — printed on every surface that shows dollars.
DEFAULTS = {
    "avg_job_value": 18_000,
    "estimate_response_low": 0.10, "estimate_response_high": 0.25,
    "past_customer_response_low": 0.05, "past_customer_response_high": 0.15,
    "missed_call_recovery_low": 0.20, "missed_call_recovery_high": 0.40,
    "close_rate": 0.35,  # client's own close rate on activated opportunities
}


def assumptions_text(cfg: dict) -> str:
    """Human-readable assumptions line for on-page disclosure."""
    return (
        "Estimates. Assumptions: open-estimate response %d-%d%%, "
        "past-customer response %d-%d%%, unanswered-call callback %d-%d%%, "
        "average job value $%s, your close rate %d%%. "
        "We guarantee activated opportunities, not revenue - your team closes them."
    ) % (
        cfg["estimate_response_low"] * 100, cfg["estimate_response_high"] * 100,
        cfg["past_customer_response_low"] * 100, cfg["past_customer_response_high"] * 100,
        cfg["missed_call_recovery_low"] * 100, cfg["missed_call_recovery_high"] * 100,
        format(cfg["avg_job_value"], ","), cfg["close_rate"] * 100,
    )


def eligibility(past_customers: int, open_estimates_12mo: int) -> dict:
    """Conditions-precedent verdict: PASS / PRO-RATE / FAIL.

    PASS      both thresholds met -> full 20-25 guarantee
    PRO-RATE  at least half of each threshold -> guarantee pro-rated
    FAIL      below half on either -> not eligible (NOT ELIGIBLE on surfaces)
    """
    pc_ok = past_customers >= CONDITION_MIN_PAST_CUSTOMERS
    oe_ok = open_estimates_12mo >= CONDITION_MIN_OPEN_ESTIMATES
    if pc_ok and oe_ok:
        verdict, lo, hi = "PASS", GUARANTEE_MIN_OPPORTUNITIES, GUARANTEE_MAX_OPPORTUNITIES
    elif (past_customers >= CONDITION_MIN_PAST_CUSTOMERS // 2
          and open_estimates_12mo >= CONDITION_MIN_OPEN_ESTIMATES // 2):
        ratio = min(past_customers / CONDITION_MIN_PAST_CUSTOMERS,
                    open_estimates_12mo / CONDITION_MIN_OPEN_ESTIMATES)
        verdict = "PRO-RATE"
        lo = max(1, int(GUARANTEE_MIN_OPPORTUNITIES * ratio))
        hi = max(lo, int(GUARANTEE_MAX_OPPORTUNITIES * ratio))
    else:
        verdict, lo, hi = "FAIL", 0, 0
    return {
        "verdict": verdict,
        "past_customers": past_customers,
        "past_customers_required": CONDITION_MIN_PAST_CUSTOMERS,
        "open_estimates": open_estimates_12mo,
        "open_estimates_required": CONDITION_MIN_OPEN_ESTIMATES,
        "guaranteed_low": lo, "guaranteed_high": hi,
    }


def pool_projection(pool: str, count: int, total_value: float | None,
                    cfg: dict | None = None) -> dict:
    """Recoverable-opportunity range + estimated pipeline value for one pool."""
    cfg = {**DEFAULTS, **(cfg or {})}
    rates = {
        "open estimate": (cfg["estimate_response_low"], cfg["estimate_response_high"]),
        "past customer": (cfg["past_customer_response_low"], cfg["past_customer_response_high"]),
        "missed call": (cfg["missed_call_recovery_low"], cfg["missed_call_recovery_high"]),
    }
    lo_rate, hi_rate = rates[pool]
    opp_low, opp_high = int(count * lo_rate), max(int(count * lo_rate), int(count * hi_rate))
    if total_value is None:
        total_value = count * cfg["avg_job_value"]
    return {
        "pool": pool, "count": count,
        "opportunities_low": opp_low, "opportunities_high": opp_high,
        "pipeline_value": round(total_value, 2),
        "est_recoverable_value_low": round(total_value * lo_rate * cfg["close_rate"], 2),
        "est_recoverable_value_high": round(total_value * hi_rate * cfg["close_rate"], 2),
    }


def full_projection(pools: dict, past_customers: int, open_estimates_12mo: int,
                    cfg: dict | None = None) -> dict:
    """The complete picture both Snapshot and Audit render.

    pools: {"open estimate": {"count": n, "total_value": v|None},
            "past customer": {...}, "missed call": {...}}
    """
    cfg = {**DEFAULTS, **(cfg or {})}
    pool_results = [
        pool_projection(name, p.get("count", 0), p.get("total_value"), cfg)
        for name, p in pools.items()
    ]
    elig = eligibility(past_customers, open_estimates_12mo)
    return {
        "eligibility": elig,
        "pools": pool_results,
        "total_pipeline_value": round(sum(p["pipeline_value"] for p in pool_results), 2),
        "total_opportunities_low": sum(p["opportunities_low"] for p in pool_results),
        "total_opportunities_high": sum(p["opportunities_high"] for p in pool_results),
        "total_recoverable_low": round(sum(p["est_recoverable_value_low"] for p in pool_results), 2),
        "total_recoverable_high": round(sum(p["est_recoverable_value_high"] for p in pool_results), 2),
        "assumptions": assumptions_text(cfg),
        "config": cfg,
    }


def months_between(d1: date, d2: date) -> int:
    return (d2.year - d1.year) * 12 + (d2.month - d1.month)


def is_open_estimate_eligible(estimate_date: date, as_of: date) -> bool:
    """<= 12 months old per the conditions precedent."""
    return 0 <= months_between(estimate_date, as_of) <= OPEN_ESTIMATE_MAX_AGE_MONTHS


def guarantee_progress(ledger_rows: list, window_start: datetime,
                       as_of: datetime, guaranteed_low: int = GUARANTEE_MIN_OPPORTUNITIES,
                       guaranteed_high: int = GUARANTEE_MAX_OPPORTUNITIES) -> dict:
    """Scoreboard math from LEDGER rows (dicts with the A3 field names)."""
    activated = [r for r in ledger_rows if r.get("Response") and r.get("Qualified")]
    appointments = [r for r in ledger_rows if r.get("Appointment")]
    booked = [r for r in ledger_rows if r.get("Booked Job")]
    booked_value = sum(float(r.get("Job Value") or 0) for r in booked)
    day = max(0, (as_of - window_start).days)
    close_rate = (len(booked) / len(activated)) if activated else 0.0
    return {
        "day": day, "window_days": 30,
        "activated": len(activated),
        "guaranteed_low": guaranteed_low, "guaranteed_high": guaranteed_high,
        "on_pace": len(activated) >= (guaranteed_low * min(day, 30) / 30.0),
        "appointments": len(appointments),
        "booked_jobs": len(booked),
        "attributed_revenue": round(booked_value, 2),
        "client_close_rate": round(close_rate, 3),
        "by_pool": {
            pool: {
                "worked": len([r for r in ledger_rows if r.get("Pool") == pool]),
                "activated": len([r for r in activated if r.get("Pool") == pool]),
                "booked": len([r for r in booked if r.get("Pool") == pool]),
            } for pool in ("missed call", "open estimate", "past customer")
        },
    }
