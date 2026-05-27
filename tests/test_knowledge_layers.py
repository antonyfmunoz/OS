import os
"""Tests for knowledge layers 6-17 behavioral distillation engine."""

import sys

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

from substrate.understanding.knowledge.knowledge_layers import (
    KnowledgeLayer,
    KnowledgeLayerEngine,
    LAYERS,
)


class TestLayerDefinitions:
    def test_layer_count(self):
        assert len(LAYERS) == 12

    def test_layer_ids_are_6_through_17(self):
        ids = sorted(l.layer_id for l in LAYERS.values())
        assert ids == list(range(6, 18))

    def test_all_layers_have_principles(self):
        for key, layer in LAYERS.items():
            assert len(layer.principles) > 0, f"{key} has no principles"

    def test_all_layers_have_triggers(self):
        for key, layer in LAYERS.items():
            assert len(layer.triggers) > 0, f"{key} has no triggers"

    def test_all_layers_have_applies_to(self):
        for key, layer in LAYERS.items():
            assert len(layer.applies_to) > 0, f"{key} has no applies_to"

    def test_total_principles(self):
        total = sum(len(l.principles) for l in LAYERS.values())
        assert total >= 100


class TestKnowledgeLayerEngine:
    def setup_method(self):
        self.engine = KnowledgeLayerEngine()

    def test_layer_count_property(self):
        assert self.engine.layer_count == 12

    def test_principle_count_property(self):
        assert self.engine.principle_count >= 100

    def test_get_relevant_layers_negotiation(self):
        layers = self.engine.get_relevant_layers("I need to negotiate this deal")
        assert len(layers) > 0
        keys = [l.key for l in layers]
        assert "NEGOTIATION" in keys

    def test_get_relevant_layers_crisis(self):
        layers = self.engine.get_relevant_layers("We have an emergency outage")
        assert len(layers) > 0
        keys = [l.key for l in layers]
        assert "CRISIS" in keys

    def test_get_relevant_layers_no_match(self):
        layers = self.engine.get_relevant_layers("hello world")
        assert len(layers) == 0

    def test_department_boost(self):
        layers_no_dept = self.engine.get_relevant_layers("Let's discuss the team structure")
        layers_with_dept = self.engine.get_relevant_layers(
            "Let's discuss the team structure", department="hr"
        )
        hr_in_no_dept = any(l.key == "ORGANIZATIONAL_DESIGN" for l in layers_no_dept)
        hr_in_dept = any(l.key == "ORGANIZATIONAL_DESIGN" for l in layers_with_dept)
        if hr_in_no_dept and hr_in_dept:
            pass
        elif hr_in_dept and not hr_in_no_dept:
            pass
        else:
            assert hr_in_dept, "ORGANIZATIONAL_DESIGN should appear with hr department"

    def test_top_n_limits_results(self):
        layers = self.engine.get_relevant_layers(
            "negotiate deal contract pricing terms agreement", top_n=1
        )
        assert len(layers) <= 1

    def test_get_relevant_layer_single(self):
        layer = self.engine.get_relevant_layer("We need to negotiate the contract")
        assert layer is not None
        assert layer.key == "NEGOTIATION"

    def test_get_relevant_layer_none(self):
        layer = self.engine.get_relevant_layer("hello world")
        assert layer is None

    def test_format_for_injection_empty(self):
        result = self.engine.format_for_injection([])
        assert result == ""

    def test_format_for_injection_content(self):
        layers = self.engine.get_relevant_layers("negotiate this deal", top_n=1)
        result = self.engine.format_for_injection(layers)
        assert "[Negotiation Mastery]" in result
        assert "BATNA" in result

    def test_inject_combines_find_and_format(self):
        result = self.engine.inject("emergency crisis failure", department="operations")
        assert len(result) > 0
        assert "Crisis Management" in result

    def test_inject_no_match(self):
        result = self.engine.inject("hello world")
        assert result == ""

    def test_get_layer_by_key(self):
        layer = self.engine.get_layer("CRISIS")
        assert layer is not None
        assert layer.name == "Crisis Management"

    def test_get_layer_missing_key(self):
        layer = self.engine.get_layer("NONEXISTENT")
        assert layer is None

    def test_all_layers_api(self):
        layers = self.engine.all_layers()
        assert len(layers) == 12
        assert all("layer_id" in l for l in layers)
        assert all("principle_count" in l for l in layers)

    def test_principles_capped_at_5_in_injection(self):
        layers = self.engine.get_relevant_layers("negotiate deal", top_n=1)
        result = self.engine.format_for_injection(layers)
        lines = [l for l in result.strip().split("\n") if l.strip().startswith("- ")]
        assert len(lines) <= 5


class TestUnifiedContextIntegration:
    def test_behavioral_layers_field_exists(self):
        from substrate.control_plane.context.context_builder import UnifiedContext

        uc = UnifiedContext()
        assert hasattr(uc, "behavioral_layers")
        assert uc.behavioral_layers is None

    def test_behavioral_layers_in_system_prompt(self):
        from substrate.control_plane.context.context_builder import UnifiedContext

        uc = UnifiedContext()
        uc.behavioral_layers = "Behavioral context:\n[Crisis Management]\n  - First: stop the bleeding"
        prompt = uc.to_system_prompt()
        assert "Crisis Management" in prompt
        assert "stop the bleeding" in prompt
