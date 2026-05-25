"""Distribution API — channel status, intake, approval, and first-boot endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from substrate.distribution.distributor import DistributionLayer
from substrate.distribution.first_boot import check_first_boot, mark_first_boot_complete

router = APIRouter(prefix="/api/umh/distribution", tags=["distribution"])

try:
    from transports.channels.channel import get_channel_router
    _channel_router = get_channel_router()
except Exception:
    _channel_router = None

_distributor = DistributionLayer(channel_router=_channel_router)


def wire_pipeline(submit_fn: Any) -> None:
    """Called at startup to connect the pipeline to the distribution layer."""
    _distributor.set_pipeline(submit_fn)


class ChannelIngestRequest(BaseModel):
    content: str = Field(max_length=2000)
    source_channel: str = "api"
    risk_class: str = "READ_ONLY"
    adapter_name: str = "shell"
    pre_approved: bool = False


class ApprovalResponse(BaseModel):
    approval_id: str
    approved: bool


@router.post("/ingest")
async def channel_ingest(req: ChannelIngestRequest):
    """Ingest a signal from any channel through the distribution layer."""
    from substrate.governance.risk_classes import RiskClass
    try:
        risk = RiskClass[req.risk_class]
    except KeyError:
        risk = RiskClass.READ_ONLY

    return _distributor.ingest(
        content=req.content,
        source_channel=req.source_channel,
        risk_class=risk,
        adapter_name=req.adapter_name,
        pre_approved=req.pre_approved,
    )


@router.post("/approve")
async def receive_approval(req: ApprovalResponse):
    """Receive an approval/denial for a pending request."""
    found = _distributor.receive_approval(req.approval_id, req.approved)
    return {"processed": found, "approval_id": req.approval_id}


@router.get("/channels")
async def channel_status():
    """Get status of all configured distribution channels."""
    return _distributor.channel_status()


@router.get("/stats")
async def distribution_stats():
    """Get distribution layer statistics."""
    return _distributor.stats()


@router.get("/events")
async def recent_events(limit: int = 20):
    """Get recent distribution events."""
    return _distributor.recent_events(limit=limit)


@router.get("/first-boot")
async def first_boot_status():
    """Check if system needs first-boot onboarding."""
    return check_first_boot().to_dict()


@router.post("/first-boot/complete")
async def complete_first_boot():
    """Mark first boot as complete."""
    mark_first_boot_complete()
    return {"status": "complete"}
