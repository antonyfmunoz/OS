"""Tests for W0-001R doc CU vs API comparator module."""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from runtime.substrate.doc_cu_vs_api_comparator import (
    DocComparisonResult,
    METHOD_SEPARATION_STATEMENT,
    compare_doc_extraction,
    compute_phrase_recall,
    extract_unique_phrases,
    normalize_text,
)


class TestNormalizeText:
    def test_lowercases(self) -> None:
        assert normalize_text("Hello World") == "hello world"

    def test_collapses_whitespace(self) -> None:
        assert normalize_text("a  b   c") == "a b c"

    def test_removes_punctuation(self) -> None:
        assert normalize_text("hello, world!") == "hello world"

    def test_strips(self) -> None:
        assert normalize_text("  hello  ") == "hello"


class TestExtractUniquePhrases:
    def test_extracts_phrases(self) -> None:
        text = "one two three four five six seven eight nine ten"
        phrases = extract_unique_phrases(text, phrase_length=3)
        assert len(phrases) > 0
        assert all(len(p.split()) == 3 for p in phrases)

    def test_short_text_returns_single_phrase(self) -> None:
        phrases = extract_unique_phrases("hello world", phrase_length=5)
        assert len(phrases) == 1
        assert phrases[0] == "hello world"

    def test_empty_text(self) -> None:
        assert extract_unique_phrases("", phrase_length=5) == []

    def test_unique_only(self) -> None:
        text = "a b c d e a b c d e a b c d e"
        phrases = extract_unique_phrases(text, phrase_length=5)
        assert len(set(phrases)) == len(phrases)


class TestComputePhraseRecall:
    def test_identical_text(self) -> None:
        text = "the quick brown fox jumps over the lazy dog again and again"
        found, total = compute_phrase_recall(text, text)
        assert found == total
        assert total > 0

    def test_no_overlap(self) -> None:
        api = "the quick brown fox jumps over the lazy dog"
        cu = "completely different text with no matching words whatsoever here"
        found, total = compute_phrase_recall(api, cu)
        assert found == 0

    def test_partial_overlap(self) -> None:
        api = "the quick brown fox jumps over the lazy dog and more words"
        cu = "the quick brown fox jumps"
        found, total = compute_phrase_recall(api, cu, phrase_length=3)
        assert 0 < found < total


class TestCompareDocExtraction:
    def test_high_match(self) -> None:
        api_text = "Universal Meta Harness is a stateful event-driven control-plane intelligence runtime"
        cu_text = "Universal Meta Harness is a stateful event-driven control-plane intelligence runtime"
        result = compare_doc_extraction("id1", "UMH", api_text, 1, cu_text, 1)
        assert result.word_recall == 1.0
        assert result.confidence == "HIGH"
        assert result.phrase_recall == 1.0

    def test_low_match(self) -> None:
        api_text = "This is a very long document with many important words and sentences about various topics"
        cu_text = "short"
        result = compare_doc_extraction("id2", "Test", api_text, 8, cu_text, 1)
        assert result.word_recall < 0.5
        assert result.tab_coverage == 0.125

    def test_to_dict(self) -> None:
        result = compare_doc_extraction("id", "T", "hello world test", 1, "hello world test", 1)
        d = result.to_dict()
        assert d["file_id"] == "id"
        assert "method_separation" in d

    def test_method_separation_statement_exists(self) -> None:
        assert "Production" in METHOD_SEPARATION_STATEMENT
        assert "Computer-use" in METHOD_SEPARATION_STATEMENT
        assert "API" in METHOD_SEPARATION_STATEMENT


class TestDocComparisonResult:
    def test_dataclass_fields(self) -> None:
        r = DocComparisonResult(
            file_id="id",
            title="Test",
            api_total_words=100,
            api_total_tabs=3,
            cu_total_words=50,
            cu_tabs_read=1,
            word_recall=0.5,
            tab_coverage=0.333,
            unique_api_phrases_found_in_cu=5,
            total_api_phrases_checked=10,
            phrase_recall=0.5,
            confidence="MEDIUM",
            method_separation="test",
        )
        assert r.word_recall == 0.5
        assert r.confidence == "MEDIUM"
