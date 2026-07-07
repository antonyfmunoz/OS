"""P4S-AI-OUTBOUND-VOICE-MESSAGE-001 compile-artifact validation — compile-mode gate.

Validates the compile-only deliverables for the AIOutboundVoiceMessage category
(the highest-risk voice category: AI renders a voice message in the authorizing
operator's own authorized voice for external send). The compile is
governance-and-consent design ONLY.

This test asserts, mechanically and fail-closed:
  - the JSON artifact parses and declares compile_only mode,
  - all required top-level sections are present,
  - the FIVE hard requirements are all present and phrased as hard requirements:
      HR1 approval-before-send (held gate, never auto-send),
      HR2 full audit/proof trail,
      HR3 no covert impersonation (recipient-facing disclosure mandatory),
      HR4 no third-party voice cloning (own voice only),
      HR5 external send is a high-risk, EXTERNAL, approval-required governed mutation,
  - NO mutation is actually registered: importing MutationRegistry, the name
    'ai_outbound_voice_send' is NOT in it, and the design flags registered=false,
  - NO activation- or implementation-authorizing language appears anywhere,
  - no first-tenant / device-hostname literal appears as global truth,
  - the companion doc exists and declares compile mode.

Mirrors tests/test_p4s31d_ambient_compile_artifacts.py: mechanical, fail-closed,
truthful about what "done" means for a compile packet.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_WORKTREE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _WORKTREE not in sys.path:
    sys.path.insert(0, _WORKTREE)

_ROOT = Path(_WORKTREE)
_ARTIFACT = _ROOT / "data/umh/voice/ai_outbound_voice_compile.json"
_DOC = _ROOT / "docs/AI_OUTBOUND_VOICE_COMPILE.md"

# First-tenant + device-hostname literals that must never appear as global truth.
# The authorizing operator is modeled as a server-resolved principal (a role),
# never a hardcoded person or device name.
_BANNED_LITERALS = ("antony", "afm", "munoz", "beast")

# Phrases that would authorize activation/implementation/rendering/sending.
# The packet is compile-only: it must never carry any of these (checked lowercase).
_ACTIVATION_PHRASES = (
    "activation approved",
    "authorized for activation",
    "cleared for activation",
    "activation is authorized",
    "activate now",
    "may activate",
    "begin implementation",
    "implementation may begin",
    "implementation approved",
    "rendering approved",
    "cleared to render",
    "cleared to send",
    "send approved",
    "greenlit",
    "go-live",
)

# Required top-level sections of the compile artifact.
_REQUIRED_KEYS = {
    "record",
    "compiled",
    "packet",
    "compile_only",
    "mode",
    "category",
    "category_definition",
    "activation_gate",
    "hard_requirements",
    "voice_authorization_model",
    "approval_gate",
    "audit_proof_trail",
    "anti_impersonation_disclosure_policy",
    "governed_mutation_design",
    "secret_credential_handling",
    "threat_model",
    "rollback",
    "forbidden_in_this_packet",
}

_MUTATION_NAME = "ai_outbound_voice_send"


def _load(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ── parse + compile mode ──────────────────────────────────────────────────────


def test_artifact_parses():
    assert _ARTIFACT.exists(), f"missing artifact {_ARTIFACT}"
    _load(_ARTIFACT)  # raises on bad JSON


def test_artifact_declares_compile_only():
    data = _load(_ARTIFACT)
    assert data.get("compile_only") is True, "artifact must flag compile_only=true"
    assert "compile_only" in data.get("mode", ""), "artifact mode must declare compile_only"
    assert "no activation authorized" in data.get("mode", "").lower(), (
        "artifact mode must state 'no activation authorized'"
    )


def test_activation_gate_is_closed():
    data = _load(_ARTIFACT)
    gate = data["activation_gate"]
    assert gate.get("activation_authorized") is False
    assert gate.get("rendering_authorized") is False
    assert gate.get("send_authorized") is False
    assert gate.get("clone_execution_authorized") is False
    assert gate.get("mutation_registration_authorized") is False


def test_doc_exists_and_declares_compile_mode():
    assert _DOC.exists(), "AI_OUTBOUND_VOICE_COMPILE.md missing"
    text = _DOC.read_text(encoding="utf-8").lower()
    assert "compile mode" in text, "doc must declare compile mode"
    assert "no activation authorized" in text, "doc must state no activation is authorized"


# ── required sections ─────────────────────────────────────────────────────────


def test_all_required_top_level_keys_present():
    data = _load(_ARTIFACT)
    missing = _REQUIRED_KEYS - set(data)
    assert not missing, f"artifact missing required top-level keys: {missing}"


def test_category_is_ai_outbound_voice_message():
    data = _load(_ARTIFACT)
    assert data["category"] == "AIOutboundVoiceMessage"


# ── the five hard requirements ────────────────────────────────────────────────


def test_all_five_hard_requirements_present():
    data = _load(_ARTIFACT)
    hr = data["hard_requirements"]
    for key in (
        "HR1_approval_before_send",
        "HR2_full_audit_trail",
        "HR3_no_covert_impersonation",
        "HR4_no_third_party_cloning",
        "HR5_external_send_is_high_risk_governed_mutation",
    ):
        assert key in hr, f"missing hard requirement {key}"
        assert hr[key].get("hard") is True, f"{key} must be flagged hard=true"
        assert hr[key].get("requirement"), f"{key} must carry a requirement statement"
        assert hr[key].get("phrasing"), f"{key} must carry hard-requirement phrasing"


def test_hr1_approval_before_send_is_a_held_gate_never_auto_send():
    data = _load(_ARTIFACT)
    hr1 = json.dumps(data["hard_requirements"]["HR1_approval_before_send"]).lower()
    assert "approval" in hr1 and "before any external send" in hr1, (
        "HR1 must require approval before any external send"
    )
    assert "held gate" in hr1, "HR1 must state it is a held gate"
    assert "never auto-send" in hr1 or "never an auto-send" in hr1, (
        "HR1 must state it is never auto-send"
    )
    # And the approval gate must have no auto_send path anywhere.
    gate = json.dumps(data["approval_gate"]).lower()
    assert "auto_send is not a field" in gate or "there is no auto-send path" in gate, (
        "approval_gate must explicitly deny any auto-send path"
    )


def test_hr2_full_audit_trail_is_required_and_precedes_send():
    data = _load(_ARTIFACT)
    hr2 = json.dumps(data["hard_requirements"]["HR2_full_audit_trail"]).lower()
    assert "audit" in hr2 and ("must" in hr2 or "required" in hr2), (
        "HR2 must require a full audit trail"
    )
    trail = json.dumps(data["audit_proof_trail"]).lower()
    assert "before" in trail and "send" in trail, (
        "audit trail must be created before send"
    )
    assert "immutable" in trail, "audit record must be immutable"


def test_hr3_no_covert_impersonation_and_disclosure_mandatory():
    data = _load(_ARTIFACT)
    hr3 = json.dumps(data["hard_requirements"]["HR3_no_covert_impersonation"]).lower()
    assert "no covert impersonation" in hr3, "HR3 must state no covert impersonation"
    assert "disclosure" in hr3, "HR3 must require recipient-facing disclosure"
    policy = data["anti_impersonation_disclosure_policy"]
    assert policy.get("hard") is True, "disclosure policy must be flagged hard=true"
    blob = json.dumps(policy).lower()
    assert "must" in blob and "disclosure" in blob, (
        "disclosure policy must be phrased as a hard requirement"
    )
    assert "no disclosure" in blob and "no send" in blob, (
        "policy must state: no disclosure, no send (fail-closed)"
    )


def test_hr4_no_third_party_voice_cloning():
    data = _load(_ARTIFACT)
    hr4 = json.dumps(data["hard_requirements"]["HR4_no_third_party_cloning"]).lower()
    assert "no third-party voice cloning" in hr4, "HR4 must state no third-party voice cloning"
    assert "own" in hr4, "HR4 must restrict to the operator's own voice"
    model = data["voice_authorization_model"]
    prohibition = model["third_party_cloning_prohibition"]
    assert prohibition.get("hard") is True
    assert "prohibited" in json.dumps(prohibition).lower()
    # The grant must carry a self-voice attestation invariant.
    grant = json.dumps(model["VoiceAuthorizationGrant"]).lower()
    assert "self_voice_attestation" in grant, (
        "VoiceAuthorizationGrant must carry self_voice_attestation"
    )
    assert "revocable" in grant or "revoked_at" in grant, (
        "the voice authorization grant must be revocable"
    )
    assert "per-purpose" in grant or "purpose_scope" in grant, (
        "the grant must be per-purpose, not blanket"
    )


def test_hr5_external_send_is_high_risk_governed_mutation():
    data = _load(_ARTIFACT)
    hr5 = json.dumps(data["hard_requirements"]["HR5_external_send_is_high_risk_governed_mutation"]).lower()
    assert "high" in hr5 and "external" in hr5 and "approval" in hr5, (
        "HR5 must state high-risk, EXTERNAL, approval-required"
    )
    spec = data["governed_mutation_design"]["spec_design"]
    assert spec["name"] == _MUTATION_NAME
    assert spec["risk_level"] == "high"
    assert spec["blast_radius"] == "external"
    assert spec["require_approval"] is True
    assert spec["degraded_mode_allowed"] is False, (
        "external irreversible send must fail closed when control plane is down"
    )


# ── the mutation is NOT registered ────────────────────────────────────────────


def test_mutation_is_not_registered_in_registry():
    """Hard gate: importing the live MutationRegistry, ai_outbound_voice_send
    must NOT be registered. This packet designs the spec; it never registers it."""
    from substrate.organism.mutation_registry import MutationRegistry

    registry = MutationRegistry()
    assert not registry.is_registered(_MUTATION_NAME), (
        f"{_MUTATION_NAME} must NOT be registered — compile-only packet never "
        "registers the mutation"
    )
    assert registry.lookup(_MUTATION_NAME) is None
    names = {s.name for s in registry.all_specs()}
    assert _MUTATION_NAME not in names, (
        f"{_MUTATION_NAME} leaked into the registry spec set"
    )


def test_mutation_source_file_does_not_define_the_spec():
    """The registry SOURCE must not define ai_outbound_voice_send anywhere."""
    src = (_ROOT / "substrate/organism/mutation_registry.py").read_text(encoding="utf-8")
    assert _MUTATION_NAME not in src, (
        f"{_MUTATION_NAME} must not appear in mutation_registry.py source"
    )


def test_design_flags_registered_false():
    data = _load(_ARTIFACT)
    gmd = data["governed_mutation_design"]
    assert gmd.get("registered") is False, "governed_mutation_design.registered must be false"
    not_done = json.dumps(gmd.get("not_done_here", [])).lower()
    assert "no mutationspec" in not_done or "no registration" in not_done, (
        "design must state the mutation is not registered/wired"
    )


# ── no activation-authorizing language ────────────────────────────────────────


def test_no_activation_authorizing_language_in_artifact():
    text = json.dumps(_load(_ARTIFACT)).lower()
    for phrase in _ACTIVATION_PHRASES:
        assert phrase not in text, (
            f"artifact carries activation/render/send-authorizing phrase {phrase!r} — "
            "compile mode must never authorize activation, rendering, or sending"
        )


def test_no_activation_authorizing_language_in_doc():
    text = _DOC.read_text(encoding="utf-8").lower()
    for phrase in _ACTIVATION_PHRASES:
        assert phrase not in text, f"doc carries activation-authorizing phrase {phrase!r}"


# ── secret / credential handling ──────────────────────────────────────────────


def test_credentials_go_through_1password():
    data = _load(_ARTIFACT)
    blob = json.dumps(data["secret_credential_handling"]).lower()
    assert "1password" in blob and "op run" in blob, (
        "provider credentials must flow through 1Password op run"
    )
    assert "credential-injection.md" in blob, "must bind to the Credential Injection Law"


# ── tenant / device safety ────────────────────────────────────────────────────


def test_no_tenant_or_device_literal_in_artifact():
    text = json.dumps(_load(_ARTIFACT)).lower()
    for literal in _BANNED_LITERALS:
        assert literal not in text, (
            f"artifact carries banned literal {literal!r} — the authorizing "
            "operator is a server-resolved principal, never a hardcoded literal"
        )


def test_doc_free_of_tenant_and_device_literals():
    text = _DOC.read_text(encoding="utf-8").lower()
    for literal in _BANNED_LITERALS:
        assert literal not in text, (
            f"AI_OUTBOUND_VOICE_COMPILE.md carries banned literal {literal!r}"
        )
