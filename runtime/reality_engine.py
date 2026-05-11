"""
RealityIntelligenceEngine — continuous market intelligence layer.

Scans for signals across ventures, classifies by priority tier, and routes
through the event bus in real time. Runs every 6 hours during waking hours
(6am, 12pm, 6pm) as a scheduled job wired into the orchestrator and Telegram bot.

Signal Tiers:
  CRITICAL   — direct competitive threat, platform change, market disruption
  HIGH       — new competitor, ICP shift, unexpected performance signal
  NORMAL     — routine market data, trend signals, daily briefing material
  BACKGROUND — low-confidence signals, noise, tangential mentions

Usage:
    from runtime.context import load_context_from_env
    from runtime.reality_engine import RealityIntelligenceEngine

    ctx = load_context_from_env()
    rie = RealityIntelligenceEngine(ctx)

    signals = rie.scan_market_signals('lyfe_institute')
    summary = rie.process_signal_queue()
    report  = rie.generate_truth_report('lyfe_institute')
"""

import datetime
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

load_dotenv(Path(__file__).parent / ".env")
load_dotenv(Path(_REPO_ROOT) / "services" / ".env")

from runtime.context import EOSContext
from runtime.cognitive_loop import CognitiveLoop
from runtime.event_bus import EventBus
from runtime.agent_runtime import TaskType
from runtime.venture_knowledge import VentureKnowledgeBase
from runtime.strategy_engine import StrategyEngine, _parse_labeled_sections
from runtime.memory import AgentMemory


SIGNAL_TIERS = ("CRITICAL", "HIGH", "NORMAL", "BACKGROUND")

# Keywords that escalate a signal to CRITICAL tier
_CRITICAL_KEYWORDS = [
    "targeting your offer",
    "directly competes",
    "platform ban",
    "policy change",
    "algorithm update",
    "market disruption",
    "shutting down",
    "regulatory",
    "terms of service violation",
    "banning accounts",
    "content removal",
    "account suspension",
]

# Keywords that escalate to HIGH tier
_HIGH_KEYWORDS = [
    "new competitor",
    "new entrant",
    "market entry",
    "icp shift",
    "language shift",
    "unexpected",
    "viral",
    "breakthrough",
    "gen z",
    "shifting psychology",
    "new offer launched",
]


def _notify(text: str) -> None:
    """Send notification via channel router."""
    try:
        from runtime.channel import get_channel_router

        router = get_channel_router()
        router.notify(text)
    except Exception as e:
        print(f"[RealityEngine] Notify failed: {e}")


class RealityIntelligenceEngine:
    """
    Continuously running intelligence layer. Detects market signals,
    classifies by priority tier, and routes through the event bus.

    Reasons from known venture data — real web scraping replaces the
    simulation layer when browser tools are wired in.
    """

    def __init__(self, ctx: EOSContext):
        self.ctx = ctx
        self.loop = CognitiveLoop(ctx)
        self.event_bus = EventBus()
        self.memory = AgentMemory()

    # ─── scan_market_signals ─────────────────────────────────────────────────

    @staticmethod
    def _venture_scan_ready(venture_id: str) -> bool:
        """Return True if the venture has enough real data to ground a scan.

        A venture is NOT ready when its ICP, competitors, AND content angles
        are all TODO placeholders — scanning would produce fabricated signals.
        """
        try:
            v = VentureKnowledgeBase.get(venture_id)
        except Exception:
            return False

        icp_empty = (
            v.primary_icp.strip().startswith("TODO") or not v.primary_icp.strip()
        )
        comps_empty = (
            all(c.strip().startswith("TODO") for c in v.competitors)
            if v.competitors
            else True
        )
        angles_empty = (
            all(a.strip().startswith("TODO") for a in v.winning_content_angles)
            if v.winning_content_angles
            else True
        )

        # Need at least ONE real data source to ground signals
        return not (icp_empty and comps_empty and angles_empty)

    def scan_market_signals(self, venture_id: str) -> list[dict]:
        """
        Scan market signals using live web data via ScraplingConnector,
        augmented by venture context reasoning.

        Returns list of dicts: {signal_type, content, confidence, source, tier}.
        Skips ventures with insufficient data (all TODOs) to avoid fabrication.
        """
        # Guard: skip ventures with no real ICP/competitor/content data
        if not self._venture_scan_ready(venture_id):
            print(
                f"[RealityEngine] {venture_id}: skipped — insufficient data (all TODOs)"
            )
            return []

        from runtime.scrapling_connector import ScraplingConnector

        venture_ctx = VentureKnowledgeBase.to_agent_context(venture_id, detail="full")

        # Live scrape competitor pages to ground the scan in real data
        sc = ScraplingConnector()
        live_intel: list[str] = []

        try:
            v = VentureKnowledgeBase.get(venture_id)
            competitors = [c for c in v.competitors if not c.startswith("TODO")]
            for comp in competitors[:3]:
                # Try to extract a URL if the competitor string contains one
                import re as _re

                url_match = _re.search(r"https?://\S+", comp)
                if url_match:
                    result = sc.fetch(url_match.group(0), stealth=True)
                    if result["status"] == "ok" and result["text"]:
                        live_intel.append(
                            f"LIVE — {result['title']} ({result['url']}):\n"
                            f"{result['text'][:800]}"
                        )
        except Exception as e:
            print(f"[RealityEngine] Scrapling scrape failed (non-blocking): {e}")

        live_section = ""
        if live_intel:
            live_section = (
                "\n\nLIVE WEB INTELLIGENCE (scraped right now):\n"
                + "\n\n".join(live_intel)
                + "\n\nUse this live data to make your signals more specific and current."
            )

        # Build venture-specific signal type descriptions from real data
        v = VentureKnowledgeBase.get(venture_id)
        real_competitors = [
            c for c in v.competitors if not c.strip().startswith("TODO")
        ]
        comp_names = (
            ", ".join(real_competitors[:5])
            if real_competitors
            else "competitors in this space"
        )

        prompt = (
            "You are a market intelligence analyst conducting a real-time scan. "
            "Using the venture context below, reason from first principles about "
            "the current market landscape for this specific offer and market segment. "
            "Generate specific, plausible market signals that a founder in this exact "
            "position needs to know right now.\n\n"
            "VENTURE CONTEXT:\n"
            f"{venture_ctx}"
            f"{live_section}\n\n"
            "Generate exactly 6 market intelligence signals. Each must be grounded "
            "in the specific context above — not generic. Reference actual competitors, "
            "platforms, ICP language, and offer mechanics from the data.\n\n"
            "For each signal, output on a new line in this exact format:\n"
            "SIGNAL: <signal_type> | <specific intelligence content> | "
            "<confidence: HIGH/MEDIUM/LOW> | <source: competitor_analysis/"
            "platform_monitor/icp_listening/trend_scan>\n\n"
            "Cover these signal types:\n"
            f"- COMPETITOR: What are the known competitors ({comp_names}) doing right now? "
            "  Any new moves, price changes, or positioning shifts?\n"
            "- PLATFORM: Any platform policy or algorithm changes affecting "
            "  the channels this venture uses for outreach or delivery?\n"
            "- ICP_SHIFT: Is the target customer's language or psychology shifting? "
            "  Any new dominant frustrations or desires emerging in this market?\n"
            "- MARKET_ENTRY: Are new players entering this venture's specific market space?\n"
            "- CONTENT: What content angles are gaining unexpected traction "
            "  in this venture's market right now?\n"
            f"- BLOCKER: What external market condition is most blocking revenue "
            f"  for this specific offer at {v.price_point or 'its current price point'} right now?\n\n"
            "Be specific. Every signal must reference details from the venture context."
        )

        result = self.loop.run(
            input=prompt,
            agent="reality_engine.scan",
            task_type=TaskType.ANALYZE,
            venture_id=venture_id,
            max_iterations=1,
        )

        signals: list[dict] = []
        if result.output:
            for line in result.output.splitlines():
                line = line.strip()
                if not line.startswith("SIGNAL:"):
                    continue
                parts = [p.strip() for p in line[len("SIGNAL:") :].split("|")]
                if len(parts) < 4:
                    continue

                signal_type = parts[0].upper()
                content = parts[1]
                raw_conf = parts[2].upper()
                confidence = (
                    raw_conf if raw_conf in ("HIGH", "MEDIUM", "LOW") else "MEDIUM"
                )
                source = parts[3]

                raw_signal = {
                    "signal_type": signal_type,
                    "content": content,
                    "confidence": confidence,
                    "source": source,
                }
                tier = self.classify_signal(raw_signal)

                signals.append(
                    {
                        **raw_signal,
                        "tier": tier,
                        "venture_id": venture_id,
                        "scanned_at": datetime.datetime.now(
                            datetime.timezone.utc
                        ).isoformat(),
                    }
                )

        print(f"[RealityEngine] {venture_id}: {len(signals)} signals scanned")
        return signals

    # ─── classify_signal ─────────────────────────────────────────────────────

    def classify_signal(self, signal: dict) -> str:
        """
        Classify signal into CRITICAL / HIGH / NORMAL / BACKGROUND.

        Rules-based — fast, no LLM call. Tier logic:
          CRITICAL  — platform policy change, direct competitive threat, market disruption
          HIGH      — new competitor, ICP language shift, unexpected content performance
          NORMAL    — routine trend data, known competitor monitoring
          BACKGROUND — low-confidence signals
        """
        signal_type = (signal.get("signal_type") or "").upper()
        confidence = (signal.get("confidence") or "").upper()
        content = (signal.get("content") or "").lower()

        # CRITICAL: any platform policy signal at high/medium confidence,
        # or content mentioning disruptive keywords
        if signal_type == "PLATFORM" and confidence in ("HIGH", "MEDIUM"):
            return "CRITICAL"

        if any(kw in content for kw in _CRITICAL_KEYWORDS):
            return "CRITICAL"

        # HIGH: new entrants, ICP shifts, or competitor signals at solid confidence
        if signal_type in ("MARKET_ENTRY", "ICP_SHIFT") and confidence in (
            "HIGH",
            "MEDIUM",
        ):
            return "HIGH"

        if signal_type == "COMPETITOR" and confidence == "HIGH":
            return "HIGH"

        if signal_type == "CONTENT" and confidence == "HIGH":
            return "HIGH"

        if any(kw in content for kw in _HIGH_KEYWORDS):
            return "HIGH"

        # BACKGROUND: low confidence — log only
        if confidence == "LOW":
            return "BACKGROUND"

        # NORMAL: everything else
        return "NORMAL"

    # ─── process_signal_queue ────────────────────────────────────────────────

    def process_signal_queue(self) -> dict:
        """
        Run scan_market_signals() for each venture, classify, and route by tier.

        Routing:
          CRITICAL   → publish to event bus immediately + Telegram alert
          HIGH       → publish to event bus (included in next morning brief)
          NORMAL     → log to memory (included in daily briefing batch)
          BACKGROUND → log only, never routed upward

        Returns: {venture_id: {tier_counts...}} summary.
        """
        venture_ids = VentureKnowledgeBase.list_ventures()
        summary: dict = {}
        all_signals: list[dict] = []

        for vid in venture_ids:
            tier_counts: dict = {t: 0 for t in SIGNAL_TIERS}

            try:
                signals = self.scan_market_signals(vid)
            except Exception as e:
                print(f"[RealityEngine] scan failed for {vid}: {e}")
                summary[vid] = {"error": str(e)}
                continue

            critical_alerts: list[str] = []

            for signal in signals:
                tier = signal["tier"]
                tier_counts[tier] = tier_counts.get(tier, 0) + 1

                if tier == "CRITICAL":
                    # Publish immediately — fires signal_captured handler
                    try:
                        self.event_bus.publish(
                            "signal_captured",
                            {
                                "signal_text": signal["content"],
                                "source": signal["source"],
                                "venture_id": vid,
                                "tier": "CRITICAL",
                                "signal_type": signal["signal_type"],
                            },
                        )
                    except Exception as e:
                        print(f"[RealityEngine] event_bus CRITICAL publish failed: {e}")
                    critical_alerts.append(
                        f"[{signal['signal_type']}] {signal['content']}"
                    )

                elif tier == "HIGH":
                    # Publish to event bus for morning brief inclusion
                    try:
                        self.event_bus.publish(
                            "signal_captured",
                            {
                                "signal_text": signal["content"],
                                "source": signal["source"],
                                "venture_id": vid,
                                "tier": "HIGH",
                                "signal_type": signal["signal_type"],
                            },
                        )
                    except Exception as e:
                        print(f"[RealityEngine] event_bus HIGH publish failed: {e}")

                elif tier == "NORMAL":
                    # Log to memory for daily briefing batch — no routing
                    try:
                        self.memory.log_event(
                            org_id=self.ctx.org_id,
                            event_type="market_signal_normal",
                            payload=signal,
                        )
                    except Exception as e:
                        print(f"[RealityEngine] NORMAL log failed: {e}")

                # BACKGROUND: signal is captured in scan record — nothing more

            # Immediate alert for CRITICAL signals
            if critical_alerts:
                alert_lines = "\n".join(f"• {a}" for a in critical_alerts)
                _notify(f"REALITY ENGINE — CRITICAL\nVenture: {vid}\n\n{alert_lines}")

            summary[vid] = tier_counts
            all_signals.extend(signals)
            print(f"[RealityEngine] {vid} → {tier_counts}")

        summary["all_signals"] = all_signals
        return summary

    # ─── run_competitor_analysis ─────────────────────────────────────────────

    def run_competitor_analysis(
        self,
        venture_id: str,
        competitor: str,
    ) -> dict:
        """
        Deep analysis of a specific competitor.
        Reasons from known data in VentureKnowledgeBase.
        Returns: positioning, offer_structure, target_icp, weaknesses,
                 opportunities, threat_level.
        """
        venture_ctx = VentureKnowledgeBase.to_agent_context(venture_id, detail="full")

        prompt = (
            "You are a competitive intelligence analyst. Conduct a deep, specific "
            "analysis of a competitor using first-principles reasoning from the "
            "venture context provided. Be direct — no hedging, no generic observations.\n\n"
            f"YOUR VENTURE CONTEXT:\n{venture_ctx}\n\n"
            f"COMPETITOR TO ANALYZE: {competitor}\n\n"
            "Produce a structured competitive intelligence report using EXACTLY "
            "these labeled sections:\n\n"
            "POSITIONING: How does this competitor position themselves? What is their "
            "stated transformation promise, brand identity, and core narrative? "
            "What emotion or identity do they sell?\n\n"
            "OFFER_STRUCTURE: What exactly do they sell? Price point, format, duration, "
            "delivery mechanism, community, coaching access. Be specific.\n\n"
            "TARGET_ICP: Who do they target? Age range, psychological state, specific "
            "pain, where they find them, what language resonates with their audience.\n\n"
            "WEAKNESSES: Where does this competitor fall short? What do customers "
            "report as gaps? Where is the gap between promise and delivery? "
            "What CAN'T they do given their model?\n\n"
            "OPPORTUNITIES: Specific, exploitable gaps. What can your venture do that "
            "this competitor structurally cannot? Reference your venture's specific "
            "advantages (LYFEOS, gamification, AI, execution framework).\n\n"
            "THREAT_LEVEL: LOW / MEDIUM / HIGH — how directly does this competitor "
            "threaten your specific venture? Reference specific audience overlap, "
            "price proximity, and channel competition."
        )

        result = self.loop.run(
            input=prompt,
            agent="reality_engine.competitor",
            task_type=TaskType.ANALYZE,
            venture_id=venture_id,
            max_iterations=1,
        )

        keys = [
            "POSITIONING",
            "OFFER_STRUCTURE",
            "TARGET_ICP",
            "WEAKNESSES",
            "OPPORTUNITIES",
            "THREAT_LEVEL",
        ]
        parsed = _parse_labeled_sections(result.output or "", keys)
        parsed["competitor"] = competitor
        parsed["venture_id"] = venture_id
        parsed["raw_output"] = result.output
        return parsed

    # ─── generate_truth_report ───────────────────────────────────────────────

    def generate_truth_report(self, venture_id: str) -> str:
        """
        On-demand competitor DNA analysis and strategic synthesis.
        Runs run_competitor_analysis() for each known competitor in venture config.
        Synthesizes into a market intelligence report with strategic recommendations.
        """
        v = VentureKnowledgeBase.get(venture_id)
        competitors = [c for c in v.competitors if not c.startswith("TODO")]

        if not competitors:
            return (
                f"TRUTH REPORT — {venture_id}\n\n"
                "No confirmed competitors configured in VentureKnowledgeBase. "
                "Update the competitors list to enable full analysis.\n\n"
                "Current entries:\n" + "\n".join(f"  • {c}" for c in v.competitors)
            )

        analyses: list[dict] = []
        for comp in competitors:
            print(f"[RealityEngine] Analyzing competitor: {comp[:60]}")
            try:
                analysis = self.run_competitor_analysis(venture_id, comp)
                analyses.append(analysis)
            except Exception as e:
                analyses.append({"competitor": comp, "error": str(e)})

        # Build competitor block for synthesis
        comp_blocks: list[str] = []
        for a in analyses:
            if "error" in a:
                comp_blocks.append(f"[{a['competitor']}] Analysis failed: {a['error']}")
                continue
            comp_blocks.append(
                f"COMPETITOR: {a['competitor']}\n"
                f"  Positioning:     {a.get('positioning', '')[:250]}\n"
                f"  Offer Structure: {a.get('offer_structure', '')[:200]}\n"
                f"  Target ICP:      {a.get('target_icp', '')[:200]}\n"
                f"  Weaknesses:      {a.get('weaknesses', '')[:200]}\n"
                f"  Opportunities:   {a.get('opportunities', '')[:200]}\n"
                f"  Threat Level:    {a.get('threat_level', '')[:50]}\n"
            )

        venture_ctx = VentureKnowledgeBase.to_agent_context(venture_id, detail="brief")

        synthesis = self.loop.run(
            input=(
                "You are the strategic intelligence layer for a founder-operator. "
                "Synthesize the competitive intelligence below into a market map "
                "with clear strategic recommendations. No hedging — be the advisor "
                "who tells you the truth about your market position.\n\n"
                f"YOUR VENTURE:\n{venture_ctx}\n\n"
                "COMPETITOR ANALYSES:\n\n" + "\n\n".join(comp_blocks) + "\n\n"
                "Produce the Truth Report with these sections:\n\n"
                "MARKET MAP\n"
                "How are the current players positioned relative to each other? "
                "Draw the landscape. Who owns which corner? Where are you relative "
                "to each of them right now?\n\n"
                "BIGGEST THREAT\n"
                "Which competitor is the most dangerous and exactly why? "
                "Be specific about the overlap.\n\n"
                "WHITESPACE\n"
                "The specific gap in the market that none of them are filling. "
                "Reference the exact ICP language and psychological state that "
                "existing competitors are NOT addressing.\n\n"
                "POSITIONING SHARPENER\n"
                "One specific, immediate change to make your positioning clearer "
                "and more differentiated from these competitors.\n\n"
                "STRATEGIC MOVES\n"
                "2-3 concrete moves based on this competitive landscape. "
                "Specific enough to execute next week."
            ),
            agent="reality_engine.truth_synthesis",
            task_type=TaskType.ANALYZE,
            venture_id=venture_id,
            max_iterations=1,
        )

        today = datetime.date.today().isoformat()
        report = (
            f"TRUTH REPORT — {venture_id.replace('_', ' ').title()}\n"
            f"Generated: {today}\n"
            f"Competitors analyzed: {len(analyses)}\n"
            f"{'─' * 48}\n\n" + (synthesis.output or "Synthesis failed — check logs.")
        )

        # Log to memory for record
        try:
            self.memory.log_event(
                org_id=self.ctx.org_id,
                event_type="truth_report",
                payload={
                    "venture_id": venture_id,
                    "competitors": [a.get("competitor") for a in analyses],
                    "generated_at": datetime.datetime.now(
                        datetime.timezone.utc
                    ).isoformat(),
                    "preview": (synthesis.output or "")[:400],
                },
            )
        except Exception:
            pass

        return report
