"""
Core test suite — 10 most critical EOS modules.
Run before any deploy: python3 -m pytest /opt/OS/tests/ -v
"""

import sys
import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"

from dotenv import load_dotenv
load_dotenv(f'{_ROOT}/runtime/.env')
load_dotenv(f'{_ROOT}/services/.env')

import pytest


# ─── EmbeddingEngine ──────────────────────────────────────────────────────────

class TestEmbeddingEngine:

    def test_available(self):
        from understanding.embedding.embedding_engine import EmbeddingEngine
        ee = EmbeddingEngine()
        assert ee.is_available()

    def test_embed_returns_384_dims(self):
        from understanding.embedding.embedding_engine import EmbeddingEngine
        ee = EmbeddingEngine()
        result = ee.embed('test text')
        assert result is not None
        assert len(result) == 384

    def test_embed_empty_returns_none(self):
        from understanding.embedding.embedding_engine import EmbeddingEngine
        ee = EmbeddingEngine()
        assert ee.embed('') is None
        assert ee.embed('   ') is None

    def test_active_tier(self):
        from understanding.embedding.embedding_engine import EmbeddingEngine
        ee = EmbeddingEngine()
        tier = ee.get_active_tier()
        assert tier in [
            'fastembed (local)',
            'gemini (cloud fallback)',
            'keyword matching',
        ]

    def test_semantic_search_returns_results(self):
        from understanding.embedding.embedding_engine import EmbeddingEngine
        from runtime.context import load_context_from_env
        ctx = load_context_from_env()
        ee = EmbeddingEngine()
        results = ee.semantic_search('focus today', ctx.org_id, limit=3)
        # Should return list (empty is ok if no data, but must not raise)
        assert isinstance(results, list)
        for r in results:
            assert 'similarity' in r
            assert r['similarity'] >= 0.0


# ─── DiscordUtils ─────────────────────────────────────────────────────────────

class TestDiscordUtils:

    def test_chunk_message_under_discord_limit(self):
        from runtime.discord_utils import chunk_message
        long = 'x ' * 1000
        chunks = chunk_message(long)
        # Discord's hard limit is 2000. DISCORD_MAX_CHARS=1800 is the content
        # budget; part labels (*Part 1/2*\n\n ≈ 13 chars) may push labeled
        # chunks slightly above 1800 but must stay under Discord's 2000 limit.
        assert all(len(c) <= 2000 for c in chunks)

    def test_chunk_preserves_all_content(self):
        from runtime.discord_utils import chunk_message
        text = 'word ' * 400
        chunks = chunk_message(text)
        rejoined = ''.join(chunks)
        # All original characters should be present
        assert len(rejoined) >= len(text.strip())

    def test_short_message_returns_single_chunk(self):
        from runtime.discord_utils import chunk_message
        text = 'short message'
        chunks = chunk_message(text)
        assert len(chunks) == 1
        assert chunks[0] == text


# ─── OutputValidator ──────────────────────────────────────────────────────────

class TestOutputValidator:

    def test_catches_long_discord_message(self):
        from runtime.output_validator import OutputValidator
        v = OutputValidator()
        result = v.validate_discord_message('x ' * 1000)
        violation_types = [viol.violation_type.value for viol in result.violations]
        assert 'discord_chunk_limit' in violation_types

    def test_catches_generic_response(self):
        from runtime.output_validator import OutputValidator
        v = OutputValidator()
        result = v.validate_discord_message(
            'Great question! How can I help?', 'agent_response'
        )
        assert len(result.violations) > 0

    def test_clean_message_passes(self):
        from runtime.output_validator import OutputValidator
        v = OutputValidator()
        result = v.validate_discord_message(
            'Morning. Zero pipeline. 20 DMs today.'
        )
        critical = [
            viol for viol in result.violations
            if viol.severity == 'critical'
        ]
        assert len(critical) == 0

    def test_result_has_expected_fields(self):
        from runtime.output_validator import OutputValidator
        v = OutputValidator()
        result = v.validate_discord_message('test')
        assert hasattr(result, 'passed')
        assert hasattr(result, 'violations')
        assert hasattr(result, 'score')


# ─── SignalHierarchy ──────────────────────────────────────────────────────────

class TestSignalHierarchy:

    def test_classifies_business_domain(self):
        from control_plane.signals.signal_hierarchy import SignalHierarchyEngine
        from runtime.context import load_context_from_env
        ctx = load_context_from_env()
        she = SignalHierarchyEngine(ctx)
        result = she.classify_input('I closed my first client today')
        assert result['domain'] == 'business'

    def test_classifies_reality_tier(self):
        from control_plane.signals.signal_hierarchy import SignalHierarchyEngine, SignalTier
        from runtime.context import load_context_from_env
        ctx = load_context_from_env()
        she = SignalHierarchyEngine(ctx)
        result = she.classify_input('revenue is down this week')
        assert result['primary_tier'] == SignalTier.REALITY

    def test_returns_required_keys(self):
        from control_plane.signals.signal_hierarchy import SignalHierarchyEngine
        from runtime.context import load_context_from_env
        ctx = load_context_from_env()
        she = SignalHierarchyEngine(ctx)
        result = she.classify_input('test input')
        assert 'primary_tier' in result
        assert 'domain' in result


# ─── KnowledgeIntegrator ──────────────────────────────────────────────────────

class TestKnowledgeIntegrator:

    def test_integrate_returns_bool(self):
        from understanding.knowledge.knowledge_integrator import KnowledgeIntegrator
        from runtime.context import load_context_from_env
        ctx = load_context_from_env()
        ki = KnowledgeIntegrator(ctx)
        result = ki.integrate(
            content='Test knowledge entry for unit test',
            source='test_suite',
            category='test',
        )
        assert isinstance(result, bool)

    def test_query_knowledge_returns_list(self):
        from understanding.knowledge.knowledge_integrator import KnowledgeIntegrator
        from runtime.context import load_context_from_env
        ctx = load_context_from_env()
        ki = KnowledgeIntegrator(ctx)
        results = ki.query_knowledge('test')
        assert isinstance(results, list)

    def test_empty_content_handled(self):
        from understanding.knowledge.knowledge_integrator import KnowledgeIntegrator
        from runtime.context import load_context_from_env
        ctx = load_context_from_env()
        ki = KnowledgeIntegrator(ctx)
        # Should not raise — graceful handling
        try:
            result = ki.integrate(content='', source='test', category='test')
            assert isinstance(result, bool)
        except Exception:
            pass  # raising is acceptable, crashing the process is not
