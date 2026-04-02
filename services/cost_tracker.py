import os
import json
import datetime
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

VAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COST_LOG_FILE = os.path.join(VAULT, "services/cost_log.json")

# Pricing constants (update if APIs change pricing)
PRICING = {
    "claude_haiku_input":   0.000001,    # $1 per 1M tokens
    "claude_haiku_output":  0.000005,    # $5 per 1M tokens
    "claude_sonnet_input":  0.000003,    # $3 per 1M tokens
    "claude_sonnet_output": 0.000015,    # $15 per 1M tokens
    "apify_per_result":     0.0000026,   # $2.60 per 1K results
    "apify_hashtag_run":    0.015,       # ~$0.015 per hashtag scrape run
    "apify_comment_run":    0.025,       # ~$0.025 per comment scrape run
    "apify_profile_run":    0.005,       # ~$0.005 per profile scrape run
    "gemini_flash_input":   0.0000003,   # $0.30 per 1M tokens
    "gemini_flash_output":  0.0000025,   # $2.50 per 1M tokens
}

_EMPTY_LOG = {
    "daily": {},
    "monthly": {},
    "all_time_total": 0.0,
    "apify": {
        "total_hashtag_runs": 0,
        "total_comment_runs": 0,
        "total_profile_runs": 0,
        "total_gross_cost": 0.0,
        "total_billable_cost": 0.0,
        "free_tier_limit": 5.00,
    }
}

_EMPTY_DAY = {
    "scraper": {
        "apify_results": 0,
        "apify_runs": {
            "hashtag": 0,
            "comment": 0,
            "profile": 0
        },
        "apify_cost": 0.0,
        "haiku_calls": 0,
        "haiku_input_tokens": 0,
        "haiku_output_tokens": 0,
        "haiku_cost": 0.0,
        "total": 0.0,
    },
    "copilot": {
        "sonnet_calls": 0,
        "sonnet_input_tokens": 0,
        "sonnet_output_tokens": 0,
        "sonnet_cost": 0.0,
        "total": 0.0,
    },
    "total_day": 0.0,
}


def _deep_copy_empty_day():
    scraper = dict(_EMPTY_DAY["scraper"])
    scraper["apify_runs"] = dict(_EMPTY_DAY["scraper"]["apify_runs"])
    return {
        "scraper": scraper,
        "copilot": dict(_EMPTY_DAY["copilot"]),
        "total_day": 0.0,
    }


def load_log():
    """Read COST_LOG_FILE, return dict. Returns empty structure if file doesn't exist."""
    if not os.path.exists(COST_LOG_FILE):
        return {
            "daily": {},
            "monthly": {},
            "all_time_total": 0.0,
        }
    try:
        with open(COST_LOG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "daily": {},
            "monthly": {},
            "all_time_total": 0.0,
        }


def save_log(log):
    """Write to COST_LOG_FILE with indent=2."""
    os.makedirs(os.path.dirname(COST_LOG_FILE), exist_ok=True)
    with open(COST_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)


def _today_key():
    return datetime.date.today().isoformat()


def _month_key():
    return datetime.date.today().strftime("%Y-%m")


def sync_apify_balance():
    """Fetch actual Apify account usage via monthly endpoint."""
    token = os.getenv("APIFY_API_TOKEN")
    if not token:
        return None
    try:
        import requests as req
        resp = req.get(
            f"https://api.apify.com/v2/users/me"
            f"/usage/monthly?token={token}",
            timeout=10
        )
        data = resp.json().get("data", {})

        # Real total spend this billing cycle
        total_spend = data.get(
            "totalUsageCreditsUsdAfterVolumeDiscount",
            None)

        if total_spend is None:
            return None

        # Also extract daily breakdown for logging
        daily = data.get("dailyServiceUsages", [])
        daily_breakdown = {
            d["date"][:10]: d["totalUsageCreditsUsd"]
            for d in daily
        }

        return {
            "total_spend": total_spend,
            "daily": daily_breakdown,
            "cycle_start": data.get(
                "usageCycle", {}).get("startAt", ""),
            "cycle_end": data.get(
                "usageCycle", {}).get("endAt", "")
        }
    except Exception as e:
        print(f"Could not sync Apify balance: {e}")
        return None


def sync_and_update_apify_log():
    """Sync real Apify usage from API and update log.
    Call anytime — not just during scraper runs."""
    sync = sync_apify_balance()
    if not sync:
        return

    log = load_log()
    if "apify" not in log:
        log["apify"] = {
            "total_hashtag_runs": 0,
            "total_comment_runs": 0,
            "total_profile_runs": 0,
            "total_gross_cost": 0.0,
            "total_billable_cost": 0.0,
            "free_tier_limit": 5.00,
            "last_synced": ""
        }

    total_spend = sync["total_spend"]
    log["apify"]["total_gross_cost"] = total_spend
    log["apify"]["total_billable_cost"] = total_spend
    log["apify"]["is_paid"] = True
    log["apify"]["cycle_start"] = sync.get(
        "cycle_start", "")
    log["apify"]["cycle_end"] = sync.get(
        "cycle_end", "")
    log["apify"]["last_synced"] = (
        datetime.date.today().isoformat())

    save_log(log)
    print(f"Apify synced: ${total_spend:.4f} total")


def log_apify_runs(hashtag_runs, comment_runs,
                   profile_runs):
    """Track actual Apify actor runs with free tier calculation.
    Syncs from Apify API every call for real billing data."""
    gross_cost = (
        hashtag_runs * PRICING["apify_hashtag_run"] +
        comment_runs * PRICING["apify_comment_run"] +
        profile_runs * PRICING["apify_profile_run"]
    )

    log = load_log()

    if "apify" not in log or not log["apify"]:
        log["apify"] = {
            "total_hashtag_runs": 0,
            "total_comment_runs": 0,
            "total_profile_runs": 0,
            "total_gross_cost": 0.0,
            "total_billable_cost": 0.0,
            "free_tier_limit": 5.00,
        }
        # Seed from real Apify data on first init
        sync = sync_apify_balance()
        if sync is not None:
            total_spend = sync["total_spend"]
            log["apify"]["total_gross_cost"] = total_spend
            log["apify"]["total_billable_cost"] = total_spend
            log["apify"]["cycle_start"] = sync["cycle_start"]
            log["apify"]["cycle_end"] = sync["cycle_end"]
            log["apify"]["last_synced"] = (
                datetime.date.today().isoformat())
            print(f"Apify sync: ${total_spend:.4f} total spend this cycle")

    # Sync live values from Apify API every run
    sync = sync_apify_balance()
    if sync and "apify" in log:
        total_spend = sync["total_spend"]
        log["apify"]["total_gross_cost"] = total_spend
        log["apify"]["total_billable_cost"] = total_spend
        log["apify"]["last_synced"] = (
            datetime.date.today().isoformat())
        log["apify"]["cycle_start"] = sync["cycle_start"]
        log["apify"]["cycle_end"] = sync["cycle_end"]

    apify = log["apify"]

    # Accumulate run counts
    apify["total_hashtag_runs"] += hashtag_runs
    apify["total_comment_runs"] += comment_runs
    apify["total_profile_runs"] += profile_runs

    # Billable from API-synced data (already set above)
    billable = apify["total_billable_cost"]

    # Update daily/monthly totals with billable only
    today = _today_key()
    month = _month_key()

    if today not in log["daily"]:
        log["daily"][today] = _deep_copy_empty_day()

    s = log["daily"][today]["scraper"]
    if "apify_runs" not in s:
        s["apify_runs"] = {"hashtag": 0, "comment": 0, "profile": 0}
    s["apify_runs"]["hashtag"] += hashtag_runs
    s["apify_runs"]["comment"] += comment_runs
    s["apify_runs"]["profile"] += profile_runs
    s["apify_cost"] = apify["total_billable_cost"]
    s["total"] = s["apify_cost"] + s.get("haiku_cost", 0.0)
    log["daily"][today]["total_day"] = (
        s["total"] +
        log["daily"][today]["copilot"].get("total", 0.0)
    )

    if month not in log["monthly"]:
        log["monthly"][month] = 0.0
    log["monthly"][month] = (
        log["monthly"].get(month, 0.0) -
        log["daily"][today].get("_prev_apify_billable", 0.0) +
        apify["total_billable_cost"])
    log["daily"][today]["_prev_apify_billable"] = (
        apify["total_billable_cost"])

    save_log(log)

    print(f"Apify runs: hashtag={hashtag_runs} comment={comment_runs} profile={profile_runs}")
    print(f"Gross cost: ${gross_cost:.4f}")
    print(f"Billable (from API): ${billable:.4f}")

    return billable


def log_scraper_costs(apify_results, haiku_calls,
                      haiku_input_tokens, haiku_output_tokens):
    """Calculate scraper costs, update log, save, and return total cost for this run."""
    apify_cost = apify_results * PRICING["apify_per_result"]
    haiku_cost = (
        haiku_input_tokens * PRICING["claude_haiku_input"]
        + haiku_output_tokens * PRICING["claude_haiku_output"]
    )
    run_total = apify_cost + haiku_cost

    log = load_log()
    today = _today_key()
    month = _month_key()

    if today not in log["daily"]:
        log["daily"][today] = _deep_copy_empty_day()

    s = log["daily"][today]["scraper"]
    s["apify_results"] += apify_results
    s["apify_cost"] += apify_cost
    s["haiku_calls"] += haiku_calls
    s["haiku_input_tokens"] += haiku_input_tokens
    s["haiku_output_tokens"] += haiku_output_tokens
    s["haiku_cost"] += haiku_cost
    s["total"] += run_total

    log["daily"][today]["total_day"] = (
        log["daily"][today]["scraper"]["total"]
        + log["daily"][today]["copilot"]["total"]
    )

    log["monthly"][month] = log["monthly"].get(month, 0.0) + run_total
    log["all_time_total"] = log.get("all_time_total", 0.0) + run_total

    save_log(log)
    return run_total


def log_copilot_costs(sonnet_calls, sonnet_input_tokens, sonnet_output_tokens):
    """Calculate copilot costs, update log, save, and return total cost for this call."""
    sonnet_cost = (
        sonnet_input_tokens * PRICING["claude_sonnet_input"]
        + sonnet_output_tokens * PRICING["claude_sonnet_output"]
    )
    run_total = sonnet_cost

    log = load_log()
    today = _today_key()
    month = _month_key()

    if today not in log["daily"]:
        log["daily"][today] = _deep_copy_empty_day()

    c = log["daily"][today]["copilot"]
    c["sonnet_calls"] += sonnet_calls
    c["sonnet_input_tokens"] += sonnet_input_tokens
    c["sonnet_output_tokens"] += sonnet_output_tokens
    c["sonnet_cost"] += sonnet_cost
    c["total"] += run_total

    log["daily"][today]["total_day"] = (
        log["daily"][today]["scraper"]["total"]
        + log["daily"][today]["copilot"]["total"]
    )

    log["monthly"][month] = log["monthly"].get(month, 0.0) + run_total
    log["all_time_total"] = log.get("all_time_total", 0.0) + run_total

    save_log(log)
    return run_total


def get_today_costs():
    """Return today's full cost entry. Returns zeroed structure if no entry."""
    log = load_log()
    today = _today_key()
    return log["daily"].get(today, _deep_copy_empty_day())


def get_monthly_costs(month_str=None):
    """Return monthly total. month_str format: '2026-03'. Defaults to current month."""
    if month_str is None:
        month_str = _month_key()
    log = load_log()
    return log["monthly"].get(month_str, 0.0)


def get_all_time_total():
    """Return all_time_total float."""
    log = load_log()
    return log.get("all_time_total", 0.0)


def get_cost_summary():
    """Return dict with today and cumulative cost totals."""
    today_entry = get_today_costs()
    today_scraper = today_entry["scraper"]["total"]
    today_copilot = today_entry["copilot"]["total"]
    return {
        "today_scraper": today_scraper,
        "today_copilot": today_copilot,
        "today_total": today_entry["total_day"],
        "month_total": get_monthly_costs(),
        "all_time_total": get_all_time_total(),
    }


def format_cost_report():
    """Return formatted cost report string with Apify details."""
    costs = get_today_costs()
    month = get_monthly_costs()
    all_time = get_all_time_total()

    log = load_log()
    apify = log.get("apify", {})

    total_gross = apify.get("total_gross_cost", 0.0)
    total_billable = apify.get("total_billable_cost", 0.0)
    total_runs = (
        apify.get("total_hashtag_runs", 0) +
        apify.get("total_comment_runs", 0) +
        apify.get("total_profile_runs", 0)
    )

    return (
        f"COSTS\n"
        f"  Today scraper:   ${costs['scraper']['total']:.4f}\n"
        f"  Today co-pilot:  ${costs['copilot']['total']:.4f}\n"
        f"  Today total:     ${costs['total_day']:.4f}\n"
        f"  This month:      ${month:.2f}\n"
        f"  All time:        ${all_time:.2f}\n\n"
        f"APIFY (cycle: {apify.get('cycle_start','')[:10]}"
        f" -> {apify.get('cycle_end','')[:10]})\n"
        f"  Total runs:      {total_runs}\n"
        f"  This cycle:      ${total_gross:.4f}\n"
        f"  Billed to card:  ${total_billable:.4f}\n"
        f"  Last synced:     {apify.get('last_synced', 'never')}"
    )
