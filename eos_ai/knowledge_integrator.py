"""
KnowledgeIntegrator — permanent knowledge accumulation layer.

Every piece of information the system produces — web searches, market scans,
conversations, outcomes, world events, creator content — gets permanently
integrated into the knowledge base. Nothing is ever discarded.

Stores in two places:
  1. Neon events table — full content, queryable, permanent
  2. Neon embeddings table — semantic vector, retrievable by meaning

Categories:
  web_search       — search results and scraped pages
  market_signal    — market intelligence from scans
  conversation     — distilled conversation insights
  outcome          — what happened after an action
  world_event      — significant external events
  creator_content  — content from tracked creators (Hormozi, Carnegie, Voss, etc.)
  business_insight — business-specific learnings
  world_pulse      — continuous monitoring of market sources

Usage:
    from eos_ai.context import load_context_from_env
    from eos_ai.knowledge_integrator import KnowledgeIntegrator

    ctx = load_context_from_env()
    ki = KnowledgeIntegrator(ctx)

    ki.integrate(
        content='Hormozi: The key to scaling offers is risk removal.',
        source='hormozi_youtube',
        category='creator_content',
        metadata={'creator': 'Alex Hormozi'},
    )

    results = ki.query_knowledge('offer guarantee conversion')
"""

import uuid
from typing import Optional

from eos_ai.context import EOSContext
from eos_ai.memory import AgentMemory
from eos_ai.embedding_engine import EmbeddingEngine

VALID_CATEGORIES = {
    'web_search',
    'market_signal',
    'conversation',
    'outcome',
    'world_event',
    'creator_content',
    'business_insight',
    'world_pulse',
}


class KnowledgeIntegrator:
    """
    Permanently integrates new knowledge into the system.
    Every call to integrate() stores to Neon events AND embeds for semantic retrieval.
    Never overwrites — always adds. Degrades gracefully on any failure.
    """

    def __init__(self, ctx: EOSContext):
        self.ctx = ctx
        self.ee  = EmbeddingEngine()

    def integrate(
        self,
        content: str,
        source: str,
        category: str,
        metadata: Optional[dict] = None,
    ) -> bool:
        """
        Permanently store new knowledge.

        Stores as an interaction row (not events) so the FK on the embeddings
        table is satisfied and semantic_search() returns results correctly.
        Also logs to the events table for audit trail.

        Args:
            content:  The knowledge to store (max 2000 chars stored, 1000 embedded).
            source:   Origin URL or identifier (e.g. 'hormozi_youtube', 'web_search').
            category: One of VALID_CATEGORIES.
            metadata: Optional extra fields (creator, query, event name, etc.).

        Returns:
            True on success, False on failure.
        """
        import json as _json

        if not content or len(content.strip()) < 10:
            return False

        if category not in VALID_CATEGORIES:
            category = 'business_insight'

        # Store as interaction — satisfies embeddings FK and enables semantic search
        try:
            from eos_ai.db import get_conn, ORG_ID, USER_ID
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    INSERT INTO interactions
                        (org_id, user_id, venture_id, agent_id, skill_id,
                         task_type, model_used, input_summary, output_summary,
                         tokens_json, agent_label, lead_username)
                    VALUES (%s, %s, NULL, NULL, NULL,
                            %s, 'system', %s, %s,
                            %s, %s, NULL)
                    RETURNING id
                    """,
                    (
                        self.ctx.org_id,
                        USER_ID,
                        f'knowledge_{category}',
                        source[:300],
                        content[:300],
                        _json.dumps({'prompt': 0, 'completion': 0, 'total': 0, 'cost_usd': 0.0}),
                        'knowledge_integrator',
                    ),
                )
                interaction_id = str(cur.fetchone()['id'])
        except Exception as e:
            print(f'[KnowledgeIntegrator] interaction insert failed: {e}')
            return False

        # Also log to events for audit trail
        mem = AgentMemory()
        try:
            mem.log_event(
                org_id=self.ctx.org_id,
                event_type=f'knowledge_{category}',
                payload={
                    'content':        content[:2000],
                    'source':         source,
                    'category':       category,
                    'interaction_id': interaction_id,
                    'metadata':       metadata or {},
                },
            )
        except Exception:
            pass  # audit log failure does not fail integration

        # Embed for semantic retrieval (uses interaction_id — FK satisfied)
        if self.ee.is_available() and len(content) > 20:
            try:
                self.ee.embed_interaction(
                    interaction_id=interaction_id,
                    content=f'{source}: {content[:1000]}',
                    org_id=self.ctx.org_id,
                )
            except Exception as e:
                print(f'[KnowledgeIntegrator] embed failed (non-blocking): {e}')

        return True

    def integrate_search_result(
        self,
        query: str,
        results: list[dict],
    ) -> int:
        """
        Integrate all pages from a web search permanently.
        Called after every search — stores what was found.

        Returns: number of pages successfully integrated.
        """
        integrated = 0
        for r in results:
            content = (
                f'Search: {query}\n'
                f'Source: {r.get("url", "")}\n'
                f'Title: {r.get("title", "")}\n'
                f'Content: {r.get("text", "")[:500]}'
            )
            ok = self.integrate(
                content=content,
                source=r.get('url', 'web_search'),
                category='web_search',
                metadata={'query': query},
            )
            if ok:
                integrated += 1
        return integrated

    def integrate_creator_content(
        self,
        creator: str,
        title: str,
        content: str,
        url: str = '',
    ) -> bool:
        """
        Store content from a known creator permanently.
        Tracks: Hormozi, Carnegie, Voss, Morgan, Hormozi, etc.
        """
        return self.integrate(
            content=f'{creator}: {title}\n{content}',
            source=url or creator,
            category='creator_content',
            metadata={
                'creator': creator,
                'title':   title,
            },
        )

    def integrate_world_event(
        self,
        event: str,
        context: str,
        source: str,
    ) -> bool:
        """Store a significant world event permanently."""
        return self.integrate(
            content=f'WORLD EVENT: {event}\n{context}',
            source=source,
            category='world_event',
            metadata={'event': event},
        )

    def query_knowledge(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict]:
        """
        Semantic search across all stored knowledge.
        Returns top-N results by embedding similarity.
        Degrades to empty list when embedding engine unavailable.
        """
        if not self.ee.is_available():
            return []
        return self.ee.semantic_search(
            query=query,
            org_id=self.ctx.org_id,
            limit=limit,
        )
