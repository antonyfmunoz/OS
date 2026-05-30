"""Tests for substrate.understanding.knowledge.philosophy_lenses."""

from __future__ import annotations

from substrate.understanding.knowledge.philosophy_lenses import (
    LENSES,
    LensEngine,
    PhilosophyLens,
)


def test_lenses_count_is_16() -> None:
    assert len(LENSES) == 16


def test_all_lenses_have_unique_ids() -> None:
    ids = [lens.id for lens in LENSES]
    assert len(ids) == len(set(ids))


def test_all_lenses_have_unique_names() -> None:
    names = [lens.name for lens in LENSES]
    assert len(names) == len(set(names))


def test_all_lenses_have_trigger_keywords() -> None:
    for lens in LENSES:
        assert len(lens.trigger_keywords) > 0, f"Lens {lens.name} has no trigger keywords"


def test_all_lenses_have_application_question() -> None:
    for lens in LENSES:
        assert lens.application_question, f"Lens {lens.name} has no application question"


def test_all_lenses_have_description() -> None:
    for lens in LENSES:
        assert lens.description, f"Lens {lens.name} has no description"


def test_lens_ids_are_sequential() -> None:
    for i, lens in enumerate(LENSES):
        assert lens.id == i + 1, f"Lens {lens.name} has id {lens.id}, expected {i + 1}"


def test_match_returns_relevant_lenses() -> None:
    engine = LensEngine()
    results = engine.match("We need to find the root cause and reason from first principles")
    names = [r.name for r in results]
    assert "First principles" in names


def test_match_respects_top_n() -> None:
    engine = LensEngine()
    results = engine.match("system leverage constraint risk timing", top_n=2)
    assert len(results) <= 2


def test_match_returns_empty_for_no_keywords() -> None:
    engine = LensEngine()
    results = engine.match("xyzzy plugh")
    assert results == []


def test_apply_returns_formatted_question() -> None:
    engine = LensEngine()
    lens = LENSES[0]
    result = engine.apply(lens)
    assert result.startswith(f"[{lens.name}]")
    assert lens.application_question in result


def test_inject_returns_formatted_context() -> None:
    engine = LensEngine()
    result = engine.inject("We need to remove the bloat and simplify everything")
    assert "[Subtraction]" in result
    assert "->" in result


def test_inject_returns_empty_for_no_match() -> None:
    engine = LensEngine()
    result = engine.inject("xyzzy plugh")
    assert result == ""


def test_get_lens_by_id() -> None:
    engine = LensEngine()
    lens = engine.get_lens(1)
    assert lens is not None
    assert lens.name == "First principles"


def test_get_lens_by_id_returns_none_for_invalid() -> None:
    engine = LensEngine()
    assert engine.get_lens(999) is None


def test_get_lens_by_name() -> None:
    engine = LensEngine()
    lens = engine.get_lens_by_name("Leverage")
    assert lens is not None
    assert lens.id == 4


def test_get_lens_by_name_case_insensitive() -> None:
    engine = LensEngine()
    lens = engine.get_lens_by_name("TIMING")
    assert lens is not None
    assert lens.id == 7


def test_get_lens_by_name_returns_none_for_invalid() -> None:
    engine = LensEngine()
    assert engine.get_lens_by_name("nonexistent") is None


def test_all_lenses_returns_full_list() -> None:
    engine = LensEngine()
    assert len(engine.all_lenses()) == 16


def test_lens_count_property() -> None:
    engine = LensEngine()
    assert engine.lens_count == 16


def test_match_ranks_by_hit_count() -> None:
    engine = LensEngine()
    results = engine.match(
        "the system has downstream cascade consequences and ripple effects in the system"
    )
    assert results[0].name == "Systems thinking"


def test_inject_respects_top_n() -> None:
    engine = LensEngine()
    result = engine.inject("system leverage risk timing constraint", top_n=1)
    assert result.count("->") == 1


def test_philosophy_lens_dataclass_fields() -> None:
    lens = PhilosophyLens(
        id=99,
        name="Test",
        description="Test desc",
        trigger_keywords=["a", "b"],
        application_question="Test question?",
    )
    assert lens.id == 99
    assert lens.name == "Test"
    assert lens.description == "Test desc"
    assert lens.trigger_keywords == ["a", "b"]
    assert lens.application_question == "Test question?"
