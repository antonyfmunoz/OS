"""Phase 87A artifact sync policies — what gets copied where.

Defines default sync policies for code, data, config, models,
media, logs, credentials, and caches across the node topology.

No execution. No mutation. No adapter calls. No LLM calls.
No network listeners. No secrets.
"""

from __future__ import annotations

from typing import Any

from umh.distributed.contracts import (
    ArtifactSyncDirection,
    ArtifactSyncPolicy,
    ArtifactType,
    RuntimeNodeType,
    _dist_id,
    normalize_artifact_type,
    normalize_sync_direction,
)


def build_default_sync_policies() -> list[ArtifactSyncPolicy]:
    return [
        ArtifactSyncPolicy(
            policy_id=_dist_id("sync"),
            name="Code Sync (Git)",
            artifact_type=ArtifactType.CODE,
            direction=ArtifactSyncDirection.BIDIRECTIONAL,
            source_node_type=RuntimeNodeType.LOCAL_PC,
            target_node_type=RuntimeNodeType.VPS,
            sync_on_change=True,
            exclude_patterns=[
                ".env",
                ".env.*",
                "*.pyc",
                "__pycache__/",
                "node_modules/",
                ".git/",
                "*.sqlite",
            ],
            description="Git-based code sync between Local PC and VPS via GitHub",
            metadata={"method": "git_push_pull", "remote": "github"},
        ),
        ArtifactSyncPolicy(
            policy_id=_dist_id("sync"),
            name="Data Exports (Local → VPS)",
            artifact_type=ArtifactType.DATA,
            direction=ArtifactSyncDirection.LOCAL_TO_VPS,
            source_node_type=RuntimeNodeType.LOCAL_PC,
            target_node_type=RuntimeNodeType.VPS,
            sync_on_change=False,
            sync_on_schedule=True,
            max_size_mb=500,
            description="Data exports (AI chat archives, social exports) from Local PC to VPS for processing",
        ),
        ArtifactSyncPolicy(
            policy_id=_dist_id("sync"),
            name="Config Sync",
            artifact_type=ArtifactType.CONFIG,
            direction=ArtifactSyncDirection.BIDIRECTIONAL,
            source_node_type=RuntimeNodeType.LOCAL_PC,
            target_node_type=RuntimeNodeType.VPS,
            sync_on_change=True,
            exclude_patterns=[".env", "*.key", "*.pem", "credentials.*"],
            description="Configuration files (non-secret) synced between nodes",
        ),
        ArtifactSyncPolicy(
            policy_id=_dist_id("sync"),
            name="Model Artifacts (VPS → Local)",
            artifact_type=ArtifactType.MODEL,
            direction=ArtifactSyncDirection.VPS_TO_LOCAL,
            source_node_type=RuntimeNodeType.VPS,
            target_node_type=RuntimeNodeType.LOCAL_PC,
            sync_on_change=False,
            max_size_mb=2000,
            description="Trained model weights from VPS/cloud to Local PC for inference",
            metadata={"method": "scp_or_rsync"},
        ),
        ArtifactSyncPolicy(
            policy_id=_dist_id("sync"),
            name="Media Assets (Local → VPS)",
            artifact_type=ArtifactType.MEDIA,
            direction=ArtifactSyncDirection.LOCAL_TO_VPS,
            source_node_type=RuntimeNodeType.LOCAL_PC,
            target_node_type=RuntimeNodeType.VPS,
            sync_on_change=False,
            sync_on_schedule=True,
            max_size_mb=5000,
            description="Edited media, thumbnails, brand assets from Local PC to VPS for distribution",
        ),
        ArtifactSyncPolicy(
            policy_id=_dist_id("sync"),
            name="Log Collection (VPS → Archive)",
            artifact_type=ArtifactType.LOG,
            direction=ArtifactSyncDirection.NO_SYNC,
            source_node_type=RuntimeNodeType.VPS,
            target_node_type=RuntimeNodeType.VPS,
            description="Logs stay on VPS — no sync needed (VPS is primary log host)",
            metadata={"retention_days": 30},
        ),
        ArtifactSyncPolicy(
            policy_id=_dist_id("sync"),
            name="Credentials (No Sync)",
            artifact_type=ArtifactType.CREDENTIAL,
            direction=ArtifactSyncDirection.NO_SYNC,
            source_node_type=RuntimeNodeType.VPS,
            target_node_type=RuntimeNodeType.VPS,
            exclude_patterns=["*"],
            description="Credentials NEVER synced — each node has its own .env",
        ),
        ArtifactSyncPolicy(
            policy_id=_dist_id("sync"),
            name="Cache (No Sync)",
            artifact_type=ArtifactType.CACHE,
            direction=ArtifactSyncDirection.NO_SYNC,
            source_node_type=RuntimeNodeType.VPS,
            target_node_type=RuntimeNodeType.VPS,
            description="Caches are node-local — rebuilt on each node independently",
        ),
    ]


def get_sync_policy_for_artifact(
    artifact_type: str | ArtifactType,
    policies: list[ArtifactSyncPolicy] | None = None,
) -> ArtifactSyncPolicy | None:
    if policies is None:
        policies = build_default_sync_policies()
    at = normalize_artifact_type(artifact_type)
    for p in policies:
        if p.artifact_type == at:
            return p
    return None


def should_sync(
    artifact_type: str | ArtifactType,
    policies: list[ArtifactSyncPolicy] | None = None,
) -> bool:
    policy = get_sync_policy_for_artifact(artifact_type, policies)
    if policy is None:
        return False
    return policy.direction != ArtifactSyncDirection.NO_SYNC


def get_credential_policy(
    policies: list[ArtifactSyncPolicy] | None = None,
) -> ArtifactSyncPolicy | None:
    return get_sync_policy_for_artifact(ArtifactType.CREDENTIAL, policies)


def classify_artifact(
    name: str,
    description: str | None = None,
) -> ArtifactType:
    key = (name + " " + (description or "")).lower()

    _MAP: list[tuple[list[str], ArtifactType]] = [
        (["credential", "secret", "key", "password", "token", ".env"], ArtifactType.CREDENTIAL),
        (["model", "weights", "checkpoint", "onnx", "pytorch"], ArtifactType.MODEL),
        (["log", "trace", "audit", "journal"], ArtifactType.LOG),
        (["cache", "tmp", "temp", "__pycache__"], ArtifactType.CACHE),
        (["media", "video", "image", "audio", "thumbnail", "brand"], ArtifactType.MEDIA),
        (["config", "settings", "yaml", "toml", "ini", "json"], ArtifactType.CONFIG),
        (["data", "csv", "export", "archive", "database", "backup"], ArtifactType.DATA),
        (["code", "python", "typescript", "javascript", "source", ".py", ".ts"], ArtifactType.CODE),
    ]

    for keywords, atype in _MAP:
        if any(kw in key for kw in keywords):
            return atype
    return ArtifactType.UNKNOWN


def sync_policy_to_dict(p: ArtifactSyncPolicy) -> dict[str, Any]:
    return p.to_dict()


def sync_policy_from_dict(d: dict[str, Any]) -> ArtifactSyncPolicy:
    return ArtifactSyncPolicy.from_dict(d)
