"""WP-P1-007 — unified approval authority behavior tests.

Proves the convergence guarantees:
  * approvals from ≥3 origin channels land in / project through one authority;
  * a single "what is pending" query returns them all;
  * multi-surface claim/resolve CAS prevents double-resolution;
  * a Discord-style approval resolves the SAME record it displayed (the store
    mismatch is fixed);
  * an unregistered approval_port fails CLOSED (raises), never silently no-ops;
  * the executor with no intercept service rejects rather than auto-approves.
"""

from __future__ import annotations

import tempfile

import pytest

from substrate.organism.approval_authority import ApprovalAuthority
from substrate.organism.approval_gate import OperatorApprovalGate
from substrate.organism.approval_store import ApprovalStore
from substrate.sockets import approval_port
from substrate.sockets.approval_port import ApprovalPortUnavailable, submit_approval


@pytest.fixture(autouse=True)
def _reset_port():
    """Each test starts with no handler registered on the port."""
    approval_port._approval_fn = None
    yield
    approval_port._approval_fn = None


def _gate() -> OperatorApprovalGate:
    return OperatorApprovalGate(store_dir=tempfile.mkdtemp())


def _store() -> ApprovalStore:
    return ApprovalStore(store_dir=tempfile.mkdtemp())


def _packet(gate: OperatorApprovalGate, *, title: str = "t", risk_class: str = "high"):
    """Create an ApprovalPacket with the gate's full positional signature."""
    return gate.create_packet(
        "c1",
        "src",
        title,
        "desc",
        [],
        "",
        "",
        0.0,
        0.0,
        "approve",
        [],
        [],
        "",
        "",
        "",
        risk_class=risk_class,
    )


# ── ≥3-channel unified pending query ─────────────────────────────────────────


def test_pending_spans_three_channels():
    gate = _gate()
    store = _store()

    # Channel 1: OperatorApprovalGate packet (sandbox/Discord surface).
    _packet(gate, title="gate approval", risk_class="high")
    # Channel 2: organism ApprovalStore (governance-blocked signal → Discord alert origin).
    store.create_approval(title="signal approval", description="blocked", risk_level="medium")

    # Channel 3: executor intercept service.
    from substrate.organism.executors.approval_intercept import get_approval_intercept_service

    intercept = get_approval_intercept_service()
    intercept.request_approval(
        execution_id="e1",
        request_id="r1",
        executor_type="coder",
        operation="write",
        risk_class="high",
        reason="needs approval",
    )

    authority = ApprovalAuthority(
        operator_gate=gate, organism_store=store, intercept_service=intercept
    )
    pending = authority.pending()

    origins = {p.source_origin.value for p in pending}
    assert len(pending) >= 3, f"expected >=3 pending, got {len(pending)}"
    assert {"sandbox_gate", "organism_store", "executor_intercept"} <= origins, origins


def test_pending_degrades_not_blanks_on_bad_source():
    """A failing source is skipped; the view still returns the healthy ones."""

    class _Broken:
        def pending_packets(self):
            raise RuntimeError("boom")

    store = _store()
    store.create_approval(title="ok", description="d", risk_level="low")
    authority = ApprovalAuthority(operator_gate=_Broken(), organism_store=store)
    pending = authority.pending()
    assert len(pending) == 1
    assert pending[0].source_origin.value == "organism_store"


# ── multi-surface CAS ────────────────────────────────────────────────────────


def test_cas_prevents_double_resolution():
    gate = _gate()
    pkt = _packet(gate, title="race", risk_class="high")
    authority = ApprovalAuthority(operator_gate=gate)

    # Two surfaces race to claim; only one wins.
    won_a = authority.claim(pkt.packet_id, "discord")
    won_b = authority.claim(pkt.packet_id, "cockpit")
    assert won_a is True and won_b is False, "only one surface may claim"

    # The non-claiming surface cannot resolve.
    assert authority.resolve(pkt.packet_id, "approve", "cockpit") is False
    # The claiming surface resolves once.
    assert authority.resolve(pkt.packet_id, "approve", "discord") is True
    # A second resolve is refused (already resolved).
    assert authority.resolve(pkt.packet_id, "reject", "discord") is False


def test_resolve_unknown_id_fails_closed():
    authority = ApprovalAuthority(operator_gate=_gate())
    assert authority.resolve("does-not-exist", "approve", "discord") is False
    assert authority.claim("does-not-exist", "discord") is False


def test_resolve_invalid_decision_rejected():
    gate = _gate()
    pkt = _packet(gate, title="x", risk_class="low")
    authority = ApprovalAuthority(operator_gate=gate)
    authority.claim(pkt.packet_id, "discord")
    assert authority.resolve(pkt.packet_id, "sudo-approve", "discord") is False


# ── approval_port fail-closed ────────────────────────────────────────────────


def test_unregistered_port_raises_fail_closed():
    with pytest.raises(ApprovalPortUnavailable):
        submit_approval("some-id", True)


def test_registered_port_resolves():
    store = _store()
    rec = store.create_approval(title="deploy", description="ship", risk_level="high")
    authority = ApprovalAuthority(organism_store=store)
    approval_port.register_approval_handler(authority.submit_port_decision)

    resp = submit_approval(rec["id"], True, decided_by="op", surface="cockpit")
    assert resp.success is True
    assert resp.state == "approved"


def test_port_unknown_id_fails_closed_not_raise():
    """A registered handler that doesn't own the id returns success=False (the
    decision is refused, not silently applied) — but does not raise."""
    authority = ApprovalAuthority(organism_store=_store())
    approval_port.register_approval_handler(authority.submit_port_decision)
    resp = submit_approval("unknown-id", True)
    assert resp.success is False


# ── Discord same-record round-trip (store mismatch fixed) ────────────────────


def test_discord_resolves_same_record_it_displayed():
    """The Discord alert originates in the organism ApprovalStore. Resolving
    through the port must mark THAT record resolved — previously the button
    targeted a different store and silently failed."""
    store = _store()
    rec = store.create_approval(title="alert", description="d", risk_level="high")
    displayed_id = rec["id"]  # the id the Discord button is built with

    authority = ApprovalAuthority(organism_store=store)
    approval_port.register_approval_handler(authority.submit_port_decision)

    # Simulate the Discord approve button.
    resp = submit_approval(displayed_id, True, decided_by="discord-user", surface="discord")
    assert resp.success is True

    # The SAME record is now resolved in the store it was displayed from.
    after = [a for a in store.list_approvals() if a["id"] == displayed_id][0]
    assert after["status"] == "approved"
    assert after["decided_by"] == "discord-user"


# ── executor fail-closed on missing intercept ────────────────────────────────


def test_executor_blocks_when_intercept_service_missing(monkeypatch):
    """ExecutorRuntime.request_approval must BLOCK (not auto-approve) when the
    intercept service cannot be obtained."""
    from substrate.organism import executor_runtime as er

    rt = er.ExecutorRuntime(data_dir=tempfile.mkdtemp())
    request = rt.create_request(
        execution_plan_id="expl-1",
        executor_type="coder",
        risk_class="high",
        metadata={"operation": "write"},
    )

    # Force the intercept-service lookup to fail.
    import substrate.organism.executors.approval_intercept as ai

    def _boom():
        raise RuntimeError("service down")

    monkeypatch.setattr(ai, "get_approval_intercept_service", _boom)

    approved, message = rt.request_approval(request, reason="needs approval")
    assert approved is False, "missing intercept service must NOT auto-approve"
    assert "blocked" in message.lower() or "unavailable" in message.lower()
