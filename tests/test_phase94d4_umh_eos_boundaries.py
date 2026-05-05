"""Tests for Phase 94D.4 UMH/EOS boundary enforcement."""

import sys

sys.path.insert(0, "/opt/OS")

import pytest

from eos_ai.substrate.substrate_projection_boundaries import (
    BoundaryClassification,
    ComponentBoundary,
    EOS_PROJECTION_TERMS,
    PROJECTION_TERMS,
    UMH_SUBSTRATE_TERMS,
    classify_component_boundary,
    detect_umh_eos_confusion,
    validate_boundary_statement,
)


class TestComponentClassification:
    def test_substrate_path_classified_as_umh(self):
        result = classify_component_boundary("MessageBus", path="eos_ai/substrate/message_bus.py")
        assert result.boundary == ComponentBoundary.UMH_SUBSTRATE

    def test_saas_path_classified_as_projection(self):
        result = classify_component_boundary("Dashboard", path="saas/components/Dashboard.tsx")
        assert result.boundary == ComponentBoundary.PROJECTION

    def test_discord_service_classified_as_projection(self):
        result = classify_component_boundary("DiscordBot", path="services/discord_bot.py")
        assert result.boundary == ComponentBoundary.PROJECTION

    def test_substrate_term_in_name(self):
        result = classify_component_boundary("governance engine module")
        assert result.boundary == ComponentBoundary.UMH_SUBSTRATE

    def test_eos_term_in_name(self):
        result = classify_component_boundary("entrepreneuros_dashboard")
        assert result.boundary == ComponentBoundary.PROJECTION

    def test_projection_term_in_name(self):
        result = classify_component_boundary("lyfeos_user_profile")
        assert result.boundary == ComponentBoundary.PROJECTION

    def test_ambiguous_returns_ambiguous(self):
        result = classify_component_boundary("utility_helper")
        assert result.boundary == ComponentBoundary.AMBIGUOUS

    def test_classification_returns_reason(self):
        result = classify_component_boundary("CognitiveLoop", path="eos_ai/substrate/loop.py")
        assert result.reason != ""


class TestConfusionDetection:
    def test_detects_eos_is_substrate(self):
        warnings = detect_umh_eos_confusion("EOS is the substrate layer")
        assert len(warnings) > 0
        assert "projection" in warnings[0].lower()

    def test_detects_eos_powers_umh(self):
        warnings = detect_umh_eos_confusion("EOS powers UMH")
        assert len(warnings) > 0
        assert "umh powers" in warnings[0].lower()

    def test_no_confusion_in_valid_statement(self):
        warnings = detect_umh_eos_confusion("EOS is powered by UMH substrate")
        assert len(warnings) == 0

    def test_detects_entrepreneuros_is_substrate(self):
        warnings = detect_umh_eos_confusion("EntrepreneurOS is the substrate")
        assert len(warnings) > 0

    def test_case_insensitive(self):
        warnings = detect_umh_eos_confusion("eos IS THE SUBSTRATE")
        assert len(warnings) > 0


class TestBoundaryValidation:
    def test_valid_eos_powered_by_umh(self):
        assert validate_boundary_statement("EOS is powered by UMH") is True

    def test_valid_eos_is_projection(self):
        assert validate_boundary_statement("EOS is a projection") is True

    def test_valid_umh_is_substrate(self):
        assert validate_boundary_statement("UMH is the substrate") is True

    def test_invalid_eos_is_substrate(self):
        assert validate_boundary_statement("EOS is the substrate") is False

    def test_invalid_eos_powers_umh(self):
        assert validate_boundary_statement("EOS powers UMH") is False

    def test_neutral_statement_is_valid(self):
        assert validate_boundary_statement("The weather is nice today") is True

    def test_lyfeos_is_projection_valid(self):
        assert validate_boundary_statement("LyfeOS is a projection") is True


class TestTermSets:
    def test_umh_terms_not_empty(self):
        assert len(UMH_SUBSTRATE_TERMS) > 0

    def test_eos_terms_not_empty(self):
        assert len(EOS_PROJECTION_TERMS) > 0

    def test_projection_terms_not_empty(self):
        assert len(PROJECTION_TERMS) > 0

    def test_no_overlap_between_umh_and_eos(self):
        overlap = UMH_SUBSTRATE_TERMS & EOS_PROJECTION_TERMS
        assert overlap == frozenset(), f"Overlap found: {overlap}"

    def test_no_overlap_between_umh_and_projections(self):
        overlap = UMH_SUBSTRATE_TERMS & PROJECTION_TERMS
        assert overlap == frozenset(), f"Overlap found: {overlap}"
