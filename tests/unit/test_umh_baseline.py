"""Baseline safety tests for UMH extraction refactor.

These tests verify that the three critical modules — execution_spine,
gateway, and context_builder — remain importable and their primary
public interfaces remain callable throughout the extraction.

Run: python3 -m pytest tests/test_umh_baseline.py -v
"""

import sys

sys.path.insert(0, "/opt/OS")


class TestExecutionSpineBaseline:
    def test_import(self):
        from umh.runtime_engine.execution_spine import ExecutionSpine

        assert ExecutionSpine is not None

    def test_spine_result_importable(self):
        from umh.runtime_engine.execution_spine import SpineResult

        assert SpineResult is not None

    def test_spine_result_is_str_subclass(self):
        from umh.runtime_engine.execution_spine import SpineResult

        assert issubclass(SpineResult, str)

    def test_spine_instantiable(self):
        from umh.runtime_engine.execution_spine import ExecutionSpine

        spine = ExecutionSpine.__new__(ExecutionSpine)
        assert hasattr(spine, "run")


class TestGatewayBaseline:
    def test_import(self):
        from umh.runtime_engine.gateway import EOSGateway

        assert EOSGateway is not None

    def test_gateway_instantiable(self):
        from umh.runtime_engine.gateway import EOSGateway

        assert hasattr(EOSGateway, "handle")


class TestContextBuilderBaseline:
    def test_import(self):
        from umh.runtime_engine.context_builder import ContextBuilder

        assert ContextBuilder is not None

    def test_builder_has_build(self):
        from umh.runtime_engine.context_builder import ContextBuilder

        assert hasattr(ContextBuilder, "build")


class TestCorePrimitivesBaseline:
    def test_import(self):
        from umh.primitives.ontological import PrimitiveTag, L0

        assert PrimitiveTag is not None
        assert L0 is not None

    def test_ten_primitives(self):
        from umh.primitives.ontological import PrimitiveTag

        assert len(PrimitiveTag) == 10

    def test_validate_callable(self):
        from umh.primitives.ontological import validate_primitive_set, PrimitiveTag

        result = validate_primitive_set({PrimitiveTag.STATE, PrimitiveTag.CHANGE})
        assert isinstance(result, list)


class TestWorldModelBaseline:
    def test_world_types_import(self):
        from umh.world.types import Entity, Relation, Observation

        assert Entity is not None
        assert Relation is not None
        assert Observation is not None

    def test_world_reasoning_import(self):
        from umh.world.reasoning import WorldReasoningEngine

        assert WorldReasoningEngine is not None

    def test_world_simulation_import(self):
        from umh.world.simulation import WorldSimulationEngine

        assert WorldSimulationEngine is not None

    def test_world_calibration_import(self):
        from umh.world.calibration import WorldCalibrationEngine

        assert WorldCalibrationEngine is not None

    def test_world_dynamics_adapter_import(self):
        from umh.world.dynamics_adapter import WorldDynamicsAdapter

        assert WorldDynamicsAdapter is not None

    def test_world_state_import(self):
        from umh.world.state import WorldStateEngine

        assert WorldStateEngine is not None

    def test_world_model_import(self):
        from umh.world.model import WorldModel, WorldModelEntry

        assert WorldModel is not None
        assert WorldModelEntry is not None
