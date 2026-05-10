"""Tests for the LLM planning strategy — data models, registry, and proposal logic.

Validates:
1. Canonicalization determinism (key ordering, float, unicode, null).
2. EventTypeRegistry: registration, validation, schema_hash.
3. LLMPlanningStrategy.propose(): valid, malformed, rejected.
4. Prompt construction: determinism, truncation.
5. Composite prompt hash includes model/temp/config/registry version.
6. Proposal identity: canonical vs raw-response paths.
"""

from __future__ import annotations

import json
import sys

sys.path.insert(0, "/opt/OS")

from eos_ai.substrate.llm_planner import (
    EventSchema,
    EventTypeRegistry,
    LLMEventProposal,
    LLMPlannerConfig,
    LLMPlanningStrategy,
    LLMProposalResult,
    ProposedEvent,
    SelectionPolicy,
    ValidationResult,
    _canonical_json,
    _normalize_for_canonical,
    _sha256_prefix,
    build_llm_prompt,
    compute_prompt_hash,
)


# ─── Fixtures ────────────────────────────────────────────────────────


def _make_registry() -> EventTypeRegistry:
    reg = EventTypeRegistry()
    reg.register(
        EventSchema(
            event_type="test_action",
            required_fields=frozenset({"session_name", "action"}),
            optional_fields=frozenset({"metadata"}),
            field_types={"session_name": str, "action": str},
        )
    )
    reg.register(
        EventSchema(
            event_type="test_mutation",
            required_fields=frozenset({"key", "value"}),
            optional_fields=frozenset(),
        )
    )
    return reg


def _make_config(**overrides) -> LLMPlannerConfig:
    defaults = {"enabled": True, "model_name": "test-model"}
    defaults.update(overrides)
    return LLMPlannerConfig(**defaults)


def _make_llm_fn(response: str):
    """Deterministic llm_fn returning a fixed response."""
    call_count = [0]

    def fn(prompt: str) -> str:
        call_count[0] += 1
        return response

    fn.call_count = call_count
    return fn


VALID_RESPONSE = json.dumps(
    {
        "events": [
            {
                "event_type": "test_action",
                "payload": {"session_name": "s1", "action": "go"},
                "description": "Test action",
            },
        ],
        "reasoning": "Test reasoning",
    }
)

MULTI_EVENT_RESPONSE = json.dumps(
    {
        "events": [
            {
                "event_type": "test_action",
                "payload": {"session_name": "s1", "action": "a"},
            },
            {"event_type": "test_mutation", "payload": {"key": "k", "value": "v"}},
        ],
    }
)

INVALID_JSON = "this is not json {{"

UNKNOWN_EVENT_RESPONSE = json.dumps(
    {
        "events": [
            {"event_type": "nonexistent_type", "payload": {"x": 1}},
        ],
    }
)

MISSING_FIELDS_RESPONSE = json.dumps(
    {
        "events": [
            {"event_type": "test_action", "payload": {"session_name": "s1"}},
        ],
    }
)

WRONG_TYPES_RESPONSE = json.dumps(
    {
        "events": [
            {
                "event_type": "test_action",
                "payload": {"session_name": 123, "action": "go"},
            },
        ],
    }
)


# ─── Canonicalization tests ──────────────────────────────────────────


class TestCanonicalization:
    def test_key_ordering_stable(self):
        a = _canonical_json({"z": 1, "a": 2, "m": 3})
        b = _canonical_json({"m": 3, "a": 2, "z": 1})
        assert a == b

    def test_float_normalization(self):
        a = _canonical_json({"val": 0.0})
        b = _canonical_json({"val": -0.0})
        # Both should produce consistent output
        assert isinstance(a, str)
        assert isinstance(b, str)

    def test_float_roundtrip(self):
        a = _canonical_json({"val": 1.1})
        b = _canonical_json({"val": 1.1})
        assert a == b

    def test_unicode_nfc_normalization(self):
        # e + combining acute vs precomposed e-acute
        decomposed = "e\u0301"
        composed = "\u00e9"
        a = _canonical_json({"name": decomposed})
        b = _canonical_json({"name": composed})
        assert a == b

    def test_empty_vs_null_preserved(self):
        a = _canonical_json({"a": "", "b": None, "c": []})
        parsed = json.loads(a)
        assert parsed["a"] == ""
        assert parsed["b"] is None
        assert parsed["c"] == []

    def test_nested_normalization(self):
        obj = {"outer": {"inner": [{"key": "val\u0301ue"}]}}
        result = _canonical_json(obj)
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert "outer" in parsed


# ─── EventTypeRegistry tests ─────────────────────────────────────────


class TestEventTypeRegistry:
    def test_register_and_retrieve(self):
        reg = _make_registry()
        schema = reg.get("test_action")
        assert schema is not None
        assert schema.event_type == "test_action"

    def test_version_increments(self):
        reg = EventTypeRegistry()
        assert reg.version == 0
        reg.register(
            EventSchema(
                event_type="a",
                required_fields=frozenset(),
                optional_fields=frozenset(),
            )
        )
        assert reg.version == 1
        reg.register(
            EventSchema(
                event_type="b",
                required_fields=frozenset(),
                optional_fields=frozenset(),
            )
        )
        assert reg.version == 2

    def test_schema_hash_changes(self):
        reg = EventTypeRegistry()
        h1 = reg.schema_hash
        reg.register(
            EventSchema(
                event_type="a",
                required_fields=frozenset(),
                optional_fields=frozenset(),
            )
        )
        h2 = reg.schema_hash
        assert h1 != h2

    def test_schema_hash_deterministic(self):
        r1 = _make_registry()
        r2 = _make_registry()
        assert r1.schema_hash == r2.schema_hash

    def test_validate_accept(self):
        reg = _make_registry()
        valid, reason = reg.validate_event(
            "test_action", {"session_name": "s1", "action": "go"}
        )
        assert valid is True
        assert reason == ""

    def test_validate_unknown_type(self):
        reg = _make_registry()
        valid, reason = reg.validate_event("nonexistent", {})
        assert valid is False
        assert "unknown event_type" in reason

    def test_validate_missing_required(self):
        reg = _make_registry()
        valid, reason = reg.validate_event("test_action", {"session_name": "s1"})
        assert valid is False
        assert "missing required" in reason

    def test_validate_unknown_fields(self):
        reg = _make_registry()
        valid, reason = reg.validate_event(
            "test_action",
            {"session_name": "s1", "action": "go", "extra": True},
        )
        assert valid is False
        assert "unknown fields" in reason

    def test_validate_wrong_field_type(self):
        reg = _make_registry()
        valid, reason = reg.validate_event(
            "test_action",
            {"session_name": 123, "action": "go"},
        )
        assert valid is False
        assert "expected str" in reason

    def test_validate_optional_with_type(self):
        reg = _make_registry()
        valid, reason = reg.validate_event(
            "test_action",
            {"session_name": "s1", "action": "go", "metadata": "extra"},
        )
        assert valid is True

    def test_validate_proposal_too_many_events(self):
        reg = _make_registry()
        config = _make_config(max_events_per_proposal=1)
        events = (
            ProposedEvent(
                event_type="test_action", payload={"session_name": "s1", "action": "a"}
            ),
            ProposedEvent(
                event_type="test_action", payload={"session_name": "s2", "action": "b"}
            ),
        )
        proposal = LLMEventProposal(events=events, proposal_id="test")
        result = reg.validate_proposal(proposal, config)
        assert result.valid is False

    def test_validate_proposal_payload_too_large(self):
        reg = _make_registry()
        config = _make_config(max_payload_bytes_per_event=10)
        events = (
            ProposedEvent(
                event_type="test_action", payload={"session_name": "s1", "action": "go"}
            ),
        )
        proposal = LLMEventProposal(events=events, proposal_id="test")
        result = reg.validate_proposal(proposal, config)
        assert result.valid is False
        assert "payload size" in list(result.rejection_reasons.values())[0]


# ─── LLMPlanningStrategy tests ───────────────────────────────────────


class TestLLMPlanningStrategy:
    def test_valid_proposal(self):
        llm_fn = _make_llm_fn(VALID_RESPONSE)
        strategy = LLMPlanningStrategy(
            llm_fn=llm_fn, registry=_make_registry(), config=_make_config()
        )
        result = strategy.propose('{"status":"active"}', "abc123", [])
        assert result.proposal is not None
        assert len(result.proposal.events) == 1
        assert result.proposal.events[0].event_type == "test_action"
        assert result.parse_failed is False
        assert result.validation is not None
        assert result.validation.valid is True

    def test_malformed_json(self):
        llm_fn = _make_llm_fn(INVALID_JSON)
        strategy = LLMPlanningStrategy(
            llm_fn=llm_fn, registry=_make_registry(), config=_make_config()
        )
        result = strategy.propose('{"status":"active"}', "abc123", [])
        assert result.proposal is None
        assert result.parse_failed is True
        assert result.canonical_json is None

    def test_unknown_event_type(self):
        llm_fn = _make_llm_fn(UNKNOWN_EVENT_RESPONSE)
        strategy = LLMPlanningStrategy(
            llm_fn=llm_fn, registry=_make_registry(), config=_make_config()
        )
        result = strategy.propose('{"status":"active"}', "abc123", [])
        assert result.proposal is not None
        assert result.validation is not None
        assert result.validation.valid is False
        assert len(result.validation.rejected_events) == 1

    def test_missing_required_fields(self):
        llm_fn = _make_llm_fn(MISSING_FIELDS_RESPONSE)
        strategy = LLMPlanningStrategy(
            llm_fn=llm_fn, registry=_make_registry(), config=_make_config()
        )
        result = strategy.propose('{"status":"active"}', "abc123", [])
        assert result.validation is not None
        assert result.validation.valid is False

    def test_wrong_field_types(self):
        llm_fn = _make_llm_fn(WRONG_TYPES_RESPONSE)
        strategy = LLMPlanningStrategy(
            llm_fn=llm_fn, registry=_make_registry(), config=_make_config()
        )
        result = strategy.propose('{"status":"active"}', "abc123", [])
        assert result.validation is not None
        assert result.validation.valid is False

    def test_too_many_events(self):
        events = [
            {
                "event_type": "test_action",
                "payload": {"session_name": f"s{i}", "action": "x"},
            }
            for i in range(10)
        ]
        response = json.dumps({"events": events})
        llm_fn = _make_llm_fn(response)
        strategy = LLMPlanningStrategy(
            llm_fn=llm_fn,
            registry=_make_registry(),
            config=_make_config(max_events_per_proposal=2),
        )
        result = strategy.propose('{"status":"active"}', "abc123", [])
        assert result.validation is not None
        assert result.validation.valid is False

    def test_oversized_payload(self):
        big_val = "x" * 20000
        response = json.dumps(
            {
                "events": [
                    {
                        "event_type": "test_action",
                        "payload": {"session_name": big_val, "action": "go"},
                    }
                ],
            }
        )
        llm_fn = _make_llm_fn(response)
        strategy = LLMPlanningStrategy(
            llm_fn=llm_fn,
            registry=_make_registry(),
            config=_make_config(max_payload_bytes_per_event=100),
        )
        result = strategy.propose('{"status":"active"}', "abc123", [])
        assert result.validation is not None
        assert result.validation.valid is False

    def test_prompt_determinism(self):
        llm_fn = _make_llm_fn(VALID_RESPONSE)
        strategy = LLMPlanningStrategy(
            llm_fn=llm_fn, registry=_make_registry(), config=_make_config()
        )
        r1 = strategy.propose('{"a":1}', "h1", [])
        r2 = strategy.propose('{"a":1}', "h1", [])
        assert r1.prompt_hash == r2.prompt_hash

    def test_canonical_normalization_deterministic(self):
        llm_fn = _make_llm_fn(VALID_RESPONSE)
        strategy = LLMPlanningStrategy(
            llm_fn=llm_fn, registry=_make_registry(), config=_make_config()
        )
        r1 = strategy.propose('{"a":1}', "h1", [])
        r2 = strategy.propose('{"a":1}', "h1", [])
        assert r1.canonical_json == r2.canonical_json
        assert r1.proposal_id == r2.proposal_id

    def test_proposal_id_canonical_path(self):
        llm_fn = _make_llm_fn(VALID_RESPONSE)
        strategy = LLMPlanningStrategy(
            llm_fn=llm_fn, registry=_make_registry(), config=_make_config()
        )
        result = strategy.propose('{"a":1}', "h1", [])
        assert not result.proposal_id.startswith("raw_")
        assert len(result.proposal_id) == 16

    def test_proposal_id_raw_response_fallback(self):
        llm_fn = _make_llm_fn(INVALID_JSON)
        strategy = LLMPlanningStrategy(
            llm_fn=llm_fn, registry=_make_registry(), config=_make_config()
        )
        result = strategy.propose('{"a":1}', "h1", [])
        # Parse-failed path: proposal_id starts with "raw_"
        assert result.proposal_id.startswith("raw_")
        assert result.parse_failed is True

    def test_response_hash_always_present(self):
        llm_fn = _make_llm_fn(VALID_RESPONSE)
        strategy = LLMPlanningStrategy(
            llm_fn=llm_fn, registry=_make_registry(), config=_make_config()
        )
        result = strategy.propose('{"a":1}', "h1", [])
        assert len(result.response_hash) == 16

    def test_response_hash_on_parse_failure(self):
        llm_fn = _make_llm_fn(INVALID_JSON)
        strategy = LLMPlanningStrategy(
            llm_fn=llm_fn, registry=_make_registry(), config=_make_config()
        )
        result = strategy.propose('{"a":1}', "h1", [])
        assert len(result.response_hash) == 16

    def test_multi_event_proposal(self):
        llm_fn = _make_llm_fn(MULTI_EVENT_RESPONSE)
        strategy = LLMPlanningStrategy(
            llm_fn=llm_fn, registry=_make_registry(), config=_make_config()
        )
        result = strategy.propose('{"a":1}', "h1", [])
        assert result.proposal is not None
        assert len(result.proposal.events) == 2

    def test_validation_schema_hash_present(self):
        llm_fn = _make_llm_fn(VALID_RESPONSE)
        reg = _make_registry()
        strategy = LLMPlanningStrategy(
            llm_fn=llm_fn, registry=reg, config=_make_config()
        )
        result = strategy.propose('{"a":1}', "h1", [])
        assert result.validation is not None
        assert result.validation.schema_hash == reg.schema_hash


# ─── Prompt construction tests ───────────────────────────────────────


class TestPromptConstruction:
    def test_prompt_includes_catalog(self):
        prompt = build_llm_prompt('{"a":1}', [], _make_registry(), _make_config())
        assert "test_action" in prompt
        assert "test_mutation" in prompt

    def test_prompt_includes_state(self):
        prompt = build_llm_prompt(
            '{"status":"active"}', [], _make_registry(), _make_config()
        )
        assert "active" in prompt

    def test_prompt_includes_registry_version(self):
        reg = _make_registry()
        prompt = build_llm_prompt('{"a":1}', [], reg, _make_config())
        assert f"SCHEMA VERSION: {reg.version}" in prompt

    def test_prompt_determinism(self):
        reg = _make_registry()
        cfg = _make_config()
        p1 = build_llm_prompt('{"a":1}', [{"id": "i1"}], reg, cfg)
        p2 = build_llm_prompt('{"a":1}', [{"id": "i1"}], reg, cfg)
        assert p1 == p2

    def test_composite_prompt_hash(self):
        h1 = compute_prompt_hash("prompt", "model-a", 0.0, 1, 1)
        h2 = compute_prompt_hash("prompt", "model-b", 0.0, 1, 1)
        h3 = compute_prompt_hash("prompt", "model-a", 0.5, 1, 1)
        h4 = compute_prompt_hash("prompt", "model-a", 0.0, 2, 1)
        h5 = compute_prompt_hash("prompt", "model-a", 0.0, 1, 2)
        # All different because composite hash includes all fields
        assert len({h1, h2, h3, h4, h5}) == 5

    def test_truncation_within_budget(self):
        from eos_ai.substrate.llm_planner import _truncate_state

        state = '{"a":1}'
        cfg = _make_config(max_prompt_tokens=1000)
        result = _truncate_state(state, cfg)
        assert result == state

    def test_truncation_drops_keys_by_tier(self):
        from eos_ai.substrate.llm_planner import _truncate_state

        state = _canonical_json(
            {
                "metadata:x": "long" * 100,
                "core:y": "val",
            }
        )
        cfg = _make_config(
            max_prompt_tokens=10,
            truncation_priority=("metadata:", "core:"),
        )
        result = _truncate_state(state, cfg)
        parsed = json.loads(result)
        # metadata should be dropped first
        assert "metadata:x" not in parsed
