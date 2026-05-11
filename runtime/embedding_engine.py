"""
EmbeddingEngine — Three-tier hybrid embedding with graceful degradation.

Tier 1: fastembed BAAI/bge-small-en-v1.5 (local, free, 384-dim) — primary.
         Matches the embeddings.embedding vector(384) schema exactly.
Tier 2: Gemini text-embedding (cloud, 768-dim) — fallback. NOTE: its 768-dim
         output will NOT fit the 384-dim column; Tier 2 is effectively a
         query-side fallback only (semantic_search will skip DB write path).
Tier 3: keyword matching (no embedding) — always works, returns None

Every interaction stored → immediately embedded → semantically retrievable
from any interface. Degrades gracefully through the tier chain.
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load env vars from all known .env locations so GEMINI_API_KEY is available
# regardless of which entry point started the process.
# services/.env first (operational keys), eos_ai/.env second (AI keys, wins on conflict).
_REPO_ROOT = Path(__file__).parent.parent
load_dotenv(_REPO_ROOT / 'services' / '.env')
load_dotenv(_REPO_ROOT / 'eos_ai' / '.env', override=True)


class EmbeddingEngine:

    # Gemini model kept for Tier 2 fallback
    GEMINI_MODEL = 'models/gemini-embedding-001'
    GEMINI_DIMS  = 768

    # fastembed model for Tier 1
    FASTEMBED_MODEL = 'BAAI/bge-small-en-v1.5'
    FASTEMBED_DIMS  = 384

    def __init__(self):
        self._gemini_key  = os.getenv('GEMINI_API_KEY')
        self._genai_new   = False
        self._fastembed   = None  # lazy-loaded on first use

        # Pre-warm fastembed to surface errors at startup, not first call
        try:
            self._get_text_model()
        except Exception:
            pass  # logged inside _get_text_model

        # Gemini setup (Tier 2)
        if self._gemini_key:
            try:
                import google.genai as genai
                from google.genai import types as genai_types
                self._client    = genai.Client(api_key=self._gemini_key)
                self._types     = genai_types
                self._genai_new = True
            except ImportError:
                try:
                    import google.generativeai as genai  # type: ignore[no-redef]
                    genai.configure(api_key=self._gemini_key)
                    self._genai = genai
                except ImportError:
                    pass  # Gemini unavailable — Tier 2 disabled

        print(f'[EmbeddingEngine] Active: {self.get_active_tier()}')

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_text_model(self):
        """Lazy-load fastembed TextEmbedding model (cached after first call)."""
        if self._fastembed is None:
            from fastembed import TextEmbedding
            self._fastembed = TextEmbedding(self.FASTEMBED_MODEL)
        return self._fastembed

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def embed(
        self,
        text: str,
        task_type: str = None,
    ) -> Optional[list[float]]:
        """
        Generate an embedding vector using the first available tier.

        Returns None only if all tiers fail — callers should fall back
        to keyword-based search in that case.

        task_type is accepted for API compatibility but only used by
        the Gemini Tier 2 path.
        """
        if not text or not text.strip():
            return None
        text = text[:8000]  # guard against oversized inputs

        # Tier 1: fastembed (local, free, 384-dim)
        try:
            model = self._get_text_model()
            embeddings = list(model.embed([text]))
            return embeddings[0].tolist()
        except Exception as e:
            print(f'[EmbeddingEngine] fastembed failed: {e} — falling back to Gemini')

        # Tier 2: Gemini text embedding (cloud, paid, 768-dim)
        if self._gemini_key:
            try:
                if self._genai_new:
                    result = self._client.models.embed_content(
                        model=self.GEMINI_MODEL,
                        contents=text,
                        config=self._types.EmbedContentConfig(
                            task_type=task_type or 'RETRIEVAL_DOCUMENT',
                            output_dimensionality=self.GEMINI_DIMS,
                        ),
                    )
                    embedding = list(result.embeddings[0].values)
                else:
                    result = self._genai.embed_content(
                        model=self.GEMINI_MODEL,
                        content=text,
                        task_type=task_type or 'retrieval_document',
                        output_dimensionality=self.GEMINI_DIMS,
                    )
                    embedding = result['embedding']
                print('[EmbeddingEngine] Gemini text fallback used')
                return embedding
            except Exception as e:
                print(f'[EmbeddingEngine] Gemini fallback failed: {e} — falling back to keywords')

        # Tier 3: keyword matching — callers handle None by using keyword search
        print('[EmbeddingEngine] All embedding methods failed. Keyword matching active.')
        return None

    def is_available(self) -> bool:
        """True if ANY embedding method is functional (not just keyword fallback)."""
        try:
            self._get_text_model()
            return True  # fastembed available
        except Exception:
            pass
        if self._gemini_key:
            return True  # Gemini available
        return False  # keyword only

    def get_active_tier(self) -> str:
        """Return the highest-priority tier currently available. Used for monitoring."""
        try:
            self._get_text_model()
            return 'fastembed (local)'
        except Exception:
            pass
        if self._gemini_key:
            return 'gemini (cloud fallback)'
        return 'keyword matching'

    def embed_interaction(
        self,
        interaction_id: str,
        content: str,
        org_id: str,
    ) -> bool:
        """
        Embed content and store in the Neon embeddings table.
        Called after every interaction is logged — never blocks the main call.
        Deletes any existing embedding for this interaction before reinserting.
        Records which model/tier was used in embedding_model column.
        """
        # Provider stage
        try:
            vector = self.embed(content, 'retrieval_document')
        except Exception as e:
            print(
                f'[EmbeddingEngine] PROVIDER_FAILURE iid={interaction_id} '
                f'cls={type(e).__name__}: {e}'
            )
            return False
        if not vector:
            print(
                f'[EmbeddingEngine] PROVIDER_NO_VECTOR iid={interaction_id} '
                f'(all tiers returned None — keyword-only mode)'
            )
            return False

        # Dimension guard — DB column is vector(384); reject mismatches loudly
        # instead of letting Postgres raise a cryptic type error mid-INSERT.
        EXPECTED_DIMS = self.FASTEMBED_DIMS  # 384
        if len(vector) != EXPECTED_DIMS:
            print(
                f'[EmbeddingEngine] DIMENSION_MISMATCH iid={interaction_id} '
                f'got={len(vector)} expected={EXPECTED_DIMS} — skipping DB write. '
                f'Tier 2 (Gemini 768-dim) cannot be persisted against the '
                f'current 384-dim schema.'
            )
            return False

        # Determine which model label to record (fastembed is the only writeable tier)
        try:
            self._get_text_model()
            model_label = self.FASTEMBED_MODEL
        except Exception:
            model_label = self.GEMINI_MODEL  # shouldn't happen given dim guard above

        # Serialization stage
        import json
        try:
            vec_json = json.dumps(vector)
        except (TypeError, ValueError) as e:
            print(
                f'[EmbeddingEngine] SERIALIZATION_FAILURE iid={interaction_id} '
                f'cls={type(e).__name__}: {e}'
            )
            return False

        # DB write stage
        from eos_ai.db import get_conn
        try:
            with get_conn(org_id) as cur:
                cur.execute(
                    'DELETE FROM embeddings '
                    'WHERE interaction_id = %s AND org_id = %s',
                    (interaction_id, org_id),
                )
                cur.execute(
                    '''
                    INSERT INTO embeddings
                        (interaction_id, org_id, embedding,
                         content_preview, embedding_model)
                    VALUES (%s, %s, %s::vector, %s, %s)
                    ''',
                    (
                        interaction_id,
                        org_id,
                        vec_json,
                        content[:200],
                        model_label,
                    ),
                )
            return True
        except Exception as e:
            # Keep non-blocking semantics but classify the failure.
            kind = 'DB_FAILURE'
            msg = str(e).lower()
            if 'expected' in msg and 'dimensions' in msg:
                kind = 'DIMENSION_MISMATCH_DB'
            elif 'duplicate' in msg or 'unique' in msg:
                kind = 'DB_CONSTRAINT'
            print(
                f'[EmbeddingEngine] {kind} iid={interaction_id} '
                f'cls={type(e).__name__}: {e}'
            )
            return False

    def semantic_search(
        self,
        query: str,
        org_id: str,
        limit: int = 5,
        venture_id: str | None = None,
    ) -> list[dict]:
        """
        Return the top-N interactions most semantically similar to query.

        Falls back to recency-based search if all embedding tiers fail.
        """
        query_vector = self.embed(query, 'retrieval_query')
        if not query_vector:
            return self._recent_fallback(org_id, limit, venture_id)

        from eos_ai.db import get_conn
        import json
        try:
            with get_conn(org_id) as cur:
                if venture_id:
                    cur.execute(
                        '''
                        SELECT
                            i.id, i.agent_label, i.task_type,
                            i.input_summary, i.output_summary,
                            i.created_at,
                            1 - (e.embedding <=> %s::vector) AS similarity
                        FROM embeddings e
                        JOIN interactions i ON i.id = e.interaction_id
                        WHERE e.org_id = %s
                          AND i.venture_id = %s
                        ORDER BY e.embedding <=> %s::vector
                        LIMIT %s
                        ''',
                        (
                            json.dumps(query_vector),
                            org_id, venture_id,
                            json.dumps(query_vector), limit,
                        ),
                    )
                else:
                    cur.execute(
                        '''
                        SELECT
                            i.id, i.agent_label, i.task_type,
                            i.input_summary, i.output_summary,
                            i.created_at,
                            1 - (e.embedding <=> %s::vector) AS similarity
                        FROM embeddings e
                        JOIN interactions i ON i.id = e.interaction_id
                        WHERE e.org_id = %s
                        ORDER BY e.embedding <=> %s::vector
                        LIMIT %s
                        ''',
                        (
                            json.dumps(query_vector),
                            org_id,
                            json.dumps(query_vector), limit,
                        ),
                    )
                rows = cur.fetchall()
                return [
                    {
                        'id':             str(r['id']),
                        'agent':          r['agent_label'],
                        'task_type':      r['task_type'],
                        'input_summary':  r['input_summary'],
                        'output_summary': r['output_summary'],
                        'created_at':     (
                            r['created_at'].isoformat()
                            if r['created_at'] else None
                        ),
                        'similarity':     float(r['similarity']),
                    }
                    for r in rows
                ]
        except Exception as e:
            print(f'[EmbeddingEngine] search failed: {e}')
            return self._recent_fallback(org_id, limit, venture_id)

    def backfill_missing(
        self,
        org_id: str,
        limit: int = 200,
    ) -> dict:
        """
        Find interactions without embeddings and embed them in bulk.
        Rate-limited: pauses 1s every 20 rows to avoid API limits.
        Returns stats dict: found, embedded, failed, skipped.
        """
        if not self.is_available():
            return {
                'found': 0, 'embedded': 0,
                'failed': 0, 'skipped': 0,
                'reason': 'No embedding method available',
            }

        import time
        from eos_ai.db import get_conn

        with get_conn(org_id) as cur:
            cur.execute(
                '''
                SELECT i.id, i.input_summary,
                       i.output_summary, i.agent_label
                FROM interactions i
                LEFT JOIN embeddings e
                  ON e.interaction_id = i.id
                WHERE i.org_id = %s
                  AND e.id IS NULL
                ORDER BY i.created_at ASC
                LIMIT %s
                ''',
                (org_id, limit),
            )
            missing = cur.fetchall()

        found    = len(missing)
        embedded = failed = skipped = 0

        for i, row in enumerate(missing):
            iid     = str(row['id'])
            content = (
                f"{row['input_summary'] or ''} "
                f"{row['output_summary'] or ''}"
            ).strip()

            if len(content) < 10:
                skipped += 1
                continue

            if i > 0 and i % 20 == 0:
                time.sleep(1)

            ok = self.embed_interaction(iid, content, org_id)
            if ok:
                embedded += 1
            else:
                failed += 1

        return {
            'found':    found,
            'embedded': embedded,
            'failed':   failed,
            'skipped':  skipped,
        }

    def _recent_fallback(
        self,
        org_id: str,
        limit: int,
        venture_id: str | None,
    ) -> list[dict]:
        """Recency-based fallback when all embedding tiers fail."""
        from eos_ai.memory import AgentMemory
        mem = AgentMemory()
        return mem.get_recent(venture_id=venture_id, limit=limit)
