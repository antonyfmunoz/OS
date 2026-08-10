"""C2 — Pipeline Snapshot: intake answers -> instant personalized estimate.

Self-serve, inbound, PRE-access — built from what the owner tells us plus
public signals. Renders through C0, math through C1 (never a second
formula). Writes the PROSPECTS row including the pre-qualification
eligibility verdict: the Snapshot is a qualification instrument, not a
lead magnet.

Client-facing copy: outcome language only (jobs, calendar, estimates,
homeowners, book). The one sanctioned lead-language use is the canonical
positioning sentence.
"""
from __future__ import annotations

import html as html_mod

from ..engine import pipeline_math
from ..renderer import link_tokens, render_service
from projections.empyrean.brand import page_shell

INTAKE_QUESTIONS = (
    ("company", "Company name"),
    ("service_area", "Primary service area (city / county)"),
    ("estimates_12mo", "Estimates sent in the last 12 months (count)"),
    ("estimates_open", "Of those, roughly how many never became a yes or a no?"),
    ("past_customers", "Past customers you could still reach (count)"),
    ("missed_calls_month", "Calls that ring out or hit voicemail in a typical month"),
    ("avg_job_value", "Average job value (dollars)"),
    ("close_rate_pct", "Of the estimates you sit down for, what percent do you win?"),
)


def build_snapshot(answers: dict) -> dict:
    """Compute the Snapshot from intake answers via C1. Pure function."""
    cfg = {}
    if answers.get("avg_job_value"):
        cfg["avg_job_value"] = float(answers["avg_job_value"])
    if answers.get("close_rate_pct"):
        cfg["close_rate"] = float(answers["close_rate_pct"]) / 100.0
    pools = {
        "open estimate": {"count": int(answers.get("estimates_open", 0)),
                          "total_value": None},
        "past customer": {"count": int(answers.get("past_customers", 0)),
                          "total_value": None},
        "missed call": {"count": int(answers.get("missed_calls_month", 0)),
                        "total_value": None},
    }
    projection = pipeline_math.full_projection(
        pools,
        past_customers=int(answers.get("past_customers", 0)),
        open_estimates_12mo=int(answers.get("estimates_open", 0)),
        cfg=cfg,
    )
    return {"answers": answers, "projection": projection}


def prospects_row(snapshot: dict) -> dict:
    """The A1 PROSPECTS row this Snapshot writes — verdict included."""
    a, p = snapshot["answers"], snapshot["projection"]
    return {
        "Company": a.get("company", "unknown"),
        "Service Area": a.get("service_area", ""),
        "Pipeline Estimate": p["total_pipeline_value"],
        "Eligibility Verdict": p["eligibility"]["verdict"],
        "Stage": "Snapshot Sent",
        "Next Action": "instant alert -> respond inside 5 minutes",
    }


def render_snapshot(data: dict) -> str:
    """Branded one-pager. data = build_snapshot() output."""
    a, p = data["answers"], data["projection"]
    e = p["eligibility"]
    company = html_mod.escape(str(a.get("company", "Your company")))
    verdict_class = {"PASS": "pass", "PRO-RATE": "prorate"}.get(e["verdict"], "fail")
    verdict_label = {"PASS": "QUALIFIED", "PRO-RATE": "PARTIALLY QUALIFIED"}.get(
        e["verdict"], "NOT YET QUALIFIED")
    pool_rows = "".join(
        "<tr><td>%s</td><td>%d</td><td>%d&ndash;%d</td><td>$%s</td></tr>" % (
            {"open estimate": "Estimates still waiting on an answer",
             "past customer": "Past customers you could book again",
             "missed call": "Calls that never got a call back"}[pr["pool"]],
            pr["count"], pr["opportunities_low"], pr["opportunities_high"],
            format(int(pr["pipeline_value"]), ","),
        ) for pr in p["pools"]
    )
    body = """
    <div class="card">
      <div class="muted" style="font-size:13px">Based on what you told us, work you already paid for is sitting in three places:</div>
      <table><tr><th>Where the jobs are</th><th>Count</th><th>Conversations we'd expect to reopen</th><th>Estimated value</th></tr>%(pool_rows)s</table>
    </div>
    <div class="card" style="text-align:center">
      <div class="muted">Estimated jobs waiting in your pipeline</div>
      <div class="big-number">$%(total)s</div>
      <div class="muted" style="font-size:13px">%(opp_low)d&ndash;%(opp_high)d homeowner conversations we'd expect to reopen in 30 days</div>
    </div>
    <div class="card">
      <h2 style="margin-top:0">Do you qualify for the booked-jobs guarantee?</h2>
      <span class="verdict %(vclass)s">%(vlabel)s</span>
      <table>
        <tr><th>Requirement</th><th>Yours</th></tr>
        <tr><td>Reachable past customers &ge; %(pc_req)d</td><td>%(pc)d</td></tr>
        <tr><td>Estimates &le; 12 months old &ge; %(oe_req)d</td><td>%(oe)d</td></tr>
      </table>
    </div>
    <p style="margin:20px 0">This is what we can see from the outside. With read-only access
    to your system, we replace every assumption with your actual numbers &mdash; free,
    within 48 hours, and you keep the report either way.</p>
    <p><a class="cta" href="#book">See your real number</a></p>
    <div class="footnote">%(assumptions)s<br><br>
    <strong>Our promise on your data:</strong> access is read-only and technically enforced.
    Your information is used solely to prepare your report. If we don't work together,
    it is deleted within 7 days &mdash; with written confirmation. A standing NDA is
    available before you share anything.</div>
    """ % {
        "pool_rows": pool_rows,
        "total": format(int(p["total_pipeline_value"]), ","),
        "opp_low": p["total_opportunities_low"], "opp_high": p["total_opportunities_high"],
        "vclass": verdict_class, "vlabel": verdict_label,
        "pc_req": e["past_customers_required"], "pc": e["past_customers"],
        "oe_req": e["open_estimates_required"], "oe": e["open_estimates"],
        "assumptions": html_mod.escape(p["assumptions"]),
    }
    return page_shell("Pipeline Snapshot", body,
                      subtitle="Prepared for %s" % company)


render_service.register_template("snapshot", render_snapshot)


def generate(answers: dict, record_ref: str) -> dict:
    """Full C2 flow: compute -> store record -> mint link -> render.

    Returns {token, html_path, prospects_row, alert}.
    The alert is journal-only in TEST MODE (no real notification).
    """
    snap = build_snapshot(answers)
    render_service.put_record(record_ref, "snapshot", snap)
    token = link_tokens.mint(record_ref)
    html_path = render_service.render_for_token(token)
    return {
        "token": token,
        "html_path": str(html_path) if html_path else None,
        "prospects_row": prospects_row(snap),
        "alert": {"type": "inbound_snapshot", "record_ref": record_ref,
                  "respond_within_minutes": 5, "simulated": True},
    }
