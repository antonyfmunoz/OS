"""WP-P4-SECRETS-RUNTIME-001 — guards for the UMH 1Password Secret Runtime Protocol.

The protocol standardizes the secret-runtime CONTRACT, not the manifest filename:
    1Password vault -> committed op:// Secret Reference Manifest
        -> op run runtime injection -> plaintext .env ignored/non-canonical.

These tests prove the contract holds for UMH substrate + every projection, that the
canonical wrapper enforces it, and that no secret VALUES leak into any committed record.
They read source/JSON as data (no imports, no network, no secret access).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
STATUS = REPO / "data" / "umh" / "projection_reconciliation" / "secrets_runtime_status.json"
DOC = REPO / "docs" / "PROJECTION_SECRET_RUNTIME_PROTOCOL.md"
WRAPPER = REPO / "scripts" / "op_run.sh"

EXPECTED_SYSTEMS = {"UMH", "EntrepreneurOS", "CreatorOS", "LyfeOS"}

# value-shaped secrets that must NEVER appear in a committed record
SECRET_VALUE_PATTERNS = [
    re.compile(r"sk_live_[0-9a-zA-Z]{16,}"),
    re.compile(r"sk_test_[0-9a-zA-Z]{16,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
    re.compile(r"(?:postgres|postgresql|mongodb(?:\+srv)?|mysql|redis)://[^:@/\s]+:[^@\s]{6,}@"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]


def _status() -> dict:
    return json.loads(STATUS.read_text())


def test_status_record_present_and_parses():
    assert STATUS.exists(), "secrets_runtime_status.json must exist"
    d = _status()
    assert d["packet"] == "WP-P4-SECRETS-RUNTIME-001"
    assert "systems" in d and isinstance(d["systems"], list)


def test_all_governed_systems_present():
    names = {s["system"] for s in _status()["systems"]}
    assert names == EXPECTED_SYSTEMS, f"expected {EXPECTED_SYSTEMS}, got {names}"


def test_every_system_declares_a_manifest_path():
    for s in _status()["systems"]:
        assert s.get("manifest_path"), f"{s['system']} must declare a manifest_path"
        assert s.get("env_op_template_present") is True, f"{s['system']} manifest must be present"


def test_umh_and_projections_share_the_contract_fields():
    """Filename may vary; the contract fields must be declared identically for all."""
    required = {"vault", "manifest_path", "env_op_template_present", "refs_resolve",
                "gitignore_protects_plaintext_env", "op_run_verified",
                "plaintext_env_retired_or_pending"}
    for s in _status()["systems"]:
        missing = required - set(s)
        assert not missing, f"{s['system']} missing contract fields: {missing}"


def test_umh_manifest_is_grandfathered_services_env_tpl():
    umh = next(s for s in _status()["systems"] if s["system"] == "UMH")
    assert umh["manifest_path"] == "services/.env.tpl"
    assert umh["vault"] == "UMH-Production"


def test_projections_use_env_op_tpl_and_bare_vaults():
    for s in _status()["systems"]:
        if s["role"] != "projection":
            continue
        assert s["manifest_path"] == ".env.op.tpl", f"{s['system']} projection manifest"
        assert s["vault"] == s["system"], f"{s['system']} vault should be its bare app name"


def test_every_system_refs_resolve_and_op_run_verified():
    for s in _status()["systems"]:
        assert s["refs_resolve"] is True, f"{s['system']} op:// refs must resolve"
        assert s["op_run_verified"] is True, f"{s['system']} op run must be verified"


def test_every_system_gitignores_plaintext_env():
    for s in _status()["systems"]:
        assert s["gitignore_protects_plaintext_env"] is True, f"{s['system']} must ignore .env"


def test_projection_protection_lives_on_operating_branch_not_side_branch():
    for s in _status()["systems"]:
        if s["role"] != "projection":
            continue
        assert s.get("safe_files_committed_on_operating_branch") is True, s["system"]
        assert s.get("operating_branch"), f"{s['system']} must declare its operating branch"
    side = _status()["temporary_side_branches"]
    assert "deleted" in side["final_state"].lower()
    assert "operating branch" in side["canonical_protection_location"].lower()


def test_no_secret_values_in_status_record():
    text = STATUS.read_text()
    for pat in SECRET_VALUE_PATTERNS:
        hits = pat.findall(text)
        assert not hits, f"secret-value pattern {pat.pattern} found in status JSON: {hits}"


def test_no_secret_values_in_protocol_doc():
    text = DOC.read_text()
    for pat in SECRET_VALUE_PATTERNS:
        hits = pat.findall(text)
        assert not hits, f"secret-value pattern {pat.pattern} found in protocol doc: {hits}"


def test_canonical_wrapper_exists_and_enforces_gates():
    assert WRAPPER.exists(), "scripts/op_run.sh must exist"
    body = WRAPPER.read_text()
    # the wrapper must implement each contract gate and use op run
    assert "op run" in body, "wrapper must load via op run"
    assert "op://" in body, "wrapper must validate op:// references"
    assert "diff --cached" in body, "wrapper must refuse when a plaintext .env is staged"
    assert "exec op run" in body, "wrapper must exec op run (never print resolved values)"


def test_plaintext_env_retirement_status_explicit_per_projection():
    for s in _status()["systems"]:
        if s["role"] != "projection":
            continue
        status = s["plaintext_env_retired_or_pending"]
        assert status, f"{s['system']} must state plaintext env retirement status"
        assert ("pending" in status.lower() or "retired" in status.lower()), s["system"]


# --- WP-P4-SECRETS-RETIRE-001: retirement was gated on an op-run boot smoke ---

RETIRE_DOC = REPO / "docs" / "PROJECTION_SECRETS_RETIREMENT_2026-07-05.md"


def test_retirement_block_present_and_gated():
    d = _status()
    block = d.get("plaintext_env_retirement")
    assert block, "status JSON must carry a plaintext_env_retirement block"
    assert block["packet"] == "WP-P4-SECRETS-RETIRE-001"
    # retirement must be gated on an op-run boot smoke, not a blind delete
    gate = block["precondition_gate"].lower()
    assert "op run" in gate and "boot" in gate, "retirement must be gated on op-run boot"
    assert "archive" in block["policy"].lower(), "policy must be archive-outside-git, not delete"
    assert set(block["repos_retired"]) == {"EntrepreneurOS", "CreatorOS", "LyfeOS"}


def test_each_projection_records_a_boot_smoke_before_retirement():
    for s in _status()["systems"]:
        if s["role"] != "projection":
            continue
        smoke = s.get("op_run_boot_smoke", "")
        assert "BOOT_OK" in smoke, f"{s['system']} must record a passing op-run boot smoke"
        assert "op run" in smoke.lower(), f"{s['system']} boot smoke must be via op run"


def test_retired_projections_say_retired_not_pending():
    """After WP-P4-SECRETS-RETIRE-001 all three projections must read 'retired', truthfully."""
    for s in _status()["systems"]:
        if s["role"] != "projection":
            continue
        status = s["plaintext_env_retired_or_pending"].lower()
        assert status.startswith("retired"), f"{s['system']} should be retired: {status!r}"
        # retirement must reference the outside-git archive location + a re-verified boot
        assert "_env_archive" in s["plaintext_env_retired_or_pending"], s["system"]
        assert "boot_ok" in status or "boot ok" in status, s["system"]


def test_retirement_doc_present_and_no_secret_values():
    assert RETIRE_DOC.exists(), "retirement governance doc must exist"
    text = RETIRE_DOC.read_text()
    for pat in SECRET_VALUE_PATTERNS:
        hits = pat.findall(text)
        assert not hits, f"secret-value pattern {pat.pattern} in retirement doc: {hits}"
