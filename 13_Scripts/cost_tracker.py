import os
import json
import datetime
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

VAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COST_LOG_FILE = os.path.join(VAULT, "13_Scripts/cost_log.json")

# Pricing constants (update if APIs change pricing)
PRICING = {
    "claude_haiku_input":   0.000001,    # $1 per 1M tokens
    "claude_haiku_output":  0.000005,    # $5 per 1M tokens
    "claude_sonnet_input":  0.000003,    # $3 per 1M tokens
    "claude_sonnet_output": 0.000015,    # $15 per 1M tokens
    "apify_per_result":     0.0000026,   # $2.60 per 1K results
    "gemini_flash_input":   0.0000003,   # $0.30 per 1M tokens
    "gemini_flash_output":  0.0000025,   # $2.50 per 1M tokens
}

_EMPTY_LOG = {
    "daily": {},
    "monthly": {},
    "all_time_total": 0.0,
}

_EMPTY_DAY = {
    "scraper": {
        "apify_results": 0,
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
    return {
        "scraper": dict(_EMPTY_DAY["scraper"]),
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
    """Return formatted cost report string."""
    s = get_cost_summary()
    return (
        f"COSTS\n"
        f"  Today scraper:   ${s['today_scraper']:.4f}\n"
        f"  Today co-pilot:  ${s['today_copilot']:.4f}\n"
        f"  Today total:     ${s['today_total']:.4f}\n"
        f"  This month:      ${s['month_total']:.2f}\n"
        f"  All time:        ${s['all_time_total']:.2f}"
    )
