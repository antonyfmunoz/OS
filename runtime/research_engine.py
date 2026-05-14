"""
ResearchEngine — autonomous knowledge gap detection and research layer.

The AI identifies its own knowledge gaps from interaction data and researches
them from first principles. Every solved problem becomes permanent capability
stored in the Neon skills table — injected into future relevant agent calls.

Runs weekly on Wednesdays via orchestrator cron.

Usage:
    from runtime.context import load_context_from_env
    from runtime.research_engine import ResearchEngine

    ctx = load_context_from_env()
    re  = ResearchEngine(ctx)

    gaps = re.detect_knowledge_gaps()
    result = re.research_topic('Tony Robbins offer structure and churn patterns')
    summary = re.run_gap_fill_cycle()
"""

import datetime
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

load_dotenv(Path(__file__).parent / ".env")

from runtime.context import EOSContext
from control_plane.runtime.cognitive_loop import CognitiveLoop
from runtime.agent_runtime import TaskType
from runtime.db import get_conn
from state.memory.memory import AgentMemory
from runtime.venture_knowledge import VentureKnowledgeBase
from runtime.strategy_engine import _parse_labeled_sections


class ResearchEngine:
    """
    Autonomous knowledge gap detection and research.

    Finds gaps in interaction quality by querying Neon (authoritative source —
    fallback), researches them from first principles, and stores findings
    as permanent skills in the Neon skills table.
    """

    def __init__(self, ctx: EOSContext):
        self.ctx    = ctx
        self.loop   = CognitiveLoop(ctx)
        self.memory = AgentMemory()

    # ─── detect_knowledge_gaps ───────────────────────────────────────────────

    def detect_knowledge_gaps(self) -> list[str]:
        """
        Query interaction history for patterns where deeper knowledge would
        have produced better outputs. Use CognitiveLoop to identify the gaps.

        Falls back to foundational gap detection when no interaction history
        exists yet (common in early-stage deployments).

        Returns list of gap descriptions (specific topic strings).
        """
        cutoff = (
            datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(days=30)
        ).isoformat()

        # Try Neon first
        interactions: list[dict] = self._query_neon_interactions(cutoff)

        # Fall back to memory.db if Neon returns nothing
        if not interactions:
            interactions = self._query_local_interactions(cutoff)

        # If still empty — no interaction history yet — use foundational gaps
        if not interactions:
            print("[ResearchEngine] No interaction history found — using foundational gaps")
            return self._detect_foundational_gaps()

        # Build summary of recent interactions for gap analysis
        interaction_summary = "\n".join(
            f"  [{i['agent']}] venture={i['venture']}: {i['output'][:200]}"
            for i in interactions[:25]
        )

        prompt = (
            "You are analyzing an AI system's recent interaction history to identify "
            "specific knowledge gaps. A knowledge gap is a topic where the system "
            "made generic statements instead of specific ones, or could not ground "
            "its reasoning in real market data.\n\n"
            "RECENT INTERACTIONS (last 30 days):\n"
            f"{interaction_summary}\n\n"
            "Identify 3-5 specific knowledge gaps. Each gap must be a precise topic "
            "— not a category. Examples of specificity:\n"
            "  BAD:  'competitor knowledge'\n"
            "  GOOD: 'Tony Robbins offer structure, pricing, and why customers "
            "         churn after Unleash the Power Within events'\n\n"
            "Focus on knowledge that would directly improve: competitor analysis, "
            "ICP psychology, platform mechanics, offer design, outreach conversion, "
            "or pricing strategy for the 18-25 men personal development market.\n\n"
            "Output each gap starting with GAP:\n"
            "GAP: <specific topic — precise enough to research in one session>\n\n"
            "Process gaps only, no commentary."
        )

        result = self.loop.run(
            input=prompt,
            agent="research_engine.gap_detector",
            task_type=TaskType.ANALYZE,
            max_iterations=1,
        )

        gaps: list[str] = []
        if result.output:
            for line in result.output.splitlines():
                line = line.strip()
                if line.startswith("GAP:"):
                    gap = line[len("GAP:"):].strip()
                    if gap:
                        gaps.append(gap)

        print(f"[ResearchEngine] {len(gaps)} knowledge gaps detected from interaction history")
        return gaps

    def _query_neon_interactions(self, cutoff: str) -> list[dict]:
        """Query Neon interactions table. Returns [] on any failure."""
        try:
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    SELECT i.id, i.agent_label, i.created_at,
                           v.name AS venture_name
                    FROM interactions i
                    LEFT JOIN ventures v ON v.id = i.venture_id
                    WHERE i.org_id = %s
                      AND i.created_at >= %s
                    ORDER BY i.created_at DESC
                    LIMIT 50
                    """,
                    (self.ctx.org_id, cutoff),
                )
                rows = cur.fetchall()

            result: list[dict] = []
            for i, row in enumerate(rows):
                result.append({
                    "id":      str(row["id"]),
                    "agent":   row["agent_label"] or "unknown",
                    "output":  "",  # output column not stored in Neon interactions
                    "venture": row["venture_name"] or "unknown",
                    "created_at": str(row["created_at"])[:19],
                })
            return result
        except Exception as e:
            print(f"[ResearchEngine] Neon query failed: {e}")
            return []

    def _query_local_interactions(self, cutoff: str) -> list[dict]:
        """Retired: memory.db is no longer active. Returns empty list."""
        return []

    def _detect_foundational_gaps(self) -> list[str]:
        """
        When no interaction history exists, identify foundational knowledge gaps
        based on the known venture landscape and documented competitor placeholders.
        """
        venture_ids = VentureKnowledgeBase.list_ventures()
        venture_blocks: list[str] = []
        for vid in venture_ids:
            try:
                ctx = VentureKnowledgeBase.to_agent_context(vid, detail="full")
                venture_blocks.append(ctx)
            except Exception:
                pass

        prompt = (
            "You are building an AI system to support a founder-operator. "
            "Based on the venture context below, identify 4-5 specific knowledge gaps "
            "that would most limit the AI's ability to give strategic advice and "
            "generate effective outreach for these exact ventures.\n\n"
            "A knowledge gap is a specific topic the AI needs to know deeply. "
            "Be precise:\n"
            "  BAD:  'competitor knowledge'\n"
            "  GOOD: 'Tony Robbins UPW event structure, ticket pricing, and the "
            "         specific complaints his customers post after events'\n\n"
            "VENTURES:\n\n"
            + "\n\n".join(venture_blocks)
            + "\n\n"
            "Focus on: competitor intelligence, ICP psychology, platform outreach "
            "mechanics (Instagram DM limits, warm DM best practices), offer pricing "
            "for cohort programs, and Gen Z / early Millennial motivation patterns.\n\n"
            "Output each gap starting with GAP:\n"
            "GAP: <specific topic>\n\n"
            "No commentary — gaps only."
        )

        result = self.loop.run(
            input=prompt,
            agent="research_engine.foundational_gaps",
            task_type=TaskType.ANALYZE,
            max_iterations=1,
        )

        gaps: list[str] = []
        if result.output:
            for line in result.output.splitlines():
                line = line.strip()
                if line.startswith("GAP:"):
                    gap = line[len("GAP:"):].strip()
                    if gap:
                        gaps.append(gap)

        print(f"[ResearchEngine] {len(gaps)} foundational gaps identified")
        return gaps

    # ─── research_topic ──────────────────────────────────────────────────────

    def research_topic(
        self,
        topic: str,
        venture_id: str | None = None,
    ) -> dict:
        """
        Horizontal research on a topic using live web sources via Scrapling,
        grounded in primary evidence rather than model priors alone.

        Returns:
            topic, venture_id, summary, confidence, sources_quality,
            knowledge_object, raw_output, researched_at
        """
        from runtime.scrapling_connector import ScraplingConnector

        venture_context = ""
        if venture_id:
            try:
                venture_context = (
                    "\n\nAPPLY TO VENTURE:\n"
                    + VentureKnowledgeBase.to_agent_context(venture_id, detail="brief")
                )
            except Exception:
                pass

        # Fetch live web sources to ground the research in real data
        live_sources = ""
        _scraped_pages: list[dict] = []
        try:
            sc = ScraplingConnector()
            _scraped_pages = sc.search_and_fetch(topic, num_results=3)
            if _scraped_pages:
                source_blocks = []
                for p in _scraped_pages:
                    if p.get('status') == 'ok' and p.get('text'):
                        source_blocks.append(
                            f"SOURCE: {p.get('title', '')} ({p.get('url', '')})\n"
                            f"{p.get('text', '')[:600]}"
                        )
                if source_blocks:
                    live_sources = (
                        "\n\nLIVE WEB SOURCES (scraped now — use as primary evidence):\n\n"
                        + "\n\n".join(source_blocks)
                    )
        except Exception as e:
            print(f"[ResearchEngine] Scrapling search failed (non-blocking): {e}")

        # Permanently integrate scraped pages into knowledge base
        if _scraped_pages:
            try:
                from runtime.knowledge_integrator import KnowledgeIntegrator
                ki = KnowledgeIntegrator(self.ctx)
                ki.integrate_search_result(topic, _scraped_pages)
            except Exception as _ki_e:
                print(f"[ResearchEngine] KnowledgeIntegrator failed (non-blocking): {_ki_e}")

        prompt = (
            "You are a deep research engine. Research the following topic from "
            "first principles with the discipline of a top-tier analyst.\n\n"
            "RESEARCH STANDARDS:\n"
            "  - Prioritize: official data, elite practitioners with verified track "
            "    records, primary sources, case studies with real numbers\n"
            "  - Deprioritize: generic blogs, unverified claims, shallow takes\n"
            "  - Cross-validate: if two independent sources disagree, flag it\n"
            "  - Go wide first (what is known across the field?) then deep "
            "    (what matters most for this specific use case?)\n"
            "  - Distinguish between what is proven vs. commonly believed\n\n"
            f"RESEARCH TOPIC: {topic}"
            f"{venture_context}"
            f"{live_sources}\n\n"
            "Produce research output using EXACTLY these labeled sections:\n\n"
            "SUMMARY: 3-5 specific, actionable insights grounded in real evidence. "
            "No generic statements. Every sentence must carry information density "
            "that makes the next strategic decision better.\n\n"
            "CONFIDENCE: HIGH / MEDIUM / LOW — rate confidence based on the quality "
            "and consistency of available evidence, not on your certainty about the topic.\n\n"
            "SOURCES_QUALITY: What types of sources are these findings based on? "
            "Name the specific evidence types used. Where are the gaps?\n\n"
            "KNOWLEDGE_OBJECT: A condensed, reusable knowledge block (200-400 words) "
            "formatted for direct injection into future AI agent prompts. Write in "
            "second person as AI context: 'When reasoning about X, know that...' "
            "No headers, no padding — maximum information density. This will be "
            "injected verbatim into future prompts when this topic is relevant."
        )

        result = self.loop.run(
            input=prompt,
            agent="research_engine.researcher",
            task_type=TaskType.ANALYZE,
            venture_id=venture_id,
            max_iterations=2,
        )

        parsed = _parse_labeled_sections(
            result.output or "",
            ["SUMMARY", "CONFIDENCE", "SOURCES_QUALITY", "KNOWLEDGE_OBJECT"],
        )

        # Normalize confidence
        confidence = parsed.get("confidence", "").strip().upper().split()[0]
        if confidence not in ("HIGH", "MEDIUM", "LOW"):
            confidence = "LOW"

        return {
            "topic":            topic,
            "venture_id":       venture_id,
            "summary":          parsed.get("summary", ""),
            "confidence":       confidence,
            "sources_quality":  parsed.get("sources_quality", ""),
            "knowledge_object": parsed.get("knowledge_object", ""),
            "raw_output":       result.output,
            "researched_at":    datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

    # ─── store_knowledge ─────────────────────────────────────────────────────

    def store_knowledge(
        self,
        topic: str,
        knowledge_object: dict,
        venture_id: str | None = None,
    ) -> bool:
        """
        Write a research result to the Neon skills table as a permanent
        knowledge skill. Skill names follow the pattern: knowledge_{topic_slug}.

        The SkillRegistry loads DB skills on init — this knowledge is injected
        into future relevant agent calls automatically.

        Returns True on success.
        """
        slug       = re.sub(r"[^a-z0-9]+", "_", topic.lower()).strip("_")
        skill_name = f"knowledge_{slug}"
        ko_content = knowledge_object.get("knowledge_object", "")

        if not ko_content or len(ko_content) < 100:
            print(f"[ResearchEngine] store_knowledge skipped — content too thin: '{topic[:60]}'")
            return False

        # Format as skill-compatible markdown (matches SkillRegistry.MIN_CONTENT_LENGTH)
        skill_content = (
            f"# Knowledge: {topic}\n\n"
            f"**Confidence:** {knowledge_object.get('confidence', 'LOW')}\n"
            f"**Researched:** {(knowledge_object.get('researched_at') or '')[:10]}\n\n"
            f"## Summary\n\n{knowledge_object.get('summary', '')}\n\n"
            f"## Knowledge Object\n\n{ko_content}\n\n"
            f"## Source Quality\n\n{knowledge_object.get('sources_quality', '')}\n"
        )

        # Upsert: insert or update if name already exists for this org
        try:
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    "SELECT id FROM skills WHERE org_id = %s AND name = %s",
                    (self.ctx.org_id, skill_name),
                )
                existing = cur.fetchone()
                if existing:
                    cur.execute(
                        """
                        UPDATE skills
                        SET content = %s, version = version + 1, updated_at = NOW()
                        WHERE id = %s
                        """,
                        (skill_content, existing["id"]),
                    )
                    print(f"[ResearchEngine] Knowledge updated: {skill_name}")
                else:
                    cur.execute(
                        """
                        INSERT INTO skills
                          (org_id, name, content, version, created_at, updated_at)
                        VALUES (%s, %s, %s, 1, NOW(), NOW())
                        """,
                        (self.ctx.org_id, skill_name, skill_content),
                    )
                    print(f"[ResearchEngine] Knowledge stored: {skill_name}")
            return True

        except Exception as e:
            print(f"[ResearchEngine] Neon store_knowledge failed: {e}")
            # Fallback: log to memory.db via event system
            try:
                self.memory.log_event(
                    org_id=self.ctx.org_id,
                    event_type="knowledge_stored",
                    payload={
                        "skill_name":      skill_name,
                        "topic":           topic,
                        "venture_id":      venture_id,
                        "confidence":      knowledge_object.get("confidence", "LOW"),
                        "content_preview": skill_content[:500],
                    },
                )
                print(f"[ResearchEngine] Knowledge logged to memory.db (Neon fallback)")
                return True
            except Exception as e2:
                print(f"[ResearchEngine] Fallback log failed: {e2}")
                return False

    # ─── run_gap_fill_cycle ──────────────────────────────────────────────────

    def run_gap_fill_cycle(self) -> dict:
        """
        Full weekly gap-fill cycle: Detect → Research → Store.

        Stores results with confidence >= MEDIUM. Low-confidence research
        is logged but not permanently stored (too uncertain to inject).

        Returns: {gaps_found, gaps_filled, knowledge_objects_created, gaps}
        """
        print("[ResearchEngine] ── Gap fill cycle start ──")

        gaps = self.detect_knowledge_gaps()
        print(f"[ResearchEngine] Gaps to research: {len(gaps)}")

        gaps_filled       = 0
        knowledge_created = 0

        for gap in gaps:
            print(f"[ResearchEngine] Researching: {gap[:70]}...")
            try:
                research = self.research_topic(gap, venture_id=None)

                if research["confidence"] in ("HIGH", "MEDIUM"):
                    stored = self.store_knowledge(gap, research)
                    if stored:
                        knowledge_created += 1
                    gaps_filled += 1
                    print(
                        f"[ResearchEngine] Gap filled (confidence={research['confidence']}): "
                        f"{gap[:60]}"
                    )
                else:
                    print(
                        f"[ResearchEngine] Low confidence — skipping store: {gap[:60]}"
                    )

            except Exception as e:
                print(f"[ResearchEngine] Research failed for '{gap[:60]}': {e}")

        result = {
            "gaps_found":               len(gaps),
            "gaps_filled":              gaps_filled,
            "knowledge_objects_created": knowledge_created,
            "gaps":                     gaps,
        }
        print(f"[ResearchEngine] ── Gap fill cycle complete: {result} ──")
        return result

    # ─── scan_ai_landscape ───────────────────────────────────────────────────

    def scan_ai_landscape(self) -> dict:
        """
        Horizontal scan of the current AI landscape.
        Uses Perplexity for real-time data if PERPLEXITY_API_KEY is set,
        falls back to Sonnet otherwise.
        Stores result as domain_technology_ai in Neon skills table.
        Updates COST_PER_MILLION_TOKENS in-memory for this session.
        """
        import os as _os
        from runtime.model_preferences import PROVIDER_CONFIGS
        from runtime.knowledge_domains import KnowledgeDomainRegistry

        use_perplexity = bool(_os.getenv('PERPLEXITY_API_KEY'))

        prompt = (
            "Research the current state of AI models available via API as of today.\n\n"
            "Return a structured report covering:\n\n"
            "1. FRONTIER MODELS (best available right now)\n"
            "   For each: provider, model name, pricing per 1M tokens input/output, "
            "best use cases, context window, key strengths\n\n"
            "2. COST-EFFICIENT MODELS (best value)\n"
            "   Same structure\n\n"
            "3. LOCAL MODELS (free, run on-device)\n"
            "   Name, size, best use cases\n\n"
            "4. EMBEDDING MODELS\n"
            "   Name, dimensions, best for\n\n"
            "5. VISION/MULTIMODAL MODELS\n"
            "   Name, what it handles\n\n"
            "6. RECENT CHANGES (last 30 days)\n"
            "   New releases, price changes, deprecations\n\n"
            "7. BEST PRACTICES (right now)\n"
            "   Which model for which task type\n\n"
            "Be specific with model names and prices. "
            "Focus on: Anthropic, Google, OpenAI, Perplexity, Meta (local), Qwen (local)."
        )

        result = self.loop.run(
            input=prompt,
            agent='research_engine.ai_landscape_scanner',
            task_type=TaskType.ANALYZE,
        )

        # Store as domain knowledge update
        registry = KnowledgeDomainRegistry()
        registry.save_domain_update(
            'technology_ai',
            result.output or '',
            self.ctx,
        )

        # Permanently integrate into knowledge base
        try:
            from runtime.knowledge_integrator import KnowledgeIntegrator
            from datetime import datetime as _dt
            ki = KnowledgeIntegrator(self.ctx)
            ki.integrate(
                content=result.output or '',
                source='ai_landscape_scan',
                category='market_signal',
                metadata={'scan_date': _dt.now().isoformat()},
            )
        except Exception as _ki_e:
            print(f'[ResearchEngine] KnowledgeIntegrator failed (non-blocking): {_ki_e}')

        # Parse and update COST_PER_MILLION_TOKENS in-memory
        updated_costs = self._parse_model_costs(result.output or '')
        if updated_costs:
            import runtime.agent_runtime as _ar
            _ar.COST_PER_MILLION_TOKENS.update(updated_costs)

        return {
            'scan_complete': True,
            'model_used': result.model_used,
            'domain_updated': 'technology_ai',
            'cost_updates': len(updated_costs),
            'output_preview': (result.output or '')[:300],
        }

    def _parse_model_costs(self, scan_text: str) -> dict:
        """
        Extract model pricing from AI landscape scan text.
        Returns dict matching COST_PER_MILLION_TOKENS format:
            {model_name: {input: float, output: float}}
        Uses Haiku to extract structured JSON pricing.
        """
        if not scan_text:
            return {}

        extract_result = self.loop.run(
            input=(
                "Extract model pricing from this text. "
                "Return ONLY a JSON object mapping model names to pricing. Format:\n"
                "{\"model-name\": {\"input\": 0.00, \"output\": 0.00}}\n"
                "Prices in USD per 1M tokens.\n\n"
                + scan_text[:2000]
            ),
            agent='research_engine.cost_extractor',
            task_type=TaskType.CLASSIFY,
        )

        try:
            import json as _json
            import re as _re
            text = extract_result.output or ''
            # Find outermost JSON object containing pricing data
            match = _re.search(r'\{[^{}]*"input"[^{}]*\}', text, _re.DOTALL)
            if match:
                return _json.loads(match.group())
            # Broader fallback: find any JSON object
            match = _re.search(r'\{.+\}', text, _re.DOTALL)
            if match:
                parsed = _json.loads(match.group())
                # Validate structure — must have at least one entry with input/output keys
                valid = {
                    k: v for k, v in parsed.items()
                    if isinstance(v, dict) and 'input' in v and 'output' in v
                }
                return valid
        except Exception:
            pass
        return {}

    # ─── run_domain_update_cycle ─────────────────────────────────────────────

    def run_domain_update_cycle(self) -> dict:
        """
        Weekly domain update cycle. Horizontal-then-vertical methodology:

        1. HORIZONTAL SCAN — ask Haiku to rate significance (1-10) for every
           domain that is due for update. One cheap call per domain.
        2. VERTICAL DEPTH — research top 5 highest-scoring domains in full
           (score >= 6 only). Saves results to Neon as domain_{key} skills.

        Returns summary dict with scores and updated domain keys.
        """
        from runtime.knowledge_domains import KnowledgeDomainRegistry

        print("[ResearchEngine] ── Domain update cycle start ──")
        registry = KnowledgeDomainRegistry()
        due_domains = registry.get_update_schedule()
        print(f"[ResearchEngine] Domains due: {len(due_domains)}")

        # HORIZONTAL SCAN — cheap scoring pass
        scores: dict[str, int] = {}
        for domain_key in due_domains:
            domain = registry.get_domain(domain_key)
            if not domain:
                continue
            focus_str = ', '.join(domain.get('current_focus', []))
            try:
                score_result = self.loop.run(
                    input=(
                        f"Rate the current significance of developments in "
                        f"'{domain_key}' on a scale 1-10. "
                        f"Focus on: {focus_str}. "
                        f"Reply with ONLY this format: SCORE: N | REASON: one sentence"
                    ),
                    agent='research_engine.domain_scanner',
                    task_type=TaskType.CLASSIFY,
                    max_iterations=1,
                )
                raw = score_result.output or ''
                try:
                    score = int(raw.split('SCORE:')[1].split('|')[0].strip())
                    score = max(1, min(10, score))
                except Exception:
                    score = 5
            except Exception as e:
                print(f"[ResearchEngine] Domain scan failed for {domain_key}: {e}")
                score = 5
            scores[domain_key] = score

        # VERTICAL DEPTH — deep research on top 5 with score >= 6
        sorted_domains = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:5]
        updated: list[str] = []

        for domain_key, score in sorted_domains:
            if score < 6:
                print(f"[ResearchEngine] Domain {domain_key} score={score} — skipping deep research")
                continue
            domain = registry.get_domain(domain_key)
            if not domain:
                continue
            focus_str = ', '.join(domain.get('current_focus', []))
            print(f"[ResearchEngine] Deep research: {domain_key} (score={score})")
            try:
                deep_result = self.loop.run(
                    input=(
                        f"Research the current state of '{domain_key}'. "
                        f"Focus on: {focus_str}. "
                        f"What are the most important developments right now? "
                        f"What should a world-class operator know? "
                        f"Be specific and actionable. 300-500 words."
                    ),
                    agent='research_engine.domain_researcher',
                    task_type=TaskType.ANALYZE,
                    max_iterations=1,
                )
                ctx = self.ctx
                saved = registry.save_domain_update(
                    domain_key,
                    deep_result.output or '',
                    ctx,
                )
                if saved:
                    updated.append(domain_key)
            except Exception as e:
                print(f"[ResearchEngine] Deep research failed for {domain_key}: {e}")

        result = {
            'domains_due': len(due_domains),
            'scanned': len(scores),
            'updated': updated,
            'scores': scores,
        }
        print(f"[ResearchEngine] ── Domain update cycle complete: "
              f"{len(updated)}/{len(due_domains)} updated ──")
        return result
