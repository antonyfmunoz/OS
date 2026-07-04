"""Canonical approval authority (WP-P1-007).

One auditable authority that every approval origin submits to or projects from.
This module does NOT introduce a new store — the durable homes remain the
ExecutionCoordinator PlanStore (per-plan JSON + lifecycle JSONL) and the
OperatorApprovalGate append-only JSONL. What it adds is:

  1. Pure, lossless round-trip adapters between every legacy approval shape and
     the canonical ``substrate.types.ApprovalRequest``.
  2. An ``ApprovalAuthority`` facade that projects a single unified pending view
     across origins and resolves multi-surface approvals with compare-and-swap
     (folded from OperatorApprovalGate) so no approval double-resolves.

Fail-closed by construction: unknown source states coerce to PENDING (never
approved); a resolve against an unknown/stale id returns False; a missing
handler raises rather than silently no-oping.

Layer: substrate/. Imports nothing from transports/ or services/.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from substrate.types import (
    ApprovalOrigin,
    ApprovalRequest,
    ApprovalState,
    RiskClass,
)

# ── helpers ──────────────────────────────────────────────────────────────────


def _coerce_risk(value: str) -> RiskClass:
    """Map any risk string (risk_class or risk_level vocab) onto RiskClass.

    Deterministic; fail-closed to HIGH for unknown values so an unrecognized
    risk never under-classifies into an auto-approvable band.
    """
    v = (value or "").strip().lower()
    try:
        return RiskClass(v)
    except ValueError:
        # legacy aliases
        if v in ("negligible", "trivial", "none"):
            return RiskClass.NEGLIGIBLE
        return RiskClass.HIGH


def _epoch_to_dt(value: Any) -> datetime | None:
    """Convert an epoch float/int (0 or falsy → None) to an aware datetime."""
    if not value:
        return None
    try:
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def _dt_to_epoch(value: datetime | None) -> float:
    """Convert an aware datetime back to epoch float (None → 0.0)."""
    if value is None:
        return 0.0
    return value.timestamp()


def _canonical_id(native_id: Any) -> dict[str, str]:
    """Build the approval_id kwarg for ApprovalRequest.

    If the source has a native id, derive a stable ``apr-{id}`` so a round-trip
    is deterministic; otherwise return an empty dict so the model's
    default_factory mints a fresh id (passing None would fail str validation).
    """
    nid = str(native_id or "").strip()
    return {"approval_id": f"apr-{nid}"} if nid else {}


# ── ApprovalPacket  (substrate/organism/approval_gate.py) ────────────────────


def from_approval_packet(packet: Any) -> ApprovalRequest:
    """ApprovalPacket → canonical. Preserves packet_id as source_id."""
    status = getattr(packet, "status", None)
    status_val = status.value if hasattr(status, "value") else str(status or "pending")
    return ApprovalRequest(
        **_canonical_id(getattr(packet, "packet_id", "")),
        source_origin=ApprovalOrigin.SANDBOX_GATE,
        source_id=getattr(packet, "packet_id", ""),
        source_channel="operator_approval_gate",
        title=getattr(packet, "candidate_title", ""),
        description=getattr(packet, "candidate_description", ""),
        risk_class=_coerce_risk(getattr(packet, "risk_class", "low")),
        state=ApprovalState.coerce(status_val),
        decided_by=getattr(packet, "decided_by", ""),
        created_at=_epoch_to_dt(getattr(packet, "created_at", 0)) or datetime.now(timezone.utc),
        expires_at=_epoch_to_dt(getattr(packet, "expires_at", 0)),
        decided_at=_epoch_to_dt(getattr(packet, "decided_at", 0)),
        claimed_by_surface=getattr(packet, "claimed_by_surface", ""),
        resolved_by_surface=getattr(packet, "resolved_by_surface", ""),
        rejection_reason=getattr(packet, "rejection_reason", ""),
        operator_input=getattr(packet, "operator_input", ""),
        metadata={
            "expected_delta": getattr(packet, "expected_delta", ""),
            "affected_files": getattr(packet, "affected_files", []),
            "governance_score": getattr(packet, "governance_score", 0.0),
            "sandbox_branch_name": getattr(packet, "sandbox_branch_name", ""),
        },
    )


# ── ApprovalInterceptRequest  (executors/approval_intercept.py) ──────────────


def from_intercept_request(req: Any) -> ApprovalRequest:
    """ApprovalInterceptRequest → canonical."""
    return ApprovalRequest(
        **_canonical_id(getattr(req, "approval_id", "")),
        source_origin=ApprovalOrigin.EXECUTOR_INTERCEPT,
        source_id=getattr(req, "approval_id", ""),
        source_channel="approval_intercept_service",
        operation=getattr(req, "operation", ""),
        description=getattr(req, "reason", ""),
        risk_class=_coerce_risk(getattr(req, "risk_class", "high")),
        state=ApprovalState.coerce(str(getattr(req, "status", "pending"))),
        decided_by=getattr(req, "decided_by", ""),
        session_id=getattr(req, "execution_id", ""),
        created_at=_epoch_to_dt(getattr(req, "requested_at", 0)) or datetime.now(timezone.utc),
        expires_at=_epoch_to_dt(getattr(req, "expires_at", 0)),
        decided_at=_epoch_to_dt(getattr(req, "decided_at", 0)),
        rejection_reason=getattr(req, "rejection_reason", ""),
        metadata={
            "executor_type": getattr(req, "executor_type", ""),
            "request_id": getattr(req, "request_id", ""),
            "details": getattr(req, "details", {}),
            "resolution_metadata": getattr(req, "resolution_metadata", {}),
        },
    )


# ── CoordinatorExecutionPlan  (execution_coordinator.py) — DURABLE AUTHORITY ──


def from_coordinator_plan(plan: Any) -> ApprovalRequest:
    """CoordinatorExecutionPlan → canonical. Maps approval_state (denied→rejected)."""
    return ApprovalRequest(
        **_canonical_id(getattr(plan, "execution_plan_id", "")),
        source_origin=ApprovalOrigin.COORDINATOR,
        source_id=getattr(plan, "execution_plan_id", ""),
        source_channel="execution_coordinator",
        title=getattr(plan, "description", ""),
        description=getattr(plan, "description", ""),
        risk_class=_coerce_risk(getattr(plan, "risk_class", "low")),
        state=ApprovalState.coerce(getattr(plan, "approval_state", "pending")),
        session_id=getattr(plan, "session_id", ""),
        created_at=_epoch_to_dt(getattr(plan, "created_at", 0)) or datetime.now(timezone.utc),
        decided_at=_epoch_to_dt(getattr(plan, "approved_at", 0)),
        proof_id=getattr(plan, "proof_id", ""),
        version=int(getattr(plan, "metadata", {}).get("approval_version", 0)),
        metadata={
            "source_workpacket_id": getattr(plan, "source_workpacket_id", ""),
            "target_executor": getattr(plan, "target_executor", ""),
            "profile_id": getattr(plan, "profile_id", ""),
            "plan_status": getattr(plan, "status", ""),
        },
    )


# ── organism ApprovalStore dict record  (organism/approval_store.py) ─────────


def from_organism_record(record: dict[str, Any]) -> ApprovalRequest:
    """organism ApprovalStore JSONL record → canonical (risk_level→risk_class)."""
    created = record.get("created_at")
    created_dt = None
    if isinstance(created, str) and created:
        try:
            created_dt = datetime.fromisoformat(created)
        except ValueError:
            created_dt = None
    return ApprovalRequest(
        **_canonical_id(record.get("id", "")),
        source_origin=ApprovalOrigin.ORGANISM_STORE,
        source_id=str(record.get("id", "")),
        source_channel="organism_approval_store",
        title=record.get("title", ""),
        description=record.get("description", ""),
        risk_class=_coerce_risk(record.get("risk_level", "medium")),
        state=ApprovalState.coerce(str(record.get("status", "pending"))),
        decided_by=record.get("decided_by") or "",
        requester_identity=record.get("agent", ""),
        created_at=created_dt or datetime.now(timezone.utc),
        trace_id=record.get("trace_id") or "",
        metadata={
            "signal_content": record.get("signal_content", ""),
            "governance_rationale": record.get("governance_rationale", ""),
        },
    )


# ── UnifiedApproval projection  (workstation/unified_approval_runtime.py) ────


def to_unified_dict(req: ApprovalRequest) -> dict[str, Any]:
    """Canonical → the dict shape the unified read projection consumes.

    Exposes the alias keys UnifiedApprovalRuntime's duck-typed extractors probe
    (``work_id``/``approval_id`` for id, ``risk_class`` for risk,
    ``created_at``/``waiting_since`` for time) so a canonical record survives
    coercion into a UnifiedApproval.
    """
    return {
        "approval_id": req.approval_id,
        "work_id": req.source_id,
        "title": req.title,
        "description": req.description,
        "risk_class": req.risk_class.value,
        "created_at": _dt_to_epoch(req.created_at),
        "waiting_since": _dt_to_epoch(req.created_at),
        "source_type": req.source_origin.value,
        "status": req.status,
    }


# ── The unified authority facade ─────────────────────────────────────────────


class ApprovalAuthority:
    """Single auditable authority projecting every origin into one pending view.

    Wraps the durable ExecutionCoordinator PlanStore (plan lifecycle) and the
    OperatorApprovalGate (interactive multi-surface CAS). Neither is replaced;
    this is the convergence seam that reads across them and resolves with
    compare-and-swap. No new store is created.

    All methods fail closed: a resolve/claim against an unknown id returns
    False; ``pending()`` never raises on a single bad source (it skips it).
    """

    def __init__(
        self,
        *,
        operator_gate: Any | None = None,
        coordinator: Any | None = None,
        organism_store: Any | None = None,
        intercept_service: Any | None = None,
    ) -> None:
        self._gate = operator_gate
        self._coordinator = coordinator
        self._organism_store = organism_store
        self._intercept = intercept_service

    # -- unified pending projection ------------------------------------------

    def pending(self) -> list[ApprovalRequest]:
        """Return every pending approval across all wired origins, canonicalized.

        This is the "what is pending approval?" query. Spans ≥3 channels when
        the corresponding sources are wired. A failing source is skipped, never
        fatal — the unified view degrades gracefully rather than going blank.
        """
        out: list[ApprovalRequest] = []

        gate = self._gate
        if gate is not None:
            try:
                for packet in gate.pending_packets():
                    out.append(from_approval_packet(packet))
            except Exception:  # noqa: BLE001 — one bad source must not blank the view
                pass

        coord = self._coordinator
        if coord is not None:
            try:
                store = getattr(coord, "_plan_store", None)
                plans = store.awaiting_approval() if store is not None else []
                for plan in plans:
                    out.append(from_coordinator_plan(plan))
            except Exception:  # noqa: BLE001
                pass

        store = self._organism_store
        if store is not None:
            try:
                for record in store.list_pending():
                    out.append(from_organism_record(record))
            except Exception:  # noqa: BLE001
                pass

        intercept = self._intercept
        if intercept is not None:
            try:
                for req in intercept.pending():
                    out.append(from_intercept_request(req))
            except Exception:  # noqa: BLE001
                pass

        return out

    def list_pending(self) -> list[ApprovalRequest]:
        """Alias for the minimal store contract expected by callers/tests."""
        return self.pending()

    @property
    def pending_count(self) -> int:
        return len(self.pending())

    # -- multi-surface CAS resolution ----------------------------------------

    def claim(self, source_id: str, surface: str) -> bool:
        """Atomically claim a pending approval by its native source id.

        Delegates to OperatorApprovalGate's compare-and-swap. First valid claim
        wins; a claim against an unknown/already-claimed/non-pending id returns
        False (fail-closed).
        """
        gate = self._gate
        if gate is None or not source_id:
            return False
        try:
            return bool(gate.claim_approval(source_id, surface))
        except Exception:  # noqa: BLE001
            return False

    def resolve(
        self,
        source_id: str,
        decision: str,
        surface: str,
        *,
        decided_by: str = "operator",
        input_text: str = "",
    ) -> bool:
        """Resolve a claimed approval with compare-and-swap.

        ``decision`` is one of "approve" | "reject" | "provide_input". Only the
        claiming surface may resolve; a resolve against an unknown/stale id, or
        from a non-claiming surface, returns False (fail-closed — no
        double-resolve, no silent success).
        """
        gate = self._gate
        if gate is None or not source_id:
            return False
        if decision not in ("approve", "reject", "provide_input"):
            return False
        try:
            return bool(
                gate.resolve_approval(
                    source_id,
                    decision,
                    surface,
                    input_text=input_text,
                    decided_by=decided_by,
                )
            )
        except Exception:  # noqa: BLE001
            return False

    # -- approval_port handler (single trust-boundary entry) ------------------

    def submit_port_decision(self, request: Any) -> dict[str, Any]:
        """Resolve a decision arriving through the typed ``approval_port``.

        ``request`` is an ``ApprovalPortRequest`` (decision_id, approved, reason,
        decided_by, surface). This is the ONE seam every surface (Discord,
        cockpit, API) resolves through — so the record a surface displays is the
        record it resolves, regardless of which underlying store owns it.

        Resolution order (deterministic): try the organism ApprovalStore that
        governance-blocked signals originate in (the Discord alert origin), then
        the OperatorApprovalGate CAS path. Fail-closed: if no store recognizes
        the id, returns ``success=False`` — the decision is refused, never
        silently dropped.
        """
        decision_id = str(getattr(request, "decision_id", "") or "")
        approved = bool(getattr(request, "approved", False))
        reason = str(getattr(request, "reason", "") or "")
        decided_by = str(getattr(request, "decided_by", "operator") or "operator")
        surface = str(getattr(request, "surface", "") or "port")
        decision = "approve" if approved else "reject"

        if not decision_id:
            return {"success": False, "detail": "empty decision_id"}

        # 1) organism ApprovalStore — the Discord alert-origin store. Resolving
        #    here means the button resolves the SAME record it displayed.
        store = self._organism_store
        if store is not None:
            try:
                result = store.decide(
                    decision_id,
                    "approved" if approved else "rejected",
                    decided_by=decided_by,
                )
                if result is not None:
                    return {
                        "success": True,
                        "decision_id": decision_id,
                        "state": result.get("status", ""),
                        "detail": f"resolved in organism store via {surface}",
                    }
            except Exception:  # noqa: BLE001
                pass

        # 2) OperatorApprovalGate CAS path (claim then resolve).
        gate = self._gate
        if gate is not None:
            try:
                gate.claim_approval(decision_id, surface)
                ok = gate.resolve_approval(
                    decision_id,
                    decision,
                    surface,
                    input_text=reason,
                    decided_by=decided_by,
                )
                if ok:
                    return {
                        "success": True,
                        "decision_id": decision_id,
                        "state": "approved" if approved else "rejected",
                        "detail": f"resolved via gate CAS ({surface})",
                    }
            except Exception:  # noqa: BLE001
                pass

        # Fail-closed: nobody owned this id.
        return {
            "success": False,
            "decision_id": decision_id,
            "detail": "no authority recognized decision_id (refused, fail-closed)",
        }


# ── module-level default authority + port registration ───────────────────────

_default_authority: ApprovalAuthority | None = None


def get_approval_authority() -> ApprovalAuthority:
    """Return the process-wide canonical approval authority, building it lazily.

    Wires the durable/interactive stores that exist without importing any
    transport. Safe to call from substrate startup.
    """
    global _default_authority
    if _default_authority is not None:
        return _default_authority

    operator_gate = None
    organism_store = None
    try:
        from substrate.organism.approval_gate import OperatorApprovalGate

        operator_gate = OperatorApprovalGate()
    except Exception:  # noqa: BLE001
        operator_gate = None
    try:
        from substrate.organism.approval_store import ApprovalStore

        organism_store = ApprovalStore()
    except Exception:  # noqa: BLE001
        organism_store = None

    _default_authority = ApprovalAuthority(
        operator_gate=operator_gate,
        organism_store=organism_store,
    )
    return _default_authority


def register_with_port() -> None:
    """Register the canonical authority behind the typed ``approval_port``.

    After this call the vestigial port becomes load-bearing: every surface that
    submits through ``approval_port.submit_approval`` resolves the same
    canonical record. Idempotent.
    """
    from substrate.sockets.approval_port import register_approval_handler

    authority = get_approval_authority()
    register_approval_handler(authority.submit_port_decision)
