"""
WorldPulse — continuous market and creator intelligence monitoring.

Maintains awareness of what is happening in the world relevant to the
founder and their businesses.

Schedule:
  Daily (6am, via orchestrator): run_market_intel_scan()
    — scans tenant-derived monitored sources + checks skills for updates
    — fast, no GWS document rescan
  Saturdays (6am, via orchestrator): run_pulse_scan()
    — full scan: market intel + GWS incremental doc rescan
  On demand: /pulse Telegram command → run_pulse_scan()

Monitors:
  - Competitor creators (from each venture's BIS) for new content
  - Generic market signals (platform algorithms, delivery platforms)
  - Sales tactics and outreach best practices

All findings are permanently integrated into the knowledge base via
KnowledgeIntegrator so the system compounds intelligence over time.

Usage:
    from substrate.state.context.context import load_context_from_env
    from substrate.understanding.world_pulse.world_pulse import WorldPulse

    ctx = load_context_from_env()
    wp = WorldPulse(ctx)

    # Daily market scan
    result = wp.run_market_intel_scan()
    print(f"{result['total_integrated']} items integrated")

    # Full Saturday scan (includes GWS)
    pulse = wp.run_pulse_scan()
    print(f"{pulse['total_integrated']} items integrated")
"""

from substrate.state.context.context import SubstrateContext
from substrate.understanding.knowledge.knowledge_integrator import KnowledgeIntegrator


# ─── Perplexity market intel queries ──────────────────────────────────────────
# Queries are GENERATED PER VENTURE from the tenant's BIS at runtime
# (build_perplexity_queries) — never a hardcoded per-slug table. A fixed table
# would leak one tenant's ventures, ICP, and competitors into every seat.


def build_perplexity_queries(ctx=None) -> list[dict]:
    """Build market-intel queries per venture from the tenant registry + BIS.

    For each venture the tenant runs, derive an intel query from its industry,
    ICP, and known competitors (all from BIS). Returns [] when no ventures are
    loaded, so the pulse scan simply skips real-time synthesis rather than
    querying about some other tenant's market.
    """
    queries: list[dict] = []
    try:
        from substrate.state.business.business_instance import BusinessInstanceManager
        from substrate.state.context.context import load_context_from_env

        ctx = ctx or load_context_from_env()
        ventures = list(getattr(ctx, 'ventures', []) or [])
        bim = BusinessInstanceManager(ctx)
        for v in ventures:
            vid = v.get('id') or v.get('venture_id') or ''
            vname = v.get('name') or vid or 'this venture'
            if not vid:
                continue
            bis = None
            try:
                bis = bim.get_bis(vid)
            except Exception:
                bis = None
            industry = (getattr(bis, 'industry', '') or '') if bis else ''
            icp = (getattr(bis, 'icp_description', '') or '') if bis else ''
            competitors = (getattr(bis, 'main_competitors', None) or []) if bis else []
            comp_str = ', '.join(str(c) for c in competitors[:5])
            focus = industry or vname
            prompt = (
                f'What is trending in the {focus} market this week? '
                'What offers are gaining traction, and what pain points is the '
                f'target audience{f" ({icp})" if icp else ""} expressing online '
                'right now?'
            )
            if comp_str:
                prompt += (
                    f' Also: what are these competitors doing lately — {comp_str}? '
                    'Any new offers, campaigns, or messaging shifts in the last 7 days?'
                )
            queries.append({
                'category': f'{vname} market',
                'venture':  vid,
                'prompt':   prompt,
            })
    except Exception:
        return []
    return queries


# ─── Monitored sources ────────────────────────────────────────────────────────
# Sources are BUILT PER TENANT at runtime (build_monitored_sources): the
# creators to watch come from each venture's competitor list in BIS, and only
# the venture-agnostic distribution/outreach signals are generic. A hardcoded
# creator/market table would leak one tenant's competitive watch-list into
# every seat.

# Generic, tenant-agnostic signals — apply to any founder-operator regardless
# of niche (platform algorithms, general outreach craft). No tenant identity.
_GENERIC_SIGNAL_SOURCES: list[dict] = [
    {
        'name':          'social_algorithms',
        'search_query':  'Instagram TikTok YouTube algorithm changes this year',
        'relevance':     'content distribution',
    },
    {
        'name':          'outreach_tactics_current',
        'search_query':  'best DM outreach and sales tactics this year',
        'relevance':     'outreach optimization',
    },
]


def build_monitored_sources(ctx=None) -> dict[str, list[dict]]:
    """Build the monitored-source map for THIS tenant.

    Creators to watch are derived from each venture's `main_competitors` (BIS);
    generic distribution/outreach signals are always included. Returns just the
    generic signals when no tenant ventures/competitors are configured — never a
    hardcoded per-niche creator list.
    """
    creators: list[dict] = []
    try:
        from substrate.state.business.business_instance import BusinessInstanceManager
        from substrate.state.context.context import load_context_from_env

        ctx = ctx or load_context_from_env()
        ventures = list(getattr(ctx, 'ventures', []) or [])
        bim = BusinessInstanceManager(ctx)
        seen: set[str] = set()
        for v in ventures:
            vid = v.get('id') or v.get('venture_id') or ''
            if not vid:
                continue
            try:
                bis = bim.get_bis(vid)
            except Exception:
                bis = None
            for comp in (getattr(bis, 'main_competitors', None) or []) if bis else []:
                name = str(comp).strip()
                if not name or name.lower() in seen:
                    continue
                seen.add(name.lower())
                creators.append({
                    'name':         name,
                    'search_query': f'{name} new content this year',
                    'relevance':    'competitor / market awareness',
                })
    except Exception:
        creators = []

    sources: dict[str, list[dict]] = {'market_signals': list(_GENERIC_SIGNAL_SOURCES)}
    if creators:
        sources['creators'] = creators
    return sources


class WorldPulse:
    """
    Continuous market and creator intelligence scanner.

    run_pulse_scan() is the primary entry point — scans all monitored
    sources, fetches live pages, and integrates everything permanently
    into the knowledge base.
    """

    def __init__(self, ctx: SubstrateContext):
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
            from substrate.contracts.agent_types import TaskType as RouterTaskType
            from substrate.sockets.intelligence_port import get_router
            router = get_router()

            # Build a substrate-neutral venture context string from ctx.ventures
            # (falls back to a generic founder framing when no ventures are loaded).
            _ventures = getattr(self, 'ctx', None)
            _v_list = getattr(_ventures, 'ventures', []) if _ventures else []
            if _v_list:
                _venture_ctx_str = ', '.join(
                    f"{v.get('name', v.get('id', ''))}"
                    f"{' (' + v.get('offer', '') + ')' if v.get('offer') else ''}"
                    for v in _v_list
                )
            else:
                _venture_ctx_str = 'a founder-operator portfolio'

            for query in queries:
                prompt = (
                    f"{query['prompt']}\n\n"
                    f'Provide 3-5 specific, actionable insights. '
                    f'Focus on what matters for a founder running: '
                    f'{_venture_ctx_str}. '
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

        Scans tenant-derived monitored sources (competitor creators + generic signals)
        and checks Claude skills for updates. Does NOT rescan GWS documents —
        that runs weekly on Saturdays via run_pulse_scan().

        Returns:
            {
                'total_integrated': int,
                'sources_scanned':  list[str],
            }
        """
        from substrate.sockets.browser_port import get_scrapling_connector_class
        ScraplingConnector = get_scrapling_connector_class()
        sc = ScraplingConnector()

        results_summary: list[str] = []
        total_integrated = 0

        for category, sources in build_monitored_sources(self.ctx).items():
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
        perplexity_signals = self._scan_with_perplexity(build_perplexity_queries(self.ctx))
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
            from substrate.state.registries.claude_skill_registry import ClaudeSkillRegistryManager
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
            from substrate.sockets.notification import notify_webhook
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
            report_lines.append(f'\n— {os.environ.get("AI_NAME", "AI")}')
            notify_webhook(
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
        from substrate.sockets.browser_port import get_scrapling_connector_class
        ScraplingConnector = get_scrapling_connector_class()
        sc = ScraplingConnector()

        results_summary: list[str] = []
        total_integrated = 0

        for category, sources in build_monitored_sources(self.ctx).items():
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
        perplexity_signals = self._scan_with_perplexity(build_perplexity_queries(self.ctx))
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
            from substrate.state.registries.claude_skill_registry import ClaudeSkillRegistryManager
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
            from substrate.sockets.data_source_port import get_gws_scanner_class
            GWSDocumentScanner = get_gws_scanner_class()
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
            from substrate.sockets.notification import notify_webhook
            notify_webhook(
                report,
                title='🌍 WORLD PULSE REPORT',
                username='World Pulse',
            )
            print('[WorldPulse] Report sent')
        except Exception as e:
            print(f'[WorldPulse] Report failed: {e}')

        # Sync pulse report to NotebookLM
        try:
            from substrate.sockets.data_source_port import get_notebooklm_sync_class
            NotebookLMSync = get_notebooklm_sync_class()
            nls = NotebookLMSync(self.ctx)
            nls.sync_world_pulse_to_notebook(report)
        except Exception as e:
            print(f'[WorldPulse] NLM sync: {e}')

        # Saturday cross-reference — sync pipeline + founder docs to NotebookLM
        try:
            from datetime import datetime as _dt
            if _dt.now().weekday() == 5:  # Saturday
                from substrate.sockets.data_source_port import get_notebooklm_sync_class
                NotebookLMSync = get_notebooklm_sync_class()
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

        lines.append(f'— {os.environ.get("AI_NAME", "AI")}')
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
