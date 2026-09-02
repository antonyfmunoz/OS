"""The explicit-path candidate script loader — cache identity and isolation.

Why this suite exists: the loader was introduced to close a cross-test import
contamination defect (a pre-existing test puts stale ``/opt/OS`` on ``sys.path``;
its ``scripts`` package then shadows this candidate's own). The loader's own
cache identity then needs the same scrutiny the defect got -- an identity keyed
on the bare module name would reintroduce exactly the shadowing class of bug one
level up, inside the fix.

Every test here pins a property that must survive refactoring.
"""

from __future__ import annotations

import os
import sys
import textwrap

import pytest

from tests.wave2_script_import import load_wave2_script

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_loads_the_candidate_module_not_a_sys_path_one():
    """The module must come from THIS repo, whatever sys.path says."""
    mod = load_wave2_script("wave2_attempt_runner")
    assert mod.__file__ is not None
    assert os.path.realpath(mod.__file__) == os.path.realpath(
        os.path.join(REPO, "scripts", "wave2_attempt_runner.py")
    )


def test_same_module_is_reused_not_re_executed():
    """Repeated loads return the identical object (cheap, and no double import)."""
    a = load_wave2_script("wave2_attempt_runner")
    b = load_wave2_script("wave2_attempt_runner")
    assert a is b


def test_a_stale_sys_path_entry_cannot_redirect_the_load(monkeypatch, tmp_path):
    """The exact defect: a decoy 'scripts' package earlier on sys.path is ignored.

    This reproduces the production-shaped failure -- a stale checkout whose
    scripts/ package lacks the Wave 2 modules -- and proves the loader is immune.
    """
    decoy = tmp_path / "stale_checkout"
    (decoy / "scripts").mkdir(parents=True)
    (decoy / "scripts" / "__init__.py").write_text("")
    # A decoy that would answer to the same name but is NOT the candidate.
    (decoy / "scripts" / "wave2_attempt_runner.py").write_text(
        "SENTINEL = 'STALE'\n"
    )
    monkeypatch.syspath_prepend(str(decoy))
    # Drop any cached binding of the real package so sys.path would be consulted.
    for name in list(sys.modules):
        if name == "scripts" or name.startswith("scripts."):
            monkeypatch.delitem(sys.modules, name, raising=False)

    mod = load_wave2_script("wave2_attempt_runner")
    assert getattr(mod, "SENTINEL", None) != "STALE"
    assert os.path.realpath(mod.__file__).startswith(os.path.realpath(REPO))


def test_two_candidate_paths_do_not_collide_in_one_process(tmp_path):
    """Same module NAME from two different checkouts => two distinct modules.

    A cache keyed on the bare module name would return the first checkout's
    module for the second -- silently testing the wrong candidate. The key is
    path-qualified precisely so this cannot happen.
    """
    import tests.wave2_script_import as loader

    other = tmp_path / "other_candidate"
    (other / "scripts").mkdir(parents=True)
    (other / "scripts" / "wave2_attempt_runner.py").write_text("MARKER = 'OTHER'\n")

    real = load_wave2_script("wave2_attempt_runner")

    original_repo = loader._REPO
    try:
        loader._REPO = str(other)
        alt = load_wave2_script("wave2_attempt_runner")
    finally:
        loader._REPO = original_repo

    assert alt is not real, "two candidate paths collided in one cache entry"
    assert getattr(alt, "MARKER", None) == "OTHER"
    # And the original is still intact and still served for the real path.
    assert load_wave2_script("wave2_attempt_runner") is real


def test_cache_key_encodes_the_resolved_path(tmp_path):
    """The identity must be derived from the path, not the name alone."""
    import tests.wave2_script_import as loader

    other = tmp_path / "cand_b"
    (other / "scripts").mkdir(parents=True)
    (other / "scripts" / "wave2_beast_reconciler.py").write_text("X = 1\n")

    load_wave2_script("wave2_beast_reconciler")
    original_repo = loader._REPO
    try:
        loader._REPO = str(other)
        load_wave2_script("wave2_beast_reconciler")
    finally:
        loader._REPO = original_repo

    keys = [k for k in sys.modules if "wave2_beast_reconciler" in k
            and k.startswith("_wave2_candidate_scripts.")]
    assert len(keys) >= 2, f"expected distinct per-path cache keys, got {keys}"


def test_a_missing_module_fails_loudly_not_silently():
    """A typo or a genuinely absent script must raise, never return a stub."""
    with pytest.raises(ModuleNotFoundError):
        load_wave2_script("wave2_this_script_does_not_exist")


def test_a_module_that_raises_on_import_is_not_left_cached(tmp_path):
    """A half-initialised module must never be served to a later caller."""
    import tests.wave2_script_import as loader

    bad = tmp_path / "bad_candidate"
    (bad / "scripts").mkdir(parents=True)
    (bad / "scripts" / "wave2_attempt_runner.py").write_text(
        "raise RuntimeError('boom')\n"
    )
    original_repo = loader._REPO
    try:
        loader._REPO = str(bad)
        with pytest.raises(RuntimeError):
            load_wave2_script("wave2_attempt_runner")
        # the failed entry must be gone, so a retry re-executes rather than
        # handing back a broken module
        leaked = [
            k for k in sys.modules
            if k.startswith("_wave2_candidate_scripts.")
            and "wave2_attempt_runner" in k
            and getattr(sys.modules[k], "__file__", "")
            and str(bad) in str(sys.modules[k].__file__)
        ]
        assert not leaked, f"a failed import stayed cached: {leaked}"
    finally:
        loader._REPO = original_repo


def test_no_wave2_test_imports_a_candidate_script_through_sys_path():
    """Regression pin for the whole defect class.

    If a new Wave 2 test reaches for `import scripts.x` or
    `importlib.import_module("scripts.x")`, it is once again resolvable through
    a polluted sys.path -- and this fails, naming the file.

    Scope: IN-PROCESS imports only. A generated launcher that is written to a
    file and executed as a SEPARATE process (which sets its own sys.path before
    importing) is not exposed to this test process's polluted sys.path, so it is
    not a defect. Those are detected via AST -- an import inside a string
    literal is not an import node -- rather than by a line-level regex, which
    cannot tell the two apart.
    """
    import ast

    tests_dir = os.path.join(REPO, "tests")
    offenders: list[str] = []
    for name in sorted(os.listdir(tests_dir)):
        if not (name.startswith("test_wave2") and name.endswith(".py")):
            continue
        path = os.path.join(tests_dir, name)
        with open(path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read(), filename=path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("scripts."):
                        offenders.append(f"{name}:{node.lineno}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if (node.module or "").startswith("scripts."):
                    offenders.append(f"{name}:{node.lineno}: from {node.module} import ...")
            elif isinstance(node, ast.Call):
                func = node.func
                is_import_module = (
                    isinstance(func, ast.Attribute) and func.attr == "import_module"
                ) or (isinstance(func, ast.Name) and func.id == "import_module")
                if is_import_module and node.args:
                    arg = node.args[0]
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        if arg.value.startswith("scripts."):
                            offenders.append(
                                f"{name}:{node.lineno}: import_module({arg.value!r})"
                            )
    assert not offenders, (
        "Wave 2 tests must load candidate scripts by explicit path "
        "(tests.wave2_script_import.load_wave2_script), not through sys.path:\n"
        + "\n".join(offenders)
    )
