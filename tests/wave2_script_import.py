"""Load a Wave 2 ``scripts/`` module from THIS candidate repo, by explicit path.

Why this exists (found by the whole-tree run at e7053a753, shards s1/s2):

A plain ``import scripts.wave2_attempt_runner`` resolves through ``sys.path``.
That is safe only while nothing has put another repo root ahead of this one --
and something does. ``tests/adapters/broadcast/test_node_dispatch.py`` (pre-existing,
untouched by Wave 2) inserts ``UMH_ROOT``/``/opt/OS`` into ``sys.path`` at import
time. The live ``/opt/OS`` checkout is STALE at Wave 0 (695268727) and has its own
``scripts/`` package that contains NO Wave 2 modules, so once that path wins the
binding, the import fails with ModuleNotFoundError -- in a shard, but never when
the file runs alone.

The failure is a TEST-ISOLATION defect, not a product defect: production never
imports through pytest's ``sys.path``. So the fix belongs here, in Wave 2's own
tests, rather than in the pre-existing file or in a shard-ordering workaround
that would silently depend on which files happen to run together.

Resolving by explicit file path makes the binding independent of ``sys.path``
order entirely -- the module can only ever come from this candidate tree.
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import sys
from types import ModuleType

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_wave2_script(module_name: str) -> ModuleType:
    """Import ``scripts/<module_name>.py`` from this repo, ignoring sys.path.

    The cache key embeds the RESOLVED ABSOLUTE PATH, not just the module name.
    ``_REPO`` is derived from this file's own ``__file__``, so within a single
    process it is already fixed -- but that is a property of how the helper
    happens to be imported, not something the cache itself enforced. Keying on
    the path makes the guarantee structural instead of circumstantial: two
    different candidate checkouts loaded in one process get two distinct cache
    entries and cannot return each other's module, and a stale entry can never
    be served for a different path.
    """
    path = os.path.realpath(os.path.join(_REPO, "scripts", f"{module_name}.py"))
    if not os.path.exists(path):
        raise ModuleNotFoundError(
            f"{module_name} not found in this candidate repo at {path}"
        )

    # Path-qualified identity: same name + different checkout => different key.
    digest = hashlib.sha256(path.encode()).hexdigest()[:12]
    cache_key = f"_wave2_candidate_scripts.{digest}.{module_name}"
    cached = sys.modules.get(cache_key)
    if cached is not None:
        return cached

    spec = importlib.util.spec_from_file_location(cache_key, path)
    if spec is None or spec.loader is None:
        raise ModuleNotFoundError(f"could not build a spec for {path}")
    module = importlib.util.module_from_spec(spec)
    # Register BEFORE exec so a self-referential import inside the module resolves.
    sys.modules[cache_key] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(cache_key, None)
        raise
    return module
