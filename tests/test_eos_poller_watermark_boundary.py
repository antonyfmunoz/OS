"""WP-P4-005 — EOS poller watermark adapter-boundary + behavior regression.

Two concerns:

1. Boundary: `projections/eos/integration/` must not reach into a provider-internal
   adapter module. It previously did — `poller.py` imported `WatermarkStore` from
   `adapters.notion.integration.watermarks`, coupling the EOS projection to the
   Notion provider's internals. `WatermarkStore` is generic infrastructure and was
   relocated to `substrate/state/stores/watermark_store.py` (a legal downward
   projection→substrate dependency). This test blocks reintroducing any
   `adapters.*.integration.*` import from that directory.

2. Behavior: the relocated `WatermarkStore` must read/write watermarks exactly as
   before (round-trip, default-on-missing, last-write-wins across JSONL reload).

The boundary test parses source via `ast` (no import) — mirroring the pattern in
tests/test_eos_boot_contract.py — so it never pulls in poller's heavy deps.
"""

from __future__ import annotations

import ast
import os
import re
import sys
from pathlib import Path

_WORKTREE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _WORKTREE not in sys.path:
    sys.path.insert(0, _WORKTREE)

from substrate.state.stores.watermark_store import WatermarkStore

_EOS_INTEGRATION_DIR = Path(_WORKTREE) / "projections" / "eos" / "integration"
# provider-internal adapter path: adapters.<provider>.integration.<module>
_PROVIDER_INTERNAL_RE = re.compile(r"^adapters\.[a-z_0-9]+\.integration\b")


def _imported_modules(py_file: Path) -> list[str]:
    tree = ast.parse(py_file.read_text(encoding="utf-8"))
    mods: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            mods.append(node.module)
        elif isinstance(node, ast.Import):
            mods.extend(alias.name for alias in node.names)
    return mods


def test_eos_integration_has_no_provider_internal_adapter_imports():
    """No file under projections/eos/integration/ may import a provider-internal
    adapters.<provider>.integration.* module. EOS consumes substrate/public
    contracts, not another provider's internals."""
    offenders: list[str] = []
    for py in sorted(_EOS_INTEGRATION_DIR.glob("*.py")):
        for mod in _imported_modules(py):
            if _PROVIDER_INTERNAL_RE.match(mod):
                offenders.append(f"{py.name}: {mod}")
    assert not offenders, (
        "projections/eos/integration reaches into provider-internal adapter modules "
        f"{offenders}; consume the generic substrate WatermarkStore "
        "(substrate.state.stores.watermark_store) or a public contract instead"
    )


def test_poller_uses_substrate_watermark_store():
    """The EOS poller imports WatermarkStore from its substrate home."""
    src = (_EOS_INTEGRATION_DIR / "poller.py").read_text(encoding="utf-8")
    assert "from substrate.state.stores.watermark_store import WatermarkStore" in src
    assert "adapters.notion.integration.watermarks" not in src


def test_watermark_store_roundtrip(tmp_path):
    """Behavior preserved: default-on-missing, record→read, last-write-wins across reload."""
    p = tmp_path / "wm.jsonl"
    store = WatermarkStore(path=p)

    # default when key absent
    assert store.get_watermark("crm_contacts:u1") == "2000-01-01T00:00:00.000Z"

    # record then read back
    store.record_watermark("crm_contacts:u1", "2026-07-04T12:00:00.000Z")
    assert store.get_watermark("crm_contacts:u1") == "2026-07-04T12:00:00.000Z"

    # last-write-wins, and it survives a fresh instance (JSONL reload)
    store.record_watermark("crm_contacts:u1", "2026-07-05T00:00:00.000Z")
    reloaded = WatermarkStore(path=p)
    assert reloaded.get_watermark("crm_contacts:u1") == "2026-07-05T00:00:00.000Z"

    # independent keys don't collide
    assert reloaded.get_watermark("crm_deals:u2") == "2000-01-01T00:00:00.000Z"


def test_watermark_store_is_generic_no_provider_coupling():
    """The relocated store carries no provider-specific import coupling."""
    src = (
        Path(_WORKTREE) / "substrate" / "state" / "stores" / "watermark_store.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith("adapters."), (
                f"substrate watermark_store must not import adapters.*: {node.module}"
            )
