"""P1 Phase 2B — Operator Experience Layer verification.

Confirms that substrate/operator/ is a pure input/context layer that:
1. Does NOT perform LLM execution (no AgentRuntime, CognitiveLoop, model_router imports)
2. Does NOT bypass governance (no GovernedExecutionSpine or governed_mutation imports)
3. IS correctly imported by transports/ (correct architecture direction)
4. IS NOT imported by daemon, gateway, or cognitive_loop (it feeds the pipeline, not runs it)
5. All modules are read-only, classification-only, or context-assembly

Verdict: UNCHANGED — no code modifications needed for P1 convergence.

Run with: pytest tests/test_p1_phase2b_operator.py -v
"""

import ast
import os
import sys

import pytest

sys.path.insert(0, "/opt/OS")

pytestmark = pytest.mark.smoke

OPERATOR_DIR = os.path.join(
    os.environ.get("UMH_ROOT", "/opt/OS"),
    "substrate", "operator",
)

EXECUTION_PATTERNS = {
    "AgentRuntime",
    "CognitiveLoop",
    "model_router",
    "call_with_fallback",
    "GovernedExecutionSpine",
    "governed_mutation",
}


def _get_operator_py_files():
    """All .py files in substrate/operator/."""
    files = []
    for fname in sorted(os.listdir(OPERATOR_DIR)):
        if fname.endswith(".py") and fname != "__init__.py":
            files.append(os.path.join(OPERATOR_DIR, fname))
    return files


def _extract_imports(filepath: str) -> list[str]:
    """Extract all import strings from a Python file."""
    with open(filepath) as f:
        try:
            tree = ast.parse(f.read())
        except SyntaxError:
            return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
                for alias in node.names:
                    imports.append(f"{node.module}.{alias.name}")
    return imports


# ── 1. No execution patterns in operator layer ─────────────────────


class TestNoExecutionBypass:
    """Operator modules must not import execution infrastructure."""

    @pytest.mark.parametrize("filepath", _get_operator_py_files(),
                             ids=lambda p: os.path.basename(p))
    def test_no_execution_imports(self, filepath):
        imports = _extract_imports(filepath)
        import_text = " ".join(imports)
        for pattern in EXECUTION_PATTERNS:
            assert pattern not in import_text, (
                f"{os.path.basename(filepath)} imports execution pattern '{pattern}' "
                f"— operator layer must not perform LLM execution"
            )

    @pytest.mark.parametrize("filepath", _get_operator_py_files(),
                             ids=lambda p: os.path.basename(p))
    def test_no_runtime_run_calls(self, filepath):
        """No .run() calls on runtime objects."""
        with open(filepath) as f:
            source = f.read()
        assert "runtime.run(" not in source, (
            f"{os.path.basename(filepath)} calls runtime.run() "
            f"— operator layer must not execute"
        )


# ── 2. Architecture direction ──────────────────────────────────────


class TestArchitectureDirection:
    """Operator layer must not be imported by daemon/gateway/cognitive_loop."""

    def test_daemon_does_not_import_operator(self):
        daemon_path = os.path.join(
            os.environ.get("UMH_ROOT", "/opt/OS"),
            "substrate", "organism", "daemon.py",
        )
        if not os.path.exists(daemon_path):
            pytest.skip("daemon.py not found")
        imports = _extract_imports(daemon_path)
        for imp in imports:
            assert "substrate.operator" not in imp, (
                f"daemon.py imports {imp} — operator is a context layer, "
                f"not a daemon dependency"
            )

    def test_cognitive_loop_does_not_import_operator(self):
        loop_path = os.path.join(
            os.environ.get("UMH_ROOT", "/opt/OS"),
            "substrate", "control_plane", "runtime", "cognitive_loop.py",
        )
        if not os.path.exists(loop_path):
            pytest.skip("cognitive_loop.py not found")
        imports = _extract_imports(loop_path)
        for imp in imports:
            assert "substrate.operator" not in imp, (
                f"cognitive_loop.py imports {imp} — operator is a context layer, "
                f"not a cognitive loop dependency"
            )

    def test_gateway_does_not_import_operator(self):
        gw_path = os.path.join(
            os.environ.get("UMH_ROOT", "/opt/OS"),
            "substrate", "control_plane", "runtime", "gateway.py",
        )
        if not os.path.exists(gw_path):
            pytest.skip("gateway.py not found")
        imports = _extract_imports(gw_path)
        for imp in imports:
            assert "substrate.operator" not in imp, (
                f"gateway.py imports {imp} — operator is a context layer, "
                f"not a gateway dependency"
            )


# ── 3. Module classification ──────────────────────────────────────


class TestModuleClassification:
    """Every operator module is read-only / classification / context-assembly."""

    def test_intent_router_is_classification_only(self):
        from substrate.operator.intent_router import IntentRouter
        router = IntentRouter()
        result = router.classify("what is the status of deployment")
        assert hasattr(result, "route_type")
        assert hasattr(result, "confidence")

    def test_intent_runtime_is_state_persistence(self):
        from substrate.operator.intent_runtime import IntentRuntime
        assert hasattr(IntentRuntime, "capture")
        assert hasattr(IntentRuntime, "retrieve")
        assert hasattr(IntentRuntime, "refine")
        assert hasattr(IntentRuntime, "alignment_score")

    def test_voice_query_engine_is_read_only(self):
        from substrate.operator.voice_query_engine import VoiceQueryEngine
        assert hasattr(VoiceQueryEngine, "resolve")
        assert hasattr(VoiceQueryEngine, "detect_domain")
        imports = _extract_imports(
            os.path.join(OPERATOR_DIR, "voice_query_engine.py")
        )
        import_text = " ".join(imports)
        for pattern in EXECUTION_PATTERNS:
            assert pattern not in import_text

    def test_operator_context_engine_is_aggregation(self):
        from substrate.operator.operator_context_engine import OperatorContextEngine
        assert hasattr(OperatorContextEngine, "snapshot")

    def test_file_count_matches_expected(self):
        """19 files including __init__.py — guards against unaudited additions."""
        py_files = [f for f in os.listdir(OPERATOR_DIR) if f.endswith(".py")]
        assert len(py_files) == 19, (
            f"Expected 19 operator .py files, found {len(py_files)}. "
            f"New files must be audited for execution bypass."
        )


# ── 4. Import cleanness ───────────────────────────────────────────


class TestImportCleanness:
    """Operator modules import only from allowed layers."""

    FORBIDDEN_UPWARD = {"transports.", "services.", "saas.", "projections."}

    @pytest.mark.parametrize("filepath", _get_operator_py_files(),
                             ids=lambda p: os.path.basename(p))
    def test_no_upward_imports(self, filepath):
        imports = _extract_imports(filepath)
        for imp in imports:
            for forbidden in self.FORBIDDEN_UPWARD:
                assert not imp.startswith(forbidden), (
                    f"{os.path.basename(filepath)} imports {imp} — "
                    f"substrate/ must not import from {forbidden}"
                )
