"""C3 — The Job Pipeline Audit: CRM CSV in -> branded report out.

POST-access diagnostic, per the Notion template (Leak Report + Recovery
Audit Templates v1, Part 2): eligibility verdict first, three pools,
"the number" with assumptions printed, the 30-day plan, what we need.
Math through C1 only. Target: <= 2 hours from access (measured by the
harness against the A9 par).

CSV-first: heuristic column detection so any CRM export works; per-CRM
adapters come later.
"""
from __future__ import annotations

import csv
import html as html_mod
import re
from datetime import date, datetime
from pathlib import Path

from ..engine import pipeline_math
from ..renderer import link_tokens, render_service
from projections.empyrean.brand import page_shell

_COLUMN_PATTERNS = {
    "type": re.compile(r"type|category|record", re.I),
    "date": re.compile(r"date|created|when", re.I),
    "amount": re.compile(r"amount|value|price|total|estimate.?value", re.I),
    "status": re.compile(r"status|stage|outcome|disposition", re.I),
    "contact": re.compile(r"name|contact|customer", re.I),
    "phone": re.compile(r"phone|mobile|cell", re.I),
    "email": re.compile(r"e-?mail", re.I),
}

_TYPE_MAP = (
    (re.compile(r"estimate|quote|proposal|bid", re.I), "open estimate"),
    (re.compile(r"missed|abandoned|no.?answer|voicemail", re.I), "missed call"),
    (re.compile(r"customer|job|complete|closed|won|invoice", re.I), "past customer"),
)

_OPEN_STATUS = re.compile(r"open|pending|sent|follow|no.?response|unresolved|active", re.I)


def _detect_columns(header: list) -> dict:
    mapping = {}
    for role, pattern in _COLUMN_PATTERNS.items():
        for col in header:
            if pattern.search(col) and role not in mapping:
                mapping[role] = col
    return mapping


def _parse_date(raw: str) -> date | None:
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except (ValueError, AttributeError):
            continue
    return None


def _parse_amount(raw: str) -> float | None:
    try:
        return float(re.sub(r"[^0-9.]", "", raw or "")) or None
    except ValueError:
        return None


def classify_csv(csv_path: str, as_of: date | None = None) -> dict:
    """Parse a generic CRM export into the three pools. Deterministic spine."""
    as_of = as_of or date.today()
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        cols = _detect_columns(header)
        pools = {"open estimate": [], "past customer": [], "missed call": []}
        skipped = 0
        for row in reader:
            rtype = row.get(cols.get("type", ""), "")
            pool = None
            for pattern, name in _TYPE_MAP:
                if pattern.search(rtype or ""):
                    pool = name
                    break
            if pool is None:
                skipped += 1
                continue
            rec = {
                "contact": row.get(cols.get("contact", ""), ""),
                "date": _parse_date(row.get(cols.get("date", ""), "")),
                "amount": _parse_amount(row.get(cols.get("amount", ""), "")),
                "status": row.get(cols.get("status", ""), ""),
            }
            if pool == "open estimate":
                if rec["date"] and not pipeline_math.is_open_estimate_eligible(rec["date"], as_of):
                    continue  # older than 12 months — outside conditions precedent
                if rec["status"] and not _OPEN_STATUS.search(rec["status"]):
                    continue  # resolved estimate — not recoverable pool
            pools[pool].append(rec)
    return {"pools": pools, "columns": cols, "skipped": skipped, "as_of": as_of.isoformat()}


def build_audit(csv_path: str, company: str, cfg: dict | None = None,
                as_of: date | None = None) -> dict:
    """Classify + project. Same C1 engine the Snapshot uses."""
    classified = classify_csv(csv_path, as_of)
    p = classified["pools"]
    pool_input = {
        name: {
            "count": len(rows),
            "total_value": sum(r["amount"] for r in rows if r["amount"]) or None,
        } for name, rows in p.items()
    }
    projection = pipeline_math.full_projection(
        pool_input,
        past_customers=len(p["past customer"]),
        open_estimates_12mo=len(p["open estimate"]),
        cfg=cfg,
    )
    return {"company": company, "classified": classified, "projection": projection}


def render_audit(data: dict) -> str:
    """Branded 1-2 page report per the Notion audit template."""
    p = data["projection"]
    e = p["eligibility"]
    company = html_mod.escape(data["company"])
    verdict_class = {"PASS": "pass", "PRO-RATE": "prorate"}.get(e["verdict"], "fail")
    verdict_text = {"PASS": "PASS", "PRO-RATE": "PRO-RATE"}.get(e["verdict"], "NOT ELIGIBLE")
    pool_cards = "".join(
        """<div class="card"><h2 style="margin-top:0">%s</h2>
        <div>Records: <strong>%d</strong> &middot; Combined value: <strong>$%s</strong></div>
        <div class="muted" style="margin:6px 0">Conversations we expect to reopen: <strong>%d&ndash;%d</strong></div>
        <div class="bar"><span style="width:%d%%"></span></div></div>""" % (
            {"open estimate": "Pool 1 — Estimates waiting on an answer",
             "past customer": "Pool 2 — Past customers",
             "missed call": "Pool 3 — Calls that never got a call back"}[pr["pool"]],
            pr["count"], format(int(pr["pipeline_value"]), ","),
            pr["opportunities_low"], pr["opportunities_high"],
            min(100, int(100 * pr["pipeline_value"] / max(p["total_pipeline_value"], 1))),
        ) for pr in p["pools"]
    )
    body = """
    <div class="card">
      <h2 style="margin-top:0">1. Guarantee eligibility</h2>
      <table>
        <tr><th>Requirement</th><th>Yours</th><th>Status</th></tr>
        <tr><td>Reachable past customers &ge; %(pc_req)d</td><td>%(pc)d</td><td>%(pc_mark)s</td></tr>
        <tr><td>Open estimates &le; 12 months &ge; %(oe_req)d</td><td>%(oe)d</td><td>%(oe_mark)s</td></tr>
      </table>
      <div style="margin-top:10px">Guarantee status:
        <span class="verdict %(vclass)s">%(vtext)s</span>
        %(gline)s</div>
    </div>
    %(pool_cards)s
    <div class="card" style="text-align:center">
      <div class="muted">Total estimated pipeline waiting in your system</div>
      <div class="big-number">$%(total)s</div>
      <div>Homeowner conversations we expect to reopen in 30 days:
        <strong>%(opp_low)d&ndash;%(opp_high)d</strong></div>
      <div class="muted" style="font-size:13px;margin-top:6px">
        At your close rate, an estimated $%(rec_low)s&ndash;$%(rec_high)s in booked work.</div>
    </div>
    <h2>The 30-day plan</h2>
    <table>
      <tr><th>Week</th><th>What happens</th></tr>
      <tr><td>Days 1&ndash;2</td><td>You approve every message &middot; system goes live &middot; every unanswered call gets an immediate text back</td></tr>
      <tr><td>Week 1</td><td>Estimates &le; 90 days old get worked. First homeowner responses.</td></tr>
      <tr><td>Week 2</td><td>Older estimates &middot; re-quote offers where prices moved</td></tr>
      <tr><td>Week 3</td><td>Past customers &middot; oldest roofs first</td></tr>
      <tr><td>Week 4</td><td>Follow-up wave &middot; full scoreboard &middot; results review</td></tr>
    </table>
    <h2>What we need from you</h2>
    <p>Approvals within 48 hours &middot; about 10 minutes weekly &middot; your service
    area declared &middot; job types confirmed. <strong>Nothing else changes for your crew.</strong></p>
    <div class="footnote">%(assumptions)s</div>
    """ % {
        "pc_req": e["past_customers_required"], "pc": e["past_customers"],
        "pc_mark": "&#9989;" if e["past_customers"] >= e["past_customers_required"] else "&#9888;&#65039;",
        "oe_req": e["open_estimates_required"], "oe": e["open_estimates"],
        "oe_mark": "&#9989;" if e["open_estimates"] >= e["open_estimates_required"] else "&#9888;&#65039;",
        "vclass": verdict_class, "vtext": verdict_text,
        "gline": ("<span class='muted'>&middot; %d&ndash;%d booked-job opportunities guaranteed in 30 days</span>"
                  % (e["guaranteed_low"], e["guaranteed_high"])) if e["guaranteed_low"] else "",
        "pool_cards": pool_cards,
        "total": format(int(p["total_pipeline_value"]), ","),
        "opp_low": p["total_opportunities_low"], "opp_high": p["total_opportunities_high"],
        "rec_low": format(int(p["total_recoverable_low"]), ","),
        "rec_high": format(int(p["total_recoverable_high"]), ","),
        "assumptions": html_mod.escape(p["assumptions"]),
    }
    return page_shell("The Job Pipeline Audit", body,
                      subtitle="%s &middot; Confidential" % company)


render_service.register_template("audit", render_audit)


def generate(csv_path: str, company: str, record_ref: str,
             cfg: dict | None = None, as_of: date | None = None) -> dict:
    """Full C3 flow: classify -> project -> store -> mint -> render."""
    audit = build_audit(csv_path, company, cfg, as_of)
    render_service.put_record(record_ref, "audit", audit)
    token = link_tokens.mint(record_ref)
    html_path = render_service.render_for_token(token)
    return {
        "token": token,
        "html_path": str(html_path) if html_path else None,
        "eligibility": audit["projection"]["eligibility"],
        "totals": {
            "pipeline": audit["projection"]["total_pipeline_value"],
            "opportunities_low": audit["projection"]["total_opportunities_low"],
            "opportunities_high": audit["projection"]["total_opportunities_high"],
        },
    }
