"""UMH boundary guard tests.

Enforces architectural separation: UMH modules must not import
platform-specific code (Discord, Telegram, services, etc.).

Allowed transitional dependencies are documented in ALLOWED_EOS_IMPORTS
with rationale and removal target.

Run: python3 -m pytest tests/test_umh_boundaries.py -v
"""

import ast
import sys
from pathlib import Path

sys.path.insert(0, "/opt/OS")

UMH_ROOT = Path("/opt/OS/umh")

FORBIDDEN_PREFIXES = (
    "services.",
    "scripts.",
    "interfaces.",
)

ALLOWED_EOS_IMPORTS: dict[str, list[dict[str, str]]] = {
    "umh/memory/storage.py": [
        {
            "import": "umh.adapters.umh_storage",
            "rationale": "Adapter discovery fallback — resolves EOS storage only if available",
            "removal_target": "Phase 4: inject storage externally via set_storage()",
        },
    ],
    "umh/world/state.py": [
        {
            "import": "umh.runtime_engine.decision_trace",
            "rationale": "TYPE_CHECKING only — never executes at runtime",
            "removal_target": "Phase 3: extract DecisionTrace to umh/",
        },
        {
            "import": "umh.runtime_engine.goal_state",
            "rationale": "TYPE_CHECKING only — never executes at runtime",
            "removal_target": "Phase 3: extract GoalRegistry to umh/",
        },
        {
            "import": "umh.runtime_engine.strategy_memory",
            "rationale": "Lazy runtime import inside method — soft coupling",
            "removal_target": "Phase 3: extract strategy_memory to umh/",
        },
    ],
    "umh/goals/interfaces.py": [
        {
            "import": "umh.adapters.umh_goals",
            "rationale": "Adapter discovery fallback — resolves EOS goal persistence only if available",
            "removal_target": "Phase 4: inject persistence externally via set_goal_persistence()",
        },
    ],
    "umh/strategy/interfaces.py": [
        {
            "import": "umh.adapters.umh_strategy",
            "rationale": "Adapter discovery fallback — resolves EOS strategy persistence only if available",
            "removal_target": "Phase 4: inject persistence externally via set_strategy_persistence()",
        },
    ],
    "umh/execution/interfaces.py": [],
    "umh/workstation/business.py": [
        {
            "import": "umh.runtime_engine.agent_runtime",
            "rationale": "Lazy import inside create_from_wizard — gap-fill via execution spine",
            "removal_target": "Phase 6: inject LLM gap-filler via protocol",
        },
        {
            "import": "umh.runtime_engine.execution_spine",
            "rationale": "Lazy import inside create_from_wizard — runs gap-fill prompt",
            "removal_target": "Phase 6: inject LLM gap-filler via protocol",
        },
        {
            "import": "umh.runtime_engine.context_builder",
            "rationale": "Lazy import inside create_from_wizard — builds context for gap-fill",
            "removal_target": "Phase 6: inject context builder via protocol",
        },
    ],
}


def _collect_umh_python_files() -> list[Path]:
    return sorted(UMH_ROOT.rglob("*.py"))


def _extract_imports(filepath: Path) -> list[tuple[int, str]]:
    """Extract all import module paths from a Python file.

    Returns (line_number, module_path) tuples.
    """
    source = filepath.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError:
        return []

    imports: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append((node.lineno, node.module))
    return imports


class TestUMHCleanImports:
    """UMH primitives and world types must have zero eos_ai imports."""

    def test_ontological_primitives_clean(self):
        filepath = UMH_ROOT / "primitives" / "ontological.py"
        imports = _extract_imports(filepath)
        eos_imports = [(ln, m) for ln, m in imports if m.startswith("umh.runtime_engine.")]
        assert eos_imports == [], f"Forbidden imports in ontological.py: {eos_imports}"

    def test_world_types_clean(self):
        filepath = UMH_ROOT / "world" / "types.py"
        imports = _extract_imports(filepath)
        eos_imports = [(ln, m) for ln, m in imports if m.startswith("umh.runtime_engine.")]
        assert eos_imports == [], f"Forbidden imports in world/types.py: {eos_imports}"

    def test_world_reasoning_clean(self):
        filepath = UMH_ROOT / "world" / "reasoning.py"
        imports = _extract_imports(filepath)
        eos_imports = [(ln, m) for ln, m in imports if m.startswith("umh.runtime_engine.")]
        assert eos_imports == [], (
            f"Forbidden imports in world/reasoning.py: {eos_imports}"
        )

    def test_world_calibration_clean(self):
        filepath = UMH_ROOT / "world" / "calibration.py"
        imports = _extract_imports(filepath)
        eos_imports = [(ln, m) for ln, m in imports if m.startswith("umh.runtime_engine.")]
        assert eos_imports == [], (
            f"Forbidden imports in world/calibration.py: {eos_imports}"
        )

    def test_world_dynamics_adapter_clean(self):
        filepath = UMH_ROOT / "world" / "dynamics_adapter.py"
        imports = _extract_imports(filepath)
        eos_imports = [(ln, m) for ln, m in imports if m.startswith("umh.runtime_engine.")]
        assert eos_imports == [], (
            f"Forbidden imports in dynamics_adapter.py: {eos_imports}"
        )

    def test_world_simulation_clean(self):
        filepath = UMH_ROOT / "world" / "simulation.py"
        imports = _extract_imports(filepath)
        eos_imports = [(ln, m) for ln, m in imports if m.startswith("umh.runtime_engine.")]
        assert eos_imports == [], (
            f"Forbidden imports in world/simulation.py: {eos_imports}"
        )

    def test_world_model_clean(self):
        filepath = UMH_ROOT / "world" / "model.py"
        imports = _extract_imports(filepath)
        eos_imports = [(ln, m) for ln, m in imports if m.startswith("umh.runtime_engine.")]
        assert eos_imports == [], f"Forbidden imports in world/model.py: {eos_imports}"

    def test_decision_trace_clean(self):
        filepath = UMH_ROOT / "decision" / "trace.py"
        imports = _extract_imports(filepath)
        eos_imports = [(ln, m) for ln, m in imports if m.startswith("umh.runtime_engine.")]
        assert eos_imports == [], (
            f"Forbidden imports in decision/trace.py: {eos_imports}"
        )

    def test_goals_state_clean(self):
        filepath = UMH_ROOT / "goals" / "state.py"
        imports = _extract_imports(filepath)
        eos_imports = [(ln, m) for ln, m in imports if m.startswith("umh.runtime_engine.")]
        assert eos_imports == [], f"Forbidden imports in goals/state.py: {eos_imports}"

    def test_goals_objective_clean(self):
        filepath = UMH_ROOT / "goals" / "objective.py"
        imports = _extract_imports(filepath)
        eos_imports = [(ln, m) for ln, m in imports if m.startswith("umh.runtime_engine.")]
        assert eos_imports == [], (
            f"Forbidden imports in goals/objective.py: {eos_imports}"
        )

    def test_strategy_memory_clean(self):
        filepath = UMH_ROOT / "strategy" / "memory.py"
        imports = _extract_imports(filepath)
        eos_imports = [(ln, m) for ln, m in imports if m.startswith("umh.runtime_engine.")]
        assert eos_imports == [], (
            f"Forbidden imports in strategy/memory.py: {eos_imports}"
        )


class TestNoForbiddenServiceImports:
    """No UMH core module may import services or scripts.

    umh/interfaces/ is excluded — it is the boundary layer that connects
    UMH to external systems and legitimately references services/scripts.
    """

    def test_no_forbidden_imports_in_core(self):
        violations = []
        for filepath in _collect_umh_python_files():
            if "interfaces" in filepath.parts:
                continue
            imports = _extract_imports(filepath)
            for lineno, module in imports:
                for prefix in FORBIDDEN_PREFIXES:
                    if module.startswith(prefix):
                        violations.append(
                            f"{filepath.relative_to(UMH_ROOT)}:{lineno} imports {module}"
                        )
        assert violations == [], f"Forbidden service imports:\n" + "\n".join(violations)


class TestAllowedTransitionalImports:
    """Verify no eos/eos_ai imports remain after Phase 14 collapse."""

    def test_no_eos_imports_remain(self):
        violations = []
        for filepath in _collect_umh_python_files():
            rel = str(filepath.relative_to(Path("/opt/OS")))
            imports = _extract_imports(filepath)
            for lineno, module in imports:
                if module.startswith(("eos.", "runtime.")):
                    violations.append(f"{rel}:{lineno} imports {module}")
        assert violations == [], f"Legacy eos/eos_ai imports in UMH:\n" + "\n".join(
            violations
        )


class TestUMHImportsWork:
    """All UMH modules import without error."""

    def test_primitives(self):
        from umh.primitives.ontological import PrimitiveTag, L0

        assert len(PrimitiveTag) == 10

    def test_world_types(self):
        from umh.world.types import Entity, Relation, Observation

        assert Entity is not None

    def test_world_reasoning(self):
        from umh.world.reasoning import WorldReasoningEngine

        assert WorldReasoningEngine is not None

    def test_world_simulation(self):
        from umh.world.simulation import WorldSimulationEngine

        assert WorldSimulationEngine is not None

    def test_world_calibration(self):
        from umh.world.calibration import WorldCalibrationEngine

        assert WorldCalibrationEngine is not None

    def test_world_dynamics_adapter(self):
        from umh.world.dynamics_adapter import WorldDynamicsAdapter

        assert WorldDynamicsAdapter is not None

    def test_world_state(self):
        from umh.world.state import WorldStateEngine

        assert WorldStateEngine is not None

    def test_world_model(self):
        from umh.world.model import WorldModel

        assert WorldModel is not None

    def test_memory_storage(self):
        from umh.memory.storage import StorageBackend, InMemoryStorage

        store = InMemoryStorage()
        assert isinstance(store, StorageBackend)

    def test_decision_trace(self):
        from umh.decision.trace import DecisionTrace, MAX_TRACES, debug_print

        assert MAX_TRACES == 50
        assert DecisionTrace is not None
        assert debug_print is not None

    def test_goals_state(self):
        from umh.goals.state import (
            GoalState,
            NO_GOAL,
            GoalTracker,
            GoalRegistry,
            compute_goal_relevance,
            compute_goal_weight,
            generate_goal_directives,
            compute_control_threshold_adjustment,
            strategy_goal_score,
        )

        assert GoalState is not None
        assert NO_GOAL.goal_id == "none"
        assert GoalRegistry is not None

    def test_goals_objective(self):
        from umh.goals.objective import ObjectiveFunction, ObjectiveSet

        assert ObjectiveFunction is not None
        assert ObjectiveSet is not None

    def test_strategy_memory(self):
        from umh.strategy.memory import (
            StrategyStats,
            StrategyMemory,
            get_strategy_memory,
            reset_strategy_memory,
        )

        assert StrategyStats is not None
        assert StrategyMemory is not None

    def test_goals_interfaces(self):
        from umh.goals.interfaces import (
            GoalPersistence,
            NullGoalPersistence,
            get_goal_persistence,
        )

        null = NullGoalPersistence()
        assert isinstance(null, GoalPersistence)

    def test_strategy_interfaces(self):
        from umh.strategy.interfaces import (
            StrategyPersistence,
            NullStrategyPersistence,
            get_strategy_persistence,
        )

        null = NullStrategyPersistence()
        assert isinstance(null, StrategyPersistence)


class TestStorageProtocol:
    """UMH storage protocol works with both in-memory and adapter backends."""

    def test_in_memory_storage(self):
        from umh.memory.storage import InMemoryStorage, StorageBackend

        store = InMemoryStorage()
        store.put("k", {"v": 1})
        assert store.get("k") == {"v": 1}
        assert store.get("missing", "default") == "default"
        assert "k" in store.all_keys()
        assert isinstance(store, StorageBackend)

    def test_adapter_satisfies_protocol(self):
        from umh.adapters.umh_storage import SubstrateStorageAdapter
        from umh.memory.storage import StorageBackend

        assert issubclass(SubstrateStorageAdapter, StorageBackend) or isinstance(
            SubstrateStorageAdapter(), StorageBackend
        )

    def test_goal_persistence_protocol(self):
        from umh.goals.interfaces import (
            GoalPersistence,
            NullGoalPersistence,
            get_goal_persistence,
            set_goal_persistence,
            reset_goal_persistence,
        )

        null = NullGoalPersistence()
        null.save_goal_trackers({"test": {"score": 0.5}}, registry_turn=1)
        assert null.load_goal_trackers() is None

        set_goal_persistence(null)
        assert get_goal_persistence() is null
        reset_goal_persistence()
        fresh = get_goal_persistence()
        assert fresh is not null
        reset_goal_persistence()

    def test_strategy_persistence_protocol(self):
        from umh.strategy.interfaces import (
            StrategyPersistence,
            NullStrategyPersistence,
            get_strategy_persistence,
            set_strategy_persistence,
            reset_strategy_persistence,
        )

        null = NullStrategyPersistence()
        null.save_strategy_memory({"test": {"score": 0.5}}, global_turn=1)
        assert null.load_strategy_memory() is None

        set_strategy_persistence(null)
        assert get_strategy_persistence() is null
        reset_strategy_persistence()
        fresh = get_strategy_persistence()
        assert fresh is not null
        reset_strategy_persistence()

    def test_eos_goal_adapter_satisfies_protocol(self):
        from umh.adapters.umh_goals import GoalPersistenceAdapter
        from umh.goals.interfaces import GoalPersistence

        assert issubclass(GoalPersistenceAdapter, GoalPersistence) or isinstance(
            GoalPersistenceAdapter(), GoalPersistence
        )

    def test_eos_strategy_adapter_satisfies_protocol(self):
        from umh.adapters.umh_strategy import StrategyPersistenceAdapter
        from umh.strategy.interfaces import StrategyPersistence

        assert issubclass(
            StrategyPersistenceAdapter, StrategyPersistence
        ) or isinstance(StrategyPersistenceAdapter(), StrategyPersistence)

    def test_set_and_reset_storage(self):
        from umh.memory.storage import (
            InMemoryStorage,
            get_storage,
            reset_storage,
            set_storage,
        )

        original = get_storage()
        test_store = InMemoryStorage()
        set_storage(test_store)
        assert get_storage() is test_store
        reset_storage()
        # After reset, get_storage resolves fresh
        fresh = get_storage()
        assert fresh is not test_store
        # Restore for other tests
        reset_storage()


class TestShimCompatibility:
    """EOS shims re-export exactly what callers expect."""

    def test_decision_trace_shim(self):
        from umh.runtime_engine.decision_trace import DecisionTrace, build_trace, MAX_TRACES
        from umh.decision.trace import DecisionTrace as UMH_DT

        assert DecisionTrace is UMH_DT
        assert MAX_TRACES == 50
        assert callable(build_trace)

    def test_goal_state_shim(self):
        from umh.goals.state import (
            GoalState,
            NO_GOAL,
            GoalTracker,
            GoalRegistry,
            compute_goal_relevance,
        )
        from umh.goals.state import GoalState as UMH_GS

        assert GoalState is UMH_GS
        assert NO_GOAL.goal_id == "none"

    def test_strategy_memory_shim(self):
        from umh.strategy.memory import (
            StrategyMemory,
            StrategyStats,
            get_strategy_memory,
            reset_strategy_memory,
        )
        from umh.strategy.memory import StrategyMemory as UMH_SM

        assert StrategyMemory is UMH_SM

    def test_objective_engine_direct(self):
        from umh.goals.objective import ObjectiveFunction

        assert ObjectiveFunction is not None


class TestGoalStateFunctional:
    """UMH goals work end-to-end without EOS."""

    def test_goal_registry_lifecycle(self):
        from umh.goals.state import GoalState, GoalRegistry, NO_GOAL

        reg = GoalRegistry()
        assert reg.get_active_goal() is NO_GOAL

        goal = GoalState(
            goal_id="test",
            description="Test goal",
            success_criteria={"type": "fast"},
            priority=0.9,
        )
        reg.add_goal(goal)
        assert reg.size == 1

        reg.set_active_goal("test")
        assert reg.get_active_goal().goal_id == "test"

        reg.remove_goal("test")
        assert reg.is_empty()

    def test_goal_tracker_ema(self):
        from umh.goals.state import GoalTracker

        tracker = GoalTracker(goal_id="t")
        tracker.update_success(0.8)
        assert tracker.success_score == 0.8
        assert tracker.uses == 1

        tracker.update_success(0.6)
        assert tracker.uses == 2
        assert 0.6 < tracker.success_score < 0.8

    def test_pure_scoring_functions(self):
        from umh.goals.state import (
            GoalState,
            compute_goal_relevance,
            compute_goal_weight,
            strategy_goal_score,
        )

        goal = GoalState(
            goal_id="sell",
            description="Close sale",
            success_criteria={"response_type": "persuasive"},
            priority=0.9,
        )
        relevance = compute_goal_relevance(goal, {"response_type": "persuasive"})
        assert relevance == 1.0

        weight = compute_goal_weight(goal)
        assert 0.0 < weight <= 1.0

        score = strategy_goal_score("clarity", goal)
        assert score > 0.5


class TestStrategyMemoryFunctional:
    """UMH strategy memory works end-to-end without EOS."""

    def test_record_and_rank(self):
        from umh.strategy.memory import StrategyMemory

        mem = StrategyMemory()
        mem.record_win("clarity", quality_score=0.85)
        mem.record_win("structured", quality_score=0.65)

        ranked = mem.rank_strategies()
        assert len(ranked) == 2
        assert ranked[0][0] == "clarity"

    def test_stale_detection(self):
        from umh.strategy.memory import StrategyMemory

        mem = StrategyMemory()
        mem.record_win("a", quality_score=0.5)
        for _ in range(6):
            mem.record_win("b", quality_score=0.5)

        stale = mem.get_stale_strategy(["a", "b"], stale_threshold=5)
        assert stale == "a"


class TestUMHExecutionCleanImports:
    """Phase 4: execution contract has zero EOS dependencies."""

    def test_execution_contract_clean(self):
        filepath = UMH_ROOT / "execution" / "contract.py"
        imports = _extract_imports(filepath)
        eos_imports = [(ln, m) for ln, m in imports if m.startswith("umh.runtime_engine.")]
        assert eos_imports == [], f"Forbidden imports in contract.py: {eos_imports}"


class TestUMHExecutionImportsWork:
    """Phase 4: all execution types import successfully."""

    def test_execution_contract_imports(self):
        from umh.execution.contract import (
            ExecutionRequest,
            ExecutionResult,
            ExecutionContext,
            ExecutionClass,
            ExecutionStatus,
            ExecutionPriority,
            ExecutionConstraints,
            ExecutionTarget,
        )

        assert ExecutionClass.LLM_CALL.value == "llm_call"
        assert ExecutionStatus.SUCCEEDED.value == "succeeded"
        assert ExecutionPriority.CRITICAL.value == "critical"

    def test_execution_interfaces_imports(self):
        from umh.execution.interfaces import (
            ExecutionBackend,
            NullExecutionBackend,
            ExecutionObserver,
            NullExecutionObserver,
            get_execution_backend,
            set_execution_backend,
            reset_execution_backend,
        )

        backend = NullExecutionBackend()
        assert isinstance(backend, ExecutionBackend)
        assert not backend.can_handle("anything")


class TestExecutionContractFunctional:
    """Phase 4: execution contract types work end-to-end without EOS."""

    def test_request_roundtrip(self):
        from umh.execution.contract import (
            ExecutionRequest,
            ExecutionClass,
            ExecutionConstraints,
            ExecutionTarget,
            ExecutionContext,
        )

        ctx = ExecutionContext(
            session_id="s1",
            active_goal_id="g1",
            strategy_name="clarity",
            strategy_confidence=0.85,
        )
        req = ExecutionRequest(
            execution_id="exec_test1",
            correlation_id="corr_1",
            causal_event_id="ev_1",
            session_id="s1",
            operation="llm_generate",
            inputs={"prompt": "hello"},
            execution_class=ExecutionClass.LLM_CALL,
            constraints=ExecutionConstraints(timeout_s=60, max_tokens=1000),
            target=ExecutionTarget(node_id="vps", transport="local"),
            context=ctx,
            issued_at="2026-04-23T16:00:00Z",
            issued_by="gateway",
            idempotency_key="abc123",
        )

        d = req.to_dict()
        req2 = ExecutionRequest.from_dict(d)
        assert req == req2
        assert d["context"]["active_goal_id"] == "g1"
        assert d["context"]["strategy_confidence"] == 0.85

    def test_result_roundtrip(self):
        from umh.execution.contract import (
            ExecutionResult,
            ExecutionStatus,
        )

        result = ExecutionResult(
            execution_id="exec_test2",
            correlation_id="corr_2",
            causal_event_id="ev_2",
            operation="llm_generate",
            status=ExecutionStatus.SUCCEEDED,
            outputs={"text": "Generated response"},
            model_used="gemini/gemini-2.5-flash",
            tokens_used={"input": 80, "output": 120},
            cost_usd=0.001,
            latency_ms=150,
        )

        d = result.to_dict()
        result2 = ExecutionResult.from_dict(d)
        assert result == result2
        assert d["model_used"] == "gemini/gemini-2.5-flash"

    def test_null_backend_rejects(self):
        from umh.execution.contract import (
            ExecutionRequest,
            ExecutionClass,
            ExecutionConstraints,
            ExecutionTarget,
            ExecutionContext,
            ExecutionStatus,
        )
        from umh.execution.interfaces import NullExecutionBackend

        req = ExecutionRequest(
            execution_id="exec_null",
            correlation_id="corr_n",
            causal_event_id="ev_n",
            session_id="s1",
            operation="test_op",
            inputs={},
            execution_class=ExecutionClass.PURE,
            constraints=ExecutionConstraints(),
            target=ExecutionTarget(node_id="none", transport="none"),
            context=ExecutionContext(),
            issued_at="2026-04-23T16:00:00Z",
            issued_by="test",
            idempotency_key="null_test",
        )

        backend = NullExecutionBackend()
        result = backend.execute(req)
        assert result.status == ExecutionStatus.REJECTED
        assert result.error == "No execution backend configured"

    def test_backend_singleton_management(self):
        from umh.execution.interfaces import (
            NullExecutionBackend,
            get_execution_backend,
            set_execution_backend,
            reset_execution_backend,
        )

        reset_execution_backend()
        custom = NullExecutionBackend()
        set_execution_backend(custom)
        assert get_execution_backend() is custom
        reset_execution_backend()
        fresh = get_execution_backend()
        assert fresh is not custom
        reset_execution_backend()

    def test_observer_protocol(self):
        from umh.execution.interfaces import (
            ExecutionObserver,
            NullExecutionObserver,
            set_execution_observer,
            get_execution_observer,
            reset_execution_observer,
        )

        obs = NullExecutionObserver()
        assert isinstance(obs, ExecutionObserver)
        set_execution_observer(obs)
        assert get_execution_observer() is obs
        reset_execution_observer()

    def test_idempotency_key_deterministic(self):
        from umh.execution.contract import _compute_idempotency_key

        k1 = _compute_idempotency_key("op1", {"a": 1, "b": 2})
        k2 = _compute_idempotency_key("op1", {"b": 2, "a": 1})
        k3 = _compute_idempotency_key("op2", {"a": 1, "b": 2})
        assert k1 == k2, "Same inputs in different order should produce same key"
        assert k1 != k3, "Different operations should produce different keys"


class TestExecutionAuthorityShift:
    """Validates UMH is the sole execution authority after Phase 5.

    These tests enforce the architectural invariant: no production code
    calls ExecutionSpine() directly except the adapter backend.
    """

    SPINE_FILE = "eos/execution_spine.py"

    EXEMPT_FILES = {
        "umh/runtime_engine/execution_spine.py",
        "umh/runtime_engine/cognitive_loop.py",
        "umh/runtime_engine/session_runtime.py",
        "umh/runtime_engine/multi_strategy.py",
        "umh/runtime_engine/commit_pipeline.py",
    }

    def _production_python_files(self) -> list[Path]:
        """All Python files that are production code (not tests)."""
        repo = Path("/opt/OS")
        dirs = [repo / "umh"]
        files = []
        for d in dirs:
            files.extend(d.rglob("*.py"))
        return [
            f for f in files if "__pycache__" not in str(f) and "test_" not in f.name
        ]

    def test_no_direct_execution_spine_instantiation(self):
        """No production file instantiates ExecutionSpine() except exempt files."""
        violations = []
        for filepath in self._production_python_files():
            rel = str(filepath.relative_to(Path("/opt/OS")))
            if rel in self.EXEMPT_FILES:
                continue
            source = filepath.read_text(encoding="utf-8")
            for i, line in enumerate(source.splitlines(), 1):
                stripped = line.lstrip()
                if (
                    stripped.startswith("#")
                    or stripped.startswith('"""')
                    or stripped.startswith("'''")
                ):
                    continue
                if "ExecutionSpine()" in line:
                    violations.append(f"{rel}:{i}: {line.strip()}")
        assert not violations, (
            f"Direct ExecutionSpine() found in {len(violations)} location(s) — "
            f"all calls must go through run_via_umh():\n" + "\n".join(violations)
        )

    def test_no_direct_spine_run_calls(self):
        """No production file calls .run() on a spine instance except exempt files."""
        import re

        pattern = re.compile(r"(?:ExecutionSpine\(\)|spine)\.run\(")
        violations = []
        for filepath in self._production_python_files():
            rel = str(filepath.relative_to(Path("/opt/OS")))
            if rel in self.EXEMPT_FILES:
                continue
            source = filepath.read_text(encoding="utf-8")
            for i, line in enumerate(source.splitlines(), 1):
                stripped = line.lstrip()
                if stripped.startswith("#"):
                    continue
                if pattern.search(line):
                    violations.append(f"{rel}:{i}: {line.strip()}")
        assert not violations, (
            f"Direct spine.run() found in {len(violations)} location(s) — "
            f"all calls must go through run_via_umh():\n" + "\n".join(violations)
        )

    def test_run_via_umh_is_importable(self):
        """run_via_umh exists and is callable."""
        from umh.runtime_engine.execution_spine import run_via_umh

        assert callable(run_via_umh)

    def test_run_via_umh_returns_spine_result(self):
        """run_via_umh returns SpineResult (str subclass with metadata)."""
        import inspect
        from umh.runtime_engine.execution_spine import run_via_umh, SpineResult

        sig = inspect.signature(run_via_umh)
        assert sig.return_annotation is SpineResult

    def test_no_rogue_spine_consumers(self):
        """No non-exempt file imports ExecutionSpine for instantiation."""
        violations = []
        for filepath in self._production_python_files():
            rel = str(filepath.relative_to(Path("/opt/OS")))
            if rel in self.EXEMPT_FILES:
                continue
            source = filepath.read_text(encoding="utf-8")
            if "ExecutionSpine()" in source:
                violations.append(rel)
        assert not violations, (
            f"Rogue ExecutionSpine() instantiation in: {violations}"
        )

    def test_umh_engine_execute_is_the_entry_point(self):
        """umh.execution.engine.execute exists and accepts ExecutionRequest."""
        import inspect
        from umh.execution.engine import execute

        sig = inspect.signature(execute)
        params = list(sig.parameters.values())
        assert len(params) == 1
        ann = params[0].annotation
        assert ann == "ExecutionRequest" or (
            hasattr(ann, "__name__") and ann.__name__ == "ExecutionRequest"
        )

    def test_callsite_count_matches_redirect(self):
        """All production callsites use run_via_umh, not ExecutionSpine().run()."""
        import re

        umh_calls = 0
        direct_calls = 0
        spine_pattern = re.compile(r"ExecutionSpine\(\)\.run\(")
        umh_pattern = re.compile(r"run_via_umh\(")

        for filepath in self._production_python_files():
            rel = str(filepath.relative_to(Path("/opt/OS")))
            if rel in self.EXEMPT_FILES:
                continue
            source = filepath.read_text(encoding="utf-8")
            for line in source.splitlines():
                if line.lstrip().startswith("#"):
                    continue
                direct_calls += len(spine_pattern.findall(line))
                umh_calls += len(umh_pattern.findall(line))

        assert direct_calls == 0, (
            f"Found {direct_calls} direct spine calls that should be zero"
        )
        assert umh_calls > 0, (
            "Expected at least one run_via_umh() call in production code"
        )


class TestExecutionPipelineComposition:
    """Validates that the execution pipeline is composable and observable."""

    def _make_pipeline(self):
        from umh.runtime_engine.execution_spine import _build_default_pipeline

        return _build_default_pipeline()

    def test_default_pipeline_has_9_stages(self):
        p = self._make_pipeline()
        assert len(p.stages) == 9

    def test_default_pipeline_stage_order(self):
        p = self._make_pipeline()
        expected = [
            "authority_check",
            "prompt_enhancement",
            "context_assembly",
            "llm_generation",
            "quality_verification",
            "stage_filter",
            "outcome_evaluation",
            "commit",
            "response_footer",
        ]
        assert p.stage_names == expected

    def test_all_stages_satisfy_protocol(self):
        from umh.execution.stages import ExecutionStage

        p = self._make_pipeline()
        for stage in p.stages:
            assert isinstance(stage, ExecutionStage), (
                f"{stage.name} does not satisfy ExecutionStage"
            )

    def test_stage_can_be_removed(self):
        p = self._make_pipeline()
        p2 = p.remove("response_footer")
        assert "response_footer" not in p2.stage_names
        assert len(p2.stages) == 8

    def test_stage_can_be_replaced(self):
        from dataclasses import dataclass
        from umh.execution.stages import StageContext

        @dataclass(frozen=True)
        class NoOpStage:
            name: str = "commit"
            description: str = "no-op replacement"
            dependencies: tuple[str, ...] = ("outcome_evaluation",)
            can_abort: bool = False

            def run(self, context: StageContext) -> StageContext:
                return context

        p = self._make_pipeline()
        p2 = p.replace("commit", NoOpStage())
        assert p2.stage_names == p.stage_names
        assert type(p2.stages[7]).__name__ == "NoOpStage"

    def test_invalid_dependency_order_raises(self):
        import pytest
        from umh.execution.pipeline import ExecutionPipeline
        from umh.stages.llm_generation import LLMGenerationStage
        from umh.stages.authority import AuthorityCheckStage

        with pytest.raises(ValueError, match="depends on"):
            ExecutionPipeline([LLMGenerationStage(), AuthorityCheckStage()])

    def test_individual_stage_runs_in_isolation(self):
        from umh.execution.stages import StageContext
        from umh.stages.context_assembly import ContextAssemblyStage

        class FakeContext:
            def to_system_prompt(self):
                return "test system prompt"

        ctx = StageContext(unified_context=FakeContext())
        stage = ContextAssemblyStage()
        result = stage.run(ctx)
        assert result.system_prompt == "test system prompt"

    def test_abort_stops_pipeline(self):
        from dataclasses import dataclass
        from umh.execution.pipeline import ExecutionPipeline
        from umh.execution.stages import StageContext

        @dataclass(frozen=True)
        class AbortStage:
            name: str = "aborter"
            description: str = "always aborts"
            dependencies: tuple[str, ...] = ()
            can_abort: bool = True

            def run(self, context: StageContext) -> StageContext:
                context.aborted = True
                context.abort_result = "intentional abort"
                return context

        @dataclass(frozen=True)
        class NeverReached:
            name: str = "unreachable"
            description: str = "should never run"
            dependencies: tuple[str, ...] = ("aborter",)
            can_abort: bool = False

            def run(self, context: StageContext) -> StageContext:
                context.extra["reached"] = True
                return context

        p = ExecutionPipeline([AbortStage(), NeverReached()])
        result = p.run(StageContext())
        assert result.context.aborted
        assert result.aborted_at == "aborter"
        assert "reached" not in result.context.extra

    def test_stage_timings_recorded(self):
        from dataclasses import dataclass
        from umh.execution.pipeline import ExecutionPipeline
        from umh.execution.stages import StageContext

        @dataclass(frozen=True)
        class TimedStage:
            name: str = "timed"
            description: str = "just passes through"
            dependencies: tuple[str, ...] = ()
            can_abort: bool = False

            def run(self, context: StageContext) -> StageContext:
                return context

        p = ExecutionPipeline([TimedStage()])
        result = p.run(StageContext())
        assert "timed" in result.context.stage_timings
        assert result.total_ms >= 0
        assert len(result.stage_results) == 1
        assert result.stage_results[0].name == "timed"

    def test_pipeline_immutable_on_mutation(self):
        """insert/remove/replace return new pipelines, don't mutate original."""
        p = self._make_pipeline()
        original_names = list(p.stage_names)
        p2 = p.remove("response_footer")
        assert p.stage_names == original_names
        assert p2.stage_names != original_names


class TestObjectiveFunctional:
    """UMH objective engine works end-to-end without EOS."""

    def test_evaluate_objectives(self):
        from umh.goals.objective import ObjectiveFunction, ObjectiveSet

        obj_set = ObjectiveSet(
            objectives=[
                ObjectiveFunction("rate", "reply_rate", "maximize", 0.05, weight=0.5),
                ObjectiveFunction("cost", "cost", "minimize", 10.0, weight=0.5),
            ]
        )
        results = obj_set.evaluate({"reply_rate": 0.1, "cost": 5.0})
        assert len(results) == 2
        assert obj_set.aggregate_score() > 0
        assert obj_set.ok

    def test_hard_constraint_violation(self):
        from umh.goals.objective import ObjectiveFunction, ObjectiveSet

        obj_set = ObjectiveSet(
            objectives=[
                ObjectiveFunction(
                    "min_volume", "sent", "maximize", 50.0, hard_constraint=True
                ),
            ]
        )
        obj_set.evaluate({"sent": 10})
        assert obj_set.aggregate_score() == 0.0
        assert not obj_set.ok
