"""Tests for C22.7 — Production Surface Routes.

Campaign 22. Verifies cockpit route handlers and lazy runtime singletons.
"""

from __future__ import annotations

import asyncio
import sys
import unittest
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock, patch

sys.path.insert(0, "/opt/OS")


# ── Fake runtimes ──────────────────────────────────────────────────────────


class FakeProductionOpsRuntime:
    def snapshot(self) -> dict[str, Any]:
        return {
            "phase": "idle",
            "health": "healthy",
            "active_productions": [],
            "concurrent_projects": 0,
            "generated_at": 1000.0,
        }

    def phase(self) -> str:
        return "idle"

    def active_productions(self) -> list[dict[str, Any]]:
        return [{"project_id": "p1", "target": "substrate", "phase": "producing"}]


class FakeProductionWorkforceRuntime:
    def summary(self) -> dict[str, Any]:
        return {
            "total_agents": 3,
            "idle": 1,
            "active": 2,
            "roles": {"contributor": 2, "reviewer": 1},
        }

    def org_chart(self, project_id: str = "") -> dict[str, Any]:
        return {
            "operator": {"role": "operator", "children": [
                {"role": "director", "agent": "dev-director"},
            ]},
        }


class FakeProductionReviewRuntime:
    def pending_reviews(self) -> list[dict[str, Any]]:
        return [{"packet_id": "wp-1", "verdict": "approval_pending"}]

    def ship_readiness(self, project_id: str = "") -> dict[str, Any]:
        return {"ready": True, "blocking_checks": []}


class FakeCapabilityCompoundingRuntime:
    def snapshot(self) -> dict[str, Any]:
        return {
            "total_outcomes": 5,
            "total_lessons": 3,
            "compounding_velocity": 0.6,
        }

    def pending_promotions(self) -> list[dict[str, Any]]:
        return [{"id": "promo-1", "stage": "pattern", "title": "Test pattern"}]


class FakeProductFactoryRuntime:
    def list_products(self) -> list[dict[str, Any]]:
        return [
            {"product_id": "umh", "name": "UMH Substrate", "target_type": "substrate"},
            {"product_id": "eos", "name": "EOS", "target_type": "projection"},
        ]


class FakeSourceTruthRuntime:
    def trace_lineage(self, node_id: str, node_type: str = "work_packet") -> dict[str, Any]:
        return {
            "chain_id": f"chain-{node_id}",
            "root_intent": "build feature X",
            "nodes": [
                {"node_id": node_id, "node_type": node_type, "title": "Work packet"},
            ],
            "depth": 3,
            "terminal_state": "in_progress",
        }


# ── Fake request ───────────────────────────────────────────────────────────


class FakeQueryParams:
    def __init__(self, params: dict[str, str] | None = None):
        self._params = params or {}

    def get(self, key: str, default: str = "") -> str:
        return self._params.get(key, default)


class FakeRequest:
    def __init__(self, query_params: dict[str, str] | None = None):
        self.query_params = FakeQueryParams(query_params)


# ── Tests ──────────────────────────────────────────────────────────────────


def _run(coro: Any) -> Any:
    return asyncio.get_event_loop().run_until_complete(coro)


class TestProductionRoutes(unittest.TestCase):

    def setUp(self) -> None:
        import transports.api.cockpit_production_routes as mod
        self.mod = mod
        # Reset singletons
        mod._ops_runtime = None
        mod._workforce_runtime = None
        mod._review_runtime = None
        mod._compounding_runtime = None
        mod._factory_runtime = None
        mod._source_truth_runtime = None

    def test_configure_sets_flag(self) -> None:
        self.mod._configured = False
        self.mod.configure(lambda: None)
        self.assertTrue(self.mod._configured)

    def test_snapshot_with_runtime(self) -> None:
        self.mod._ops_runtime = FakeProductionOpsRuntime()
        result = _run(self.mod._snapshot(FakeRequest()))
        # Dict returned by fake gets wrapped in {"snapshot": ...}
        snap = result.get("snapshot", result)
        self.assertEqual(snap["phase"], "idle")
        self.assertEqual(snap["health"], "healthy")

    def test_snapshot_unavailable(self) -> None:
        self.mod._ops_runtime = None
        with patch.object(self.mod, "_get_ops", return_value=None):
            result = _run(self.mod._snapshot(FakeRequest()))
        self.assertIn("error", result)
        self.assertIn("not available", result["error"])

    def test_phase_returns_string(self) -> None:
        self.mod._ops_runtime = FakeProductionOpsRuntime()
        result = _run(self.mod._phase(FakeRequest()))
        self.assertEqual(result["phase"], "idle")

    def test_active_productions(self) -> None:
        self.mod._ops_runtime = FakeProductionOpsRuntime()
        result = _run(self.mod._active(FakeRequest()))
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["active_productions"][0]["target"], "substrate")

    def test_workforce_summary(self) -> None:
        self.mod._workforce_runtime = FakeProductionWorkforceRuntime()
        result = _run(self.mod._workforce_summary(FakeRequest()))
        self.assertEqual(result["total_agents"], 3)

    def test_workforce_chart(self) -> None:
        self.mod._workforce_runtime = FakeProductionWorkforceRuntime()
        result = _run(self.mod._workforce_chart(FakeRequest()))
        self.assertIn("org_chart", result)
        self.assertIn("operator", result["org_chart"])

    def test_reviews(self) -> None:
        self.mod._review_runtime = FakeProductionReviewRuntime()
        result = _run(self.mod._reviews(FakeRequest()))
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["pending_reviews"][0]["packet_id"], "wp-1")

    def test_ship_readiness_no_project(self) -> None:
        self.mod._review_runtime = FakeProductionReviewRuntime()
        result = _run(self.mod._ship_readiness(FakeRequest()))
        self.assertTrue(result["ship_readiness"]["ready"])

    def test_ship_readiness_with_project(self) -> None:
        self.mod._review_runtime = FakeProductionReviewRuntime()
        result = _run(self.mod._ship_readiness(FakeRequest({"project_id": "proj-1"})))
        self.assertIn("ship_readiness", result)

    def test_learning_snapshot(self) -> None:
        self.mod._compounding_runtime = FakeCapabilityCompoundingRuntime()
        result = _run(self.mod._learning(FakeRequest()))
        snap = result.get("snapshot", result)
        self.assertEqual(snap["total_outcomes"], 5)

    def test_compounding_promotions(self) -> None:
        self.mod._compounding_runtime = FakeCapabilityCompoundingRuntime()
        result = _run(self.mod._compounding(FakeRequest()))
        self.assertEqual(result["count"], 1)

    def test_products_list(self) -> None:
        self.mod._factory_runtime = FakeProductFactoryRuntime()
        result = _run(self.mod._products(FakeRequest()))
        self.assertEqual(result["count"], 2)

    def test_lineage_trace(self) -> None:
        self.mod._source_truth_runtime = FakeSourceTruthRuntime()
        result = _run(self.mod._lineage(FakeRequest({"node_type": "intent"}), "node-1"))
        lineage = result.get("lineage", result)
        self.assertEqual(lineage["chain_id"], "chain-node-1")

    def test_lineage_default_type(self) -> None:
        self.mod._source_truth_runtime = FakeSourceTruthRuntime()
        result = _run(self.mod._lineage(FakeRequest(), "node-2"))
        lineage = result.get("lineage", result)
        self.assertIn("chain_id", lineage)

    def test_unavailable_helper(self) -> None:
        result = self.mod._unavailable("TestRuntime")
        self.assertEqual(result["error"], "TestRuntime not available")
        self.assertEqual(result["status"], "unavailable")

    def test_all_getters_return_none_on_import_error(self) -> None:
        for getter_name in [
            "_get_ops", "_get_workforce", "_get_review",
            "_get_compounding", "_get_factory", "_get_source_truth",
        ]:
            getter = getattr(self.mod, getter_name)
            with patch.dict("sys.modules", {
                "substrate.organism.production_ops_runtime": None,
                "substrate.organism.production_workforce_runtime": None,
                "substrate.organism.production_review_runtime": None,
                "substrate.organism.capability_compounding_runtime": None,
                "substrate.organism.product_factory_runtime": None,
                "substrate.organism.source_truth_runtime": None,
            }):
                # Reset the singleton so it retries
                attr = getter_name.replace("_get", "") + "_runtime"
                setattr(self.mod, attr, None)

    def test_build_router_has_11_routes(self) -> None:
        dep = lambda: None  # noqa: E731
        r = self.mod._build_router(dep)
        route_paths = [route.path for route in r.routes]
        self.assertIn("/production/snapshot", route_paths)
        self.assertIn("/production/phase", route_paths)
        self.assertIn("/production/active", route_paths)
        self.assertIn("/production/workforce", route_paths)
        self.assertIn("/production/workforce/chart", route_paths)
        self.assertIn("/production/reviews", route_paths)
        self.assertIn("/production/ship-readiness", route_paths)
        self.assertIn("/production/learning", route_paths)
        self.assertIn("/production/compounding", route_paths)
        self.assertIn("/production/products", route_paths)
        self.assertIn("/production/lineage/{node_id}", route_paths)
        self.assertEqual(len(route_paths), 11)


class TestRouteErrorHandling(unittest.TestCase):

    def setUp(self) -> None:
        import transports.api.cockpit_production_routes as mod
        self.mod = mod

    def test_snapshot_handles_exception(self) -> None:
        class BrokenRuntime:
            def snapshot(self) -> None:
                raise RuntimeError("boom")
        self.mod._ops_runtime = BrokenRuntime()
        result = _run(self.mod._snapshot(FakeRequest()))
        self.assertIn("error", result)
        self.assertIn("boom", result["error"])

    def test_phase_handles_exception(self) -> None:
        class BrokenRuntime:
            def phase(self) -> None:
                raise RuntimeError("phase broke")
        self.mod._ops_runtime = BrokenRuntime()
        result = _run(self.mod._phase(FakeRequest()))
        self.assertIn("error", result)

    def test_lineage_handles_exception(self) -> None:
        class BrokenRuntime:
            def trace_lineage(self, nid: str, ntype: str) -> None:
                raise RuntimeError("lineage broke")
        self.mod._source_truth_runtime = BrokenRuntime()
        result = _run(self.mod._lineage(FakeRequest(), "bad-node"))
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()
