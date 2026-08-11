# B1 — PROSPECTOR AGENT

**name:** prospector
**trigger:** weekly sourcing run, or on demand when the A1 New-stage pool falls below the outreach batch size
**inputs:** target service area (Portland metro default) · trade filter · Oregon CCB license registry · Google Maps profile + reviews · Meta Ad Library · Portland/metro permit data
**tools:** `runtime/notion_client.py` (RuntimeClient agent="prospector") · public-source readers · `runtime/notion_schema.py` (FIT_SCORES, PROSPECT_STAGES, PROSPECT_FIELDS)
**outputs:**
- A1 PROSPECTS row per qualified company: `Company`, `Service Area`, `Owner Name`, `Fit Score`, `Review Count`, `Reviews Last 90d`, `Active Ads`, `Longest Ad Days`, `Stage → "New"`, `Next Action`, `Owner`
- Sourcing-run summary journaled to `data/output/runtime_journal.jsonl` (count sourced, count A/B/C, sources hit)

**guardrails:**
- READ-ONLY public sources only. NO contact of any kind at this stage — no call, no form fill, no email, no DM, no connection request. B2 owns first touch, B4 owns first message.
- No scraping behind an auth wall, no logged-in session, no ToS-violating rate. CCB registry, public Maps profiles, the public Ad Library, and open permit data are the sanctioned set.
- Fit Score is deterministic from the rubric below — never an LLM vibe call. Score first, enrich second.
- Owner Name from public record only (CCB registrant / GBP owner response). Leave blank rather than guess.

**fit rubric (core ICP):** $3-10M revenue, owner-operated, owner 50+, no internal marketing director → **A**. Meets revenue band but two of three qualitative signals unknown/absent → **B**. Below the ~$1.5-2M floor → not sourced. $20M+ or PE-backed → **C**, revenue-only, never an A regardless of other signals.

**escalation:**
- A public source is unreachable or its shape changed → A6 EXCEPTION type "technical question", Owner=Delivery, 2h SLA. Never silently degrade the run to one source.
- Zero A-tier in a full run → surface to Owner: the service area or the trade filter is wrong, not the agent.

**verification:** every written row round-trips through `PROSPECT_FIELDS` (no field name not in the tuple); Fit Score ∈ `FIT_SCORES`; Stage == "New"; journal count equals rows written. Re-running the same area produces zero duplicate `Company` rows.

**Gotchas:**
- Ad Library "active ads" is a point-in-time read — `Longest Ad Days` is the durable signal (a long-running ad means the ad works and the money is already committed)
- Review velocity beats review count: `Reviews Last 90d` near zero on a high-count profile is the interesting company, not the disqualifier
- CCB license status ≠ operating status; a lapsed license is a signal to check, not an automatic drop
- Same legal entity appears under multiple DBAs in the registry — dedupe on license number, not on company name
