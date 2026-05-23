"""Tests for Layer 3 Phase 2 Slice D: ActuatorMaturityLevel ↔ AdapterMaturityLevel bridge.

Covers forward mapping, reverse mapping, dict completeness,
and semantic correspondence between the two L0-L7 scales.
"""

import os
import sys
import unittest

sys.path.insert(
    0, os.environ.get("UMH_ROOT") or os.path.join(os.path.dirname(__file__), "..") or "/opt/OS"
)

from adapters.adapter_engine.adapter_manifest import AdapterMaturityLevel
from adapters.adapter_engine.adapter_maturity import (
    ACTUATOR_TO_ADAPTER,
    actuator_to_adapter_maturity,
    adapter_to_actuator_target,
)
from substrate.execution.actuation.actuator_maturity_v1 import ActuatorMaturityLevel


class TestActuatorToAdapterMapping(unittest.TestCase):
    def test_all_eight_levels_map(self):
        for act_level in ActuatorMaturityLevel:
            result = actuator_to_adapter_maturity(act_level)
            self.assertIsInstance(result, AdapterMaturityLevel)

    def test_l0_maps_to_l0(self):
        self.assertEqual(
            actuator_to_adapter_maturity(ActuatorMaturityLevel.L0_SIMULATED),
            AdapterMaturityLevel.L0_REGISTERED,
        )

    def test_l7_maps_to_l7(self):
        self.assertEqual(
            actuator_to_adapter_maturity(ActuatorMaturityLevel.L7_REPLAYABLE_ACTUATION),
            AdapterMaturityLevel.L7_MASTERFUL,
        )

    def test_intermediate_l3(self):
        self.assertEqual(
            actuator_to_adapter_maturity(ActuatorMaturityLevel.L3_FOREGROUND_FOCUSED),
            AdapterMaturityLevel.L3_TESTED,
        )

    def test_function_matches_dict(self):
        for act_level, expected in ACTUATOR_TO_ADAPTER.items():
            self.assertEqual(actuator_to_adapter_maturity(act_level), expected)


class TestAdapterToActuatorTarget(unittest.TestCase):
    def test_l0_reverse(self):
        self.assertEqual(
            adapter_to_actuator_target(AdapterMaturityLevel.L0_REGISTERED),
            ActuatorMaturityLevel.L0_SIMULATED,
        )

    def test_l5_reverse(self):
        self.assertEqual(
            adapter_to_actuator_target(AdapterMaturityLevel.L5_OPTIMIZED),
            ActuatorMaturityLevel.L5_SCREENSHOT_VERIFIED,
        )

    def test_round_trip_identity(self):
        for act_level in ActuatorMaturityLevel:
            adapter_level = actuator_to_adapter_maturity(act_level)
            back = adapter_to_actuator_target(adapter_level)
            self.assertEqual(back, act_level, f"Round-trip failed for {act_level.name}")


class TestMappingDictCompleteness(unittest.TestCase):
    def test_all_actuator_levels_present(self):
        for act_level in ActuatorMaturityLevel:
            self.assertIn(act_level, ACTUATOR_TO_ADAPTER, f"{act_level.name} missing from dict")

    def test_all_values_are_valid_adapter_levels(self):
        for act_level, adapter_level in ACTUATOR_TO_ADAPTER.items():
            self.assertIn(
                adapter_level,
                list(AdapterMaturityLevel),
                f"Value for {act_level.name} is not a valid AdapterMaturityLevel",
            )


class TestSemanticCorrespondence(unittest.TestCase):
    def test_int_values_match_positionally(self):
        for act_level in ActuatorMaturityLevel:
            adapter_level = ACTUATOR_TO_ADAPTER[act_level]
            self.assertEqual(
                act_level.value,
                adapter_level.value,
                f"{act_level.name} (value={act_level.value}) → "
                f"{adapter_level.name} (value={adapter_level.value}): "
                f"positional mapping broken",
            )

    def test_mapping_is_monotonic(self):
        prev_adapter = None
        for act_level in sorted(ActuatorMaturityLevel):
            adapter_level = ACTUATOR_TO_ADAPTER[act_level]
            if prev_adapter is not None:
                self.assertGreater(adapter_level, prev_adapter)
            prev_adapter = adapter_level

    def test_boundary_labels_correspond(self):
        self.assertEqual(
            ACTUATOR_TO_ADAPTER[ActuatorMaturityLevel.L1_PROCESS_STARTED],
            AdapterMaturityLevel.L1_CONNECTED,
        )
        self.assertEqual(
            ACTUATOR_TO_ADAPTER[ActuatorMaturityLevel.L5_SCREENSHOT_VERIFIED],
            AdapterMaturityLevel.L5_OPTIMIZED,
        )


if __name__ == "__main__":
    unittest.main()
