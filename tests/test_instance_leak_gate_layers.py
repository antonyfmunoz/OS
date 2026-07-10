"""Regression tests for the LAYER-AWARE instance-leak gate.

The gate distinguishes where instance language is a leak (tenant-neutral shipping
code/docs) from where it is correct (this instance's own data / projection /
history). These tests lock that boundary so it cannot silently regress:

  code   — every category is a leak (brand + infra + PII).
  prose  — HARD leaks only (secret/infra/account); brand NAMES tolerated.
  exempt — this instance's own data/projection/history; ONLY founder-email PII.

Founder-email PII is scrubbed EVERYWHERE, even in exempt files.
"""
import importlib.util
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "check_instance_leak", _REPO / "scripts/check_instance_leak.py"
)
_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gate)


def _scan(rel: str, text: str) -> set[str]:
    """Write text at a repo-relative path, scan, return flagged categories, clean up."""
    p = _REPO / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    existed = p.exists()
    original = p.read_text(encoding="utf-8") if existed else None
    p.write_text(text, encoding="utf-8")
    try:
        return {v["category"] for v in _gate._scan_file(p)}
    finally:
        if existed:
            p.write_text(original, encoding="utf-8")
        else:
            p.unlink()


# (id, rel_path, text, must_flag, must_not_flag)
_CASES = [
    ("code_all_fire", "substrate/_t_leak.py",
     'a="Lyfe Institute"\nb="100.77.233.50"\nc="antonyfm@empyreanstudios.co"\n',
     {"company_name", "infra_ip", "account_id"}, set()),
    ("prose_hard_only", "docs/_t_ship.md",
     "# Host 100.77.233.50 serves Lyfe Institute\n",
     {"infra_ip"}, {"company_name"}),
    ("substrate_skill_hard", "skills/tools/_t/SKILL.md",
     "Clone github.com/antonyfmunoz/OS for Initiate Arena\n",
     {"account_id"}, {"product_name"}),
    ("projection_skill_pii_only", "skills/Outreach/_t/SKILL.md",
     "Pitch Initiate Arena from antonyfm@empyreanstudios.co on 100.77.233.50\n",
     {"account_id"}, {"product_name", "infra_ip"}),
    ("history_pii_only", "docs/audits/_t_2026.md",
     "op://UMH-Production on 100.77.233.50 — antonyfm@empyreanstudios.co\n",
     {"account_id"}, {"op_vault", "infra_ip"}),
    ("history_discord_id_ok", "docs/audits/_t_did.md",
     "Channel 1485765456739696714 vault UMH-Production\n",
     set(), {"account_id", "op_vault"}),
    # A dated record ANYWHERE (not just docs/audits/) is frozen history — exempt
    # for infra/vault, but founder-email PII still fires.
    ("dated_record_pii_only", "docs/MIGRATION_2026-07-05.md",
     "op://EntrepreneurOS ran; contact antonyfm@empyreanstudios.co\n",
     {"account_id"}, {"op_vault"}),
    ("ops_runbook_pii_only", "docs/operations/_t_v1.md",
     "ssh 100.74.199.102 ; ping antonyfm@theempyreancreative.com\n",
     {"account_id"}, {"infra_ip"}),
    ("sanctioned_vault_default", "scripts/_t_vault.sh",
     'VAULT="${UMH_OP_VAULT:-UMH-Production}"\n',
     set(), {"op_vault"}),
]


@pytest.mark.parametrize("cid,rel,text,must,must_not", _CASES, ids=[c[0] for c in _CASES])
def test_layer_aware_scan(cid, rel, text, must, must_not):
    got = _scan(rel, text)
    assert must <= got, f"{cid}: missing required flags {must - got} (got {got})"
    assert not (must_not & got), f"{cid}: leaked forbidden flags {must_not & got}"


def test_scan_mode_classification():
    m = _gate._scan_mode
    assert m("substrate/x.py", ".py") == "code"
    assert m("saas/index.ts", ".ts") == "code"
    assert m("docs/SYSTEM_ARCHITECTURE.md", ".md") == "prose"
    assert m("skills/tools/git/SKILL.md", ".md") == "prose"
    assert m("skills/Outreach/x/SKILL.md", ".md") == "exempt"
    assert m("docs/audits/2026-01-01_x.md", ".md") == "exempt"
    assert m("docs/operations/runbook_v1.md", ".md") == "exempt"
    assert m("CLAUDE.md", ".md") == "exempt"
    assert m("AGENTS.md", ".md") == "exempt"
