"""C5 — Weekly Scoreboard: LEDGER rows -> branded proof.

The weekly proof ritual: guarantee progress vs 20-25 in the 30-day
window, per-pool breakdown, client close rate on our opportunities,
against par. Renders through C0; math through C1. Also drafts the
personalized report-video script (B7 output).
"""
from __future__ import annotations

import csv
import html as html_mod
from datetime import datetime

from ..engine import pipeline_math
from ..renderer import link_tokens, render_service
from projections.empyrean.brand import page_shell


def load_ledger_csv(path: str) -> list:
    """LEDGER-schema CSV (A3 field names as columns) -> row dicts."""
    rows = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            for flag in ("Response", "Qualified", "Appointment", "Booked Job"):
                row[flag] = str(row.get(flag, "")).strip().lower() in ("1", "true", "yes", "y")
            rows.append(row)
    return rows


def build_scoreboard(ledger_rows: list, company: str,
                     window_start: datetime, as_of: datetime,
                     guaranteed_low: int = 20, guaranteed_high: int = 25) -> dict:
    progress = pipeline_math.guarantee_progress(
        ledger_rows, window_start, as_of, guaranteed_low, guaranteed_high)
    return {"company": company, "progress": progress,
            "week_of": as_of.strftime("%B %d, %Y")}


def render_scoreboard(data: dict) -> str:
    g = data["progress"]
    company = html_mod.escape(data["company"])
    pct = min(100, int(100 * g["activated"] / max(g["guaranteed_low"], 1)))
    pool_rows = "".join(
        "<tr><td>%s</td><td>%d</td><td>%d</td><td>%d</td></tr>" % (
            {"missed call": "Calls answered for you",
             "open estimate": "Estimates reopened",
             "past customer": "Past customers reached"}[pool],
            v["worked"], v["activated"], v["booked"],
        ) for pool, v in g["by_pool"].items()
    )
    pace = ("On pace" if g["on_pace"] else "Behind pace — plan adjustment in motion")
    body = """
    <div class="card" style="text-align:center">
      <div class="muted">Day %(day)d of %(window)d &middot; booked-job opportunities opened</div>
      <div class="big-number">%(activated)d</div>
      <div class="muted">guarantee: %(glow)d&ndash;%(ghigh)d in 30 days &middot; %(pace)s</div>
      <div class="bar" style="margin-top:12px"><span style="width:%(pct)d%%"></span></div>
    </div>
    <div class="grid">
      <div class="card" style="text-align:center"><div class="muted">Appointments on your calendar</div>
        <div class="big-number" style="font-size:34px">%(appts)d</div></div>
      <div class="card" style="text-align:center"><div class="muted">Jobs booked</div>
        <div class="big-number" style="font-size:34px">%(booked)d</div></div>
      <div class="card" style="text-align:center"><div class="muted">Revenue on those jobs</div>
        <div class="big-number" style="font-size:34px">$%(revenue)s</div></div>
      <div class="card" style="text-align:center"><div class="muted">Your close rate on these conversations</div>
        <div class="big-number" style="font-size:34px">%(close)d%%</div></div>
    </div>
    <h2>Where this week's activity came from</h2>
    <table><tr><th>Source</th><th>Worked</th><th>Conversations opened</th><th>Jobs booked</th></tr>
    %(pool_rows)s</table>
    <div class="footnote">Every number above traces to a ledger entry with evidence.
    Dispute anything &mdash; we'll walk the record with you within 24 hours.</div>
    """ % {
        "day": g["day"], "window": g["window_days"], "activated": g["activated"],
        "glow": g["guaranteed_low"], "ghigh": g["guaranteed_high"],
        "pace": pace, "pct": pct, "appts": g["appointments"],
        "booked": g["booked_jobs"], "revenue": format(int(g["attributed_revenue"]), ","),
        "close": int(g["client_close_rate"] * 100), "pool_rows": pool_rows,
    }
    return page_shell("Weekly Scoreboard", body,
                      subtitle="%s &middot; week of %s" % (company, data["week_of"]))


render_service.register_template("scoreboard", render_scoreboard)


def video_script(data: dict) -> str:
    """B7 side-output: 45-second personalized report-video script draft."""
    g = data["progress"]
    return (
        "[Scoreboard on screen]\n"
        "Quick update for %s — day %d of your thirty.\n"
        "%d homeowner conversations are open, against the %d-to-%d we promised. "
        "%d appointments are on your calendar and %d jobs are booked — "
        "$%s in work, every dollar traceable in your ledger.\n"
        "This week: %s.\n"
        "Questions? Grab fifteen minutes on the link below — otherwise the "
        "next scoreboard lands this time next week."
    ) % (
        data["company"], g["day"], g["activated"],
        g["guaranteed_low"], g["guaranteed_high"],
        g["appointments"], g["booked_jobs"],
        format(int(g["attributed_revenue"]), ","),
        "estimates over ninety days old get re-quote offers" if g["day"] < 21
        else "past-customer outreach continues, oldest roofs first",
    )


def generate(ledger_csv: str, company: str, record_ref: str,
             window_start: datetime, as_of: datetime) -> dict:
    rows = load_ledger_csv(ledger_csv)
    board = build_scoreboard(rows, company, window_start, as_of)
    render_service.put_record(record_ref, "scoreboard", board)
    token = link_tokens.mint(record_ref)
    html_path = render_service.render_for_token(token)
    return {
        "token": token,
        "html_path": str(html_path) if html_path else None,
        "progress": board["progress"],
        "video_script": video_script(board),
    }
