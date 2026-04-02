"""
WorldPulse — continuous market and creator intelligence monitoring.

Maintains awareness of what is happening in the world relevant to the
founder and their businesses.

Schedule:
  Daily (6am, via orchestrator): run_market_intel_scan()
    — scans MONITORED_SOURCES + checks skills for updates
    — fast, no GWS document rescan
  Saturdays (6am, via orchestrator): run_pulse_scan()
    — full scan: market intel + GWS incremental doc rescan
  On demand: /pulse Telegram command → run_pulse_scan()

Monitors:
  - Key creators (Hormozi, Morgan, Tate, etc.) for new content
  - Market signals (self-improvement market, Instagram algorithm, Whop)
  - Sales tactics and outreach best practices

All findings are permanently integrated into the knowledge base via
KnowledgeIntegrator so the system compounds intelligence over time.

Usage:
    from eos_ai.context import load_context_from_env
    from eos_ai.world_pulse import WorldPulse

    ctx = load_context_from_env()
    wp = WorldPulse(ctx)

    # Daily market scan
    result = wp.run_market_intel_scan()
    print(f"{result['total_integrated']} items integrated")

    # Full Saturday scan (includes GWS)
    pulse = wp.run_pulse_scan()
    print(f"{pulse['total_integrated']} items integrated")
"""

from eos_ai.context import EOSContext
from eos_ai.knowledge_integrator import KnowledgeIntegrator


# ─── Perplexity market intel queries ──────────────────────────────────────────
# Runs daily alongside scrapling. Synthesized real-time intel per venture.

PERPLEXITY_QUERIES: list[dict] = [
    {
        'category': 'AI services market',
        'venture':  'empyrean_creative',
        'prompt': (
            'What are the latest developments in AI automation services for '
            'small businesses this week? What are agencies charging? '
            'What are the most in-demand AI services right now?'
        ),
    },
    {
        'category': "Men's coaching market",
        'venture':  'lyfe_institute',
        'prompt': (
            "What is trending in men's self-improvement and coaching right now? "
            'What offers are gaining traction? What pain points are men 18-28 '
            'expressing online this week?'
        ),
    },
    {
        'category': 'Creator economy',
        'venture':  'personal_brand',
        'prompt': (
            'What are the latest changes to Instagram, TikTok, and YouTube '
            'algorithms this week? What content formats are performing best '
            'for personal brand builders?'
        ),
    },
    {
        'category': 'Competitor intelligence',
        'venture':  'lyfe_institute',
        'prompt': (
            'What are Iman Gadzhi, Alex Hormozi, and other men\'s coaching '
            'brands doing right now? Any new offers, campaigns, or messaging '
            'shifts in the last 7 days?'
        ),
    },
    {
        'category': 'AI tools and models',
        'venture':  'empyrean_creative',
        'prompt': (
            'What are the latest AI model releases, AI agent frameworks, '
            'and AI tools launched or updated this week? '
            'What new capabilities are available? '
            'What are developers and founders talking about in AI right now? '
            'Include: new models, agent frameworks, automation tools, '
            'pricing changes, API updates, breakthrough capabilities.'
        ),
    },
    {
        'category': 'AI agency and automation',
        'venture':  'empyrean_creative',
        'prompt': (
            'What is happening in the AI agency and AI automation space this week? '
            'What are AI agencies charging? '
            'What services are most in demand? '
            'What tools are agencies using? '
            'What are founders saying about replacing human labor with AI? '
            'What new agent use cases are emerging? '
            'Include: pricing, services, tools, case studies, market shifts.'
        ),
    },
]


# ─── Monitored sources ────────────────────────────────────────────────────────

MONITORED_SOURCES: dict[str, list[dict]] = {
    'creators': [
        {
            'name':          'Alex Hormozi',
            'search_query':  'Alex Hormozi new content 2026',
            'relevance':     'offers, sales, business building',
        },
        {
            'name':          'Charlie Morgan',
            'search_query':  'Charlie Morgan outreach sales 2026',
            'relevance':     'outreach, closing, DM strategy',
        },
        {
            'name':          'Andrew Tate',
            'search_query':  'Andrew Tate business 2026',
            'relevance':     'masculine self-improvement market',
        },
    ],
    'market_signals': [
        {
            'name':          'self_improvement_market',
            'search_query':  'men self improvement coaching 2026 trends',
            'relevance':     'ICP market awareness',
        },
        {
            'name':          'instagram_algorithm',
            'search_query':  'Instagram algorithm changes 2026',
            'relevance':     'content distribution',
        },
        {
            'name':          'whop_platform',
            'search_query':  'Whop platform creators 2026',
            'relevance':     'delivery platform awareness',
        },
    ],
    'business_knowledge': [
        {
            'name':          'sales_tactics_current',
            'search_query':  'best DM outreach sales tactics 2026',
            'relevance':     'outreach optimization',
        },
    ],
}


class WorldPulse:
    """
    Continuous market and creator intelligence scanner.

    run_pulse_scan() is the primary entry point — scans all monitored
    sources, fetches live pages, and integrates everything permanently
    into the knowledge base.
    """

    def __init__(self, ctx: EOSContext):
        self.ctx = ctx
        self.ki  = KnowledgeIntegrator(ctx)

    def _scan_with_perplexity(self, queries: list[dict]) -> list[dict]:
        """
        Use Perplexity for real-time market intelligence.

        Returns a list of signal dicts with keys:
            type, category, venture, content, source
        Returns [] if PERPLEXITY_API_KEY is not set.
        """
        signals: list[dict] = []
        try:
            from eos_ai.model_router import get_router, TaskType as RouterTaskType
            router = get_router()

            for query in queries:
                prompt = (
                    f"{query['prompt']}\n\n"
                    f'Provide 3-5 specific, actionable insights. '
                    f'Focus on what matters for a founder running: '
                    f"Lyfe Institute (men's coaching $750), "
                    f'Empyrean Creative (B2B AI services), '
                    f'Personal Brand (content business). '
                    f'Be specific and current.'
                )

                response = router.call_with_fallback(
                    RouterTaskType.MARKET_INTEL,
                    prompt=prompt,
                    max_tokens=500,
                )

                if response:
                    signals.append({
                        'type':     'market_intel',
                        'category': query['category'],
                        'venture':  query['venture'],
                        'content':  response,
                        'source':   'market_intel',
                    })
                    print(f"[WorldPulse] Intel: {query['category']}")

        except Exception as e:
            print(f'[WorldPulse] Scan failed: {e}')
        return signals

    def run_market_intel_scan(self) -> dict:
        """
        Daily market intelligence scan — runs every morning at 6am.

        Scans MONITORED_SOURCES (creators, market signals, business knowledge)
        and checks Claude skills for updates. Does NOT rescan GWS documents —
        that runs weekly on Saturdays via run_pulse_scan().

        Returns:
            {
                'total_integrated': int,
                'sources_scanned':  list[str],
            }
        """
        from eos_ai.scrapling_connector import ScraplingConnector
        sc = ScraplingConnector()

        results_summary: list[str] = []
        total_integrated = 0

        for category, sources in MONITORED_SOURCES.items():
            for source in sources:
                try:
                    pages = sc.search_and_fetch(
                        query=source['search_query'],
                        num_results=3,
                    )
                    pages_ok = 0
                    for page in pages:
                        if page.get('status') == 'ok':
                            content = (
                                f"{source['name']}: "
                                f"{page.get('title', '')}\n"
                                f"{page.get('text', '')[:800]}"
                            )
                            ok = self.ki.integrate(
                                content=content,
                                source=page.get('url', ''),
                                category='world_pulse',
                                metadata={
                                    'monitored_source': source['name'],
                                    'relevance':        source['relevance'],
                                    'category':         category,
                                },
                            )
                            if ok:
                                total_integrated += 1
                                pages_ok += 1

                    results_summary.append(
                        f"{source['name']}: {pages_ok}/{len(pages)} pages integrated"
                    )

                except Exception as e:
                    results_summary.append(f"{source['name']}: error — {e}")
                    print(f'[WorldPulse] Source {source["name"]} failed: {e}')

        # Perplexity market intel — real-time synthesis per venture
        perplexity_signals = self._scan_with_perplexity(PERPLEXITY_QUERIES)
        for sig in perplexity_signals:
            ok = self.ki.integrate(
                content=sig['content'],
                source=sig['source'],
                category='market_intel',
                metadata={
                    'category':  sig['category'],
                    'venture':   sig['venture'],
                    'provider':  sig['source'],
                    'scan_type': 'perplexity',
                },
            )
            if ok:
                total_integrated += 1
            results_summary.append(
                f"{sig['category']}: intel via {sig['source']}"
            )

        # Check Claude skills for source doc updates
        skills_needing_review: list[str] = []
        try:
            from eos_ai.claude_skill_registry import ClaudeSkillRegistryManager
            csrm = ClaudeSkillRegistryManager()
            skills_needing_review = csrm.check_for_updates()
            if skills_needing_review:
                print(
                    f'[WorldPulse] Skills needing review: {skills_needing_review}'
                )
                for skill_id in skills_needing_review:
                    skill = csrm.registry.get(skill_id)
                    results_summary.append(
                        f'skill:{skill_id} — needs review '
                        f'(source: {skill.source_url if skill else "unknown"})'
                    )
        except Exception as e:
            print(f'[WorldPulse] Skill check failed: {e}')

        print(
            f'[WorldPulse] Daily market scan complete — {total_integrated} items '
            f'integrated across {len(results_summary)} sources'
        )

        # Post compact report to Discord
        try:
            from datetime import datetime as _dt
            from eos_ai.discord_utils import post_to_webhook
            now = _dt.now().strftime('%Y-%m-%d %H:%M')
            market_lines = [
                s for s in results_summary
                if 'error' not in s and 'skill:' not in s
            ]
            report_lines = [
                '━━━━━━━━━━━━━━━━━━━━━━━━',
                '📊 **DAILY MARKET SCAN**',
                now,
                '━━━━━━━━━━━━━━━━━━━━━━━━',
                '',
            ]
            for line in market_lines[:5]:
                report_lines.append(f'  {line[:80]}')
            if skills_needing_review:
                report_lines += ['', f'📚 Skills to review: {", ".join(skills_needing_review[:3])}']
            report_lines.append('\n— DEX')
            post_to_webhook(
                '\n'.join(report_lines),
                title='📊 DAILY MARKET SCAN',
                username='World Pulse',
            )
        except Exception as e:
            print(f'[WorldPulse] Daily report failed: {e}')

        return {
            'total_integrated':      total_integrated,
            'sources_scanned':       results_summary,
            'skills_needing_review': skills_needing_review,
        }

    def run_pulse_scan(self) -> dict:
        """
        Scan all monitored sources and permanently integrate findings.

        Returns:
            {
                'total_integrated': int,
                'sources_scanned': list[str],  # one line per source
            }
        """
        from eos_ai.scrapling_connector import ScraplingConnector
        sc = ScraplingConnector()

        results_summary: list[str] = []
        total_integrated = 0

        for category, sources in MONITORED_SOURCES.items():
            for source in sources:
                try:
                    pages = sc.search_and_fetch(
                        query=source['search_query'],
                        num_results=3,
                    )
                    pages_ok = 0
                    for page in pages:
                        if page.get('status') == 'ok':
                            content = (
                                f"{source['name']}: "
                                f"{page.get('title', '')}\n"
                                f"{page.get('text', '')[:800]}"
                            )
                            ok = self.ki.integrate(
                                content=content,
                                source=page.get('url', ''),
                                category='world_pulse',
                                metadata={
                                    'monitored_source': source['name'],
                                    'relevance':        source['relevance'],
                                    'category':         category,
                                },
                            )
                            if ok:
                                total_integrated += 1
                                pages_ok += 1

                    results_summary.append(
                        f"{source['name']}: {pages_ok}/{len(pages)} pages integrated"
                    )

                except Exception as e:
                    results_summary.append(f"{source['name']}: error — {e}")
                    print(f'[WorldPulse] Source {source["name"]} failed: {e}')

        # Perplexity market intel — real-time synthesis per venture
        perplexity_signals = self._scan_with_perplexity(PERPLEXITY_QUERIES)
        for sig in perplexity_signals:
            ok = self.ki.integrate(
                content=sig['content'],
                source=sig['source'],
                category='market_intel',
                metadata={
                    'category':  sig['category'],
                    'venture':   sig['venture'],
                    'provider':  sig['source'],
                    'scan_type': 'perplexity',
                },
            )
            if ok:
                total_integrated += 1
            results_summary.append(
                f"{sig['category']}: intel via {sig['source']}"
            )

        # Check Claude skills for source doc updates
        skills_needing_review: list[str] = []
        try:
            from eos_ai.claude_skill_registry import ClaudeSkillRegistryManager
            csrm = ClaudeSkillRegistryManager()
            skills_needing_review = csrm.check_for_updates()
            if skills_needing_review:
                print(
                    f'[WorldPulse] Skills needing review: {skills_needing_review}'
                )
                for skill_id in skills_needing_review:
                    skill = csrm.registry.get(skill_id)
                    results_summary.append(
                        f'skill:{skill_id} — needs review '
                        f'(source: {skill.source_url if skill else "unknown"})'
                    )
        except Exception as e:
            print(f'[WorldPulse] Skill check failed: {e}')

        # Rescan GWS docs — incremental: only new or modified docs
        gws_ingested = 0
        gws_skipped  = 0
        try:
            from eos_ai.gws_scanner import GWSDocumentScanner
            gws = GWSDocumentScanner(self.ctx)
            docs = gws.scan_all(limit=200, incremental=True)
            gws_skipped = gws._scan_skipped
            if docs:
                gws_ingested = gws.ingest_to_eos(docs)
                gws.save_context_summary(docs)
                results_summary.append(
                    f'google_docs: {gws_ingested} new/modified docs ingested'
                )
                print(f'[WorldPulse] GWS: {gws_ingested} new docs ingested')
            else:
                results_summary.append('google_docs: no new or modified docs')
                print('[WorldPulse] GWS: no new or modified docs')
        except Exception as e:
            results_summary.append(f'google_docs: error — {e}')
            print(f'[WorldPulse] GWS scan failed: {e}')

        print(
            f'[WorldPulse] Scan complete — {total_integrated} items integrated '
            f'across {len(results_summary)} sources'
        )

        # Generate and post pulse report
        try:
            report = self.generate_pulse_report(
                gws_ingested=gws_ingested,
                gws_skipped=gws_skipped,
                skills_needing_review=skills_needing_review,
                sources_scanned=results_summary,
            )
            from eos_ai.discord_utils import post_to_webhook
            post_to_webhook(
                report,
                title='🌍 WORLD PULSE REPORT',
                username='World Pulse',
            )
            print('[WorldPulse] Report sent')
        except Exception as e:
            print(f'[WorldPulse] Report failed: {e}')

        # Sync pulse report to NotebookLM
        try:
            from eos_ai.notebooklm_sync import NotebookLMSync
            nls = NotebookLMSync(self.ctx)
            nls.sync_world_pulse_to_notebook(report)
        except Exception as e:
            print(f'[WorldPulse] NLM sync: {e}')

        # Saturday cross-reference — sync pipeline + founder docs to NotebookLM
        try:
            from datetime import datetime as _dt
            if _dt.now().weekday() == 5:  # Saturday
                from eos_ai.notebooklm_sync import NotebookLMSync
                nls = NotebookLMSync(self.ctx)
                nls.check_and_update()
        except Exception as e:
            print(f'[WorldPulse] NLM check_and_update: {e}')

        return {
            'total_integrated':      total_integrated,
            'sources_scanned':       results_summary,
            'skills_needing_review': skills_needing_review,
        }

    def generate_pulse_report(
        self,
        gws_ingested: int = 0,
        gws_skipped: int = 0,
        skills_needing_review: list | None = None,
        sources_scanned: list | None = None,
    ) -> str:
        """
        Generate a human-readable report of what world pulse learned.
        Posted to Discord #agent-activity after every scan.
        """
        from datetime import datetime as _dt
        skills_needing_review = skills_needing_review or []
        sources_scanned       = sources_scanned or []
        now = _dt.now().strftime('%Y-%m-%d %H:%M')

        lines = [
            '━━━━━━━━━━━━━━━━━━━━━━━━',
            '🌍 **WORLD PULSE REPORT**',
            now,
            '━━━━━━━━━━━━━━━━━━━━━━━━',
            '',
        ]

        # GWS section
        if gws_ingested > 0:
            lines += [
                '📄 **Google Docs**',
                f'  New/updated: {gws_ingested} docs',
                f'  Unchanged: {gws_skipped} docs',
                '',
            ]

        # Skills needing review
        if skills_needing_review:
            lines += [
                '📚 **Skills to Review**',
                f'  {", ".join(skills_needing_review[:5])}',
                '',
            ]

        # Market signals (sources that returned results)
        market_lines = [
            s for s in sources_scanned
            if 'error' not in s and 'google_docs' not in s and 'skill:' not in s
        ]
        if market_lines:
            lines.append('📊 **Market Signals**')
            for sig in market_lines[:4]:
                lines.append(f'  {sig[:80]}')
            lines.append('')

        # AI insight — skipped while Anthropic credits depleted (Qwen blocks on connect)
        # Re-enable when Claude API is restored: call rt.run() via multiprocessing with timeout

        lines.append('— DEX')
        return '\n'.join(lines)

    def get_pulse_summary(self) -> str:
        """
        Returns a summary of recent world knowledge stored in the knowledge base.
        Uses semantic search to surface the most relevant recent findings.
        """
        results = self.ki.query_knowledge(
            'Alex Hormozi Hormozi business coaching 2026',
            limit=3,
        )
        if not results:
            return 'No recent world pulse data yet. Run /pulse to scan.'

        lines = ['Recent world knowledge:']
        for r in results[:3]:
            summary = str(r.get('input_summary', '') or r.get('output_summary', ''))[:100]
            if summary:
                lines.append(f'• {summary}')

        return '\n'.join(lines)
