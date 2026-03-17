import os
import json
import datetime
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kpi_history_log.json")


def load_log():
    if not os.path.exists(LOG_FILE):
        return {"daily": {}, "weekly": {}}
    try:
        with open(LOG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"daily": {}, "weekly": {}}


def save_log(log):
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)


def update_daily(date, data):
    """Merge data dict into the daily entry for date."""
    log = load_log()
    existing = log["daily"].get(date, {})
    existing.update(data)
    log["daily"][date] = existing
    save_log(log)


def store_weekly_rollup():
    log = load_log()
    daily = log.get("daily", {})
    if len(daily) < 7:
        return

    today = datetime.date.today().isoformat()
    last_7 = sorted(daily.keys())[-7:]

    total_dms = sum(daily[d].get("dms_sent", 0) for d in last_7)
    total_replies = sum(daily[d].get("replies_received", 0) for d in last_7)
    total_cost = sum(daily[d].get("api_cost", 0.0) for d in last_7)
    total_qualified = sum(daily[d].get("leads_qualified", 0) for d in last_7)

    rates = [daily[d].get("reply_rate", 0) for d in last_7
             if daily[d].get("dms_sent", 0) > 0]
    avg_rate = round(sum(rates) / len(rates), 1) if rates else 0

    best_day = max(last_7, key=lambda d: daily[d].get("reply_rate", 0))

    best_hashtag = "none"
    try:
        config_path = os.path.join(os.path.dirname(__file__), "hashtag_config.json")
        with open(config_path) as f:
            config = json.load(f)
        perf = config.get("performance", {})
        if perf:
            best_hashtag = max(
                perf.items(),
                key=lambda x: x[1].get("reply_rate", 0)
            )[0]
    except Exception:
        pass

    best_opener = "none"
    try:
        opener_path = os.path.join(os.path.dirname(__file__), "opener_stats.json")
        with open(opener_path) as f:
            openers = json.load(f).get("openers", {})
        if openers:
            best_opener = max(
                openers.items(),
                key=lambda x: x[1].get("reply_rate", 0)
            )[0]
    except Exception:
        pass

    weekly_data = {
        "week_ending": today,
        "total_dms_sent": total_dms,
        "total_replies": total_replies,
        "avg_reply_rate": avg_rate,
        "total_qualified": total_qualified,
        "total_api_cost": round(total_cost, 4),
        "best_day": best_day,
        "best_hashtag": best_hashtag,
        "best_opener": best_opener[:50] if best_opener else "none",
    }

    log.setdefault("weekly", {})[today] = weekly_data
    save_log(log)

    check_improvement_triggers(weekly_data)


def check_improvement_triggers(weekly_data):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return

    def ping(text):
        try:
            import requests as req
            req.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": text},
                timeout=10
            )
        except Exception:
            pass

    rate = weekly_data.get("avg_reply_rate", 0)
    dms = weekly_data.get("total_dms_sent", 0)

    if rate < 10 and dms > 50:
        ping(
            f"PERFORMANCE ALERT\n\n"
            f"Weekly reply rate: {rate}%\n"
            f"Target: 10%+\n\n"
            f"Suggestions:\n"
            f"- Review openers (/hashtags)\n"
            f"- Check hashtag performance\n"
            f"- Consider refreshing DM copy"
        )

    if rate >= 20 and dms >= 300:
        ping(
            f"STRONG WEEK\n\n"
            f"DMs sent: {dms}\n"
            f"Reply rate: {rate}%\n\n"
            f"System is performing well.\n"
            f"Keep the outreach consistent."
        )


def get_weekly_summary():
    log = load_log()
    weekly = log.get("weekly", {})
    if not weekly:
        return None
    latest_week = sorted(weekly.keys())[-1]
    w = weekly[latest_week]
    opener = w.get("best_opener", "N/A")
    opener_preview = (opener[:40] + "...") if len(opener) > 40 else opener
    return (
        f"WEEKLY SUMMARY ({latest_week})\n\n"
        f"DMs sent:      {w.get('total_dms_sent', 0)}\n"
        f"Replies:       {w.get('total_replies', 0)}\n"
        f"Reply rate:    {w.get('avg_reply_rate', 0)}%\n"
        f"Leads scraped: {w.get('total_qualified', 0)}\n"
        f"API cost:      ${w.get('total_api_cost', 0):.2f}\n\n"
        f"Best day:      {w.get('best_day', 'N/A')}\n"
        f"Best source:   {w.get('best_hashtag', 'N/A')}\n"
        f"Best opener:   {opener_preview}"
    )
