"""Conference Rooms API — servers, categories, channels, messages, threads, forums,
roles, members, invites, meetings, voice, DEX, artifacts, audit, search.

All endpoints prefixed /api/umh/rooms/ and registered via include_router.
"""

from __future__ import annotations

import os
import sys

_app_root = os.environ.get("UMH_ROOT", "/opt/OS")
if _app_root not in sys.path:
    sys.path.insert(0, _app_root)

import json
import logging
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import jwt as pyjwt

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from transports.api.cockpit_auth import require_clerk_auth

logger = logging.getLogger(__name__)

rooms_router = APIRouter(prefix="/rooms", tags=["rooms"])


# ── Realtime broadcast ──

def _push_room_event(event_type: str, payload: dict) -> None:
    """Push a room event into the cockpit WS pulse stream."""
    try:
        from transports.api.cockpit import push_organism_event
        push_organism_event({"type": "room_event", "event": event_type, **payload})
    except Exception:
        logger.debug("room event broadcast skipped (cockpit not loaded)")


# ── Storage ──

_DATA_DIR = Path(os.environ.get("UMH_ROOT", "/opt/OS")) / "data" / "umh" / "rooms"
_DATA_DIR.mkdir(parents=True, exist_ok=True)


def _store_path(collection: str) -> Path:
    return _DATA_DIR / f"{collection}.json"


def _load(collection: str) -> list[dict]:
    p = _store_path(collection)
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return []


def _save(collection: str, data: list[dict]) -> None:
    p = _store_path(collection)
    p.write_text(json.dumps(data, default=str, indent=2))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uid() -> str:
    return str(uuid.uuid4())


def _audit(server_id: str, channel_id: str | None, event_type: str, actor: str, details: dict) -> None:
    events = _load("audit_log")
    events.append({
        "id": _uid(),
        "server_id": server_id,
        "channel_id": channel_id,
        "type": event_type,
        "actor_id": actor,
        "actor_name": actor,
        "details": details,
        "created_at": _now(),
    })
    if len(events) > 5000:
        events = events[-5000:]
    _save("audit_log", events)


# ── Authorization helpers ──

def _user_id(user) -> str:
    if isinstance(user, dict):
        return user.get("user_id", "operator")
    return getattr(user, "user_id", "operator")


def _display_name(user) -> str:
    if isinstance(user, dict):
        return user.get("display_name", "Operator")
    return getattr(user, "display_name", None) or getattr(user, "email", None) or "Operator"


def _get_member(user, server_id: str) -> dict | None:
    uid = _user_id(user)
    for m in _load("members"):
        if m["server_id"] == server_id and m["user_id"] == uid:
            return m
    return None


def _effective_permissions(user, server_id: str) -> set[str]:
    member = _get_member(user, server_id)
    if not member:
        return set()
    role_ids = member.get("roles", [])
    perms: set[str] = set()
    for r in _load("roles"):
        if r["server_id"] == server_id and r["id"] in role_ids:
            perms.update(r.get("permissions", []))
    return perms


def _is_server_owner(user, server_id: str) -> bool:
    for s in _load("servers"):
        if s["id"] == server_id:
            return s.get("owner_id") == _user_id(user)
    return False


def _require_server_member(user, server_id: str) -> dict:
    member = _get_member(user, server_id)
    if not member and not _is_server_owner(user, server_id):
        raise HTTPException(403, "Not a member of this server")
    return member or {"user_id": _user_id(user), "server_id": server_id, "roles": []}


def _require_server_perm(user, server_id: str, perm: str) -> None:
    if _is_server_owner(user, server_id):
        return
    perms = _effective_permissions(user, server_id)
    if perm not in perms and "administrator" not in perms:
        raise HTTPException(403, f"Missing permission: {perm}")


def _channel_server_id(channel_id: str) -> str | None:
    for c in _load("channels"):
        if c["id"] == channel_id:
            return c.get("server_id")
    return None


def _require_channel_access(user, channel_id: str, perm: str = "view_channel") -> str:
    """Verify user can access a channel. Returns the server_id."""
    channels = _load("channels")
    ch = next((c for c in channels if c["id"] == channel_id), None)
    if not ch:
        raise HTTPException(404, "Channel not found")
    server_id = ch["server_id"]
    _require_server_member(user, server_id)
    if ch.get("private"):
        perms = _effective_permissions(user, server_id)
        if perm not in perms and "manage_channels" not in perms and "administrator" not in perms:
            if not _is_server_owner(user, server_id):
                raise HTTPException(403, "No access to this private channel")
    return server_id


# ── Server Templates ──

TEMPLATES: dict[str, dict] = {
    "founder_war_room": {
        "categories": ["COMMAND", "MEETINGS", "CONTENT", "CLIENTS", "ENGINEERING"],
        "channels": {
            "COMMAND": [
                ("strategy", "text"), ("execution", "text"), ("reports", "text"),
                ("approvals", "text"), ("daily-ops", "text"), ("voice-war-room", "voice"),
            ],
            "MEETINGS": [("war-room-meetings", "video_meeting")],
            "CONTENT": [("content-planning", "text"), ("assets", "files")],
            "CLIENTS": [("client-overview", "text")],
            "ENGINEERING": [("builds", "text"), ("deploys", "text")],
        },
        "roles": [
            {"name": "Commander", "color": "#FF3D3D", "permissions": ["manage_server", "manage_roles", "manage_channels", "manage_messages"]},
        ],
    },
    "sales_team": {
        "categories": ["PIPELINE", "CALLS", "RESOURCES"],
        "channels": {
            "PIPELINE": [("leads", "text"), ("discovery-calls", "text"), ("objections", "text"), ("follow-ups", "text"), ("win-loss-review", "text")],
            "CALLS": [("sales-voice", "voice"), ("sales-meetings", "video_meeting")],
            "RESOURCES": [("playbooks", "files"), ("scripts", "text")],
        },
        "roles": [
            {"name": "Sales Lead", "color": "#FFB800", "permissions": ["manage_channels", "manage_messages"]},
        ],
    },
    "client_delivery": {
        "categories": ["DELIVERY", "COMMUNICATION"],
        "channels": {
            "DELIVERY": [("announcements", "announcement"), ("deliverables", "text"), ("approvals", "text"), ("files", "files")],
            "COMMUNICATION": [("meetings", "video_meeting"), ("client-support", "text")],
        },
        "roles": [
            {"name": "Client", "color": "#00E5FF", "permissions": ["view_channel", "send_messages"]},
        ],
    },
    "engineering": {
        "categories": ["BUILD", "OPS", "VOICE"],
        "channels": {
            "BUILD": [("build", "text"), ("bugs", "text"), ("architecture", "forum"), ("test-reports", "text")],
            "OPS": [("deploys", "text"), ("incidents", "text")],
            "VOICE": [("engineering-voice", "voice")],
        },
        "roles": [
            {"name": "Tech Lead", "color": "#00FF88", "permissions": ["manage_channels", "manage_messages", "manage_threads"]},
        ],
    },
    "creator_studio": {
        "categories": ["PLANNING", "PRODUCTION", "ASSETS"],
        "channels": {
            "PLANNING": [("show-planning", "text"), ("guests", "text"), ("calendar", "text")],
            "PRODUCTION": [("live-control", "text"), ("clips", "text"), ("broadcast-voice", "voice")],
            "ASSETS": [("assets", "files"), ("scripts", "text")],
        },
        "roles": [],
    },
    "community": {
        "categories": ["INFO", "GENERAL", "RESOURCES"],
        "channels": {
            "INFO": [("welcome", "announcement"), ("rules", "announcement"), ("announcements", "announcement")],
            "GENERAL": [("general", "text"), ("forum", "forum"), ("voice-lounge", "voice")],
            "RESOURCES": [("resources", "files"), ("faq", "text")],
        },
        "roles": [
            {"name": "Moderator", "color": "#A855F7", "permissions": ["manage_messages", "manage_threads"]},
            {"name": "Member", "color": "#888888", "permissions": ["send_messages", "create_threads", "add_reactions"]},
        ],
    },
    "coaching_cohort": {
        "categories": ["PROGRAM", "COMMUNITY"],
        "channels": {
            "PROGRAM": [("announcements", "announcement"), ("wins", "text"), ("questions", "text"), ("resources", "files")],
            "COMMUNITY": [("general", "text"), ("coaching-calls", "video_meeting")],
        },
        "roles": [],
    },
    "broadcast_studio": {
        "categories": ["PRODUCTION", "CONTENT", "TEAM"],
        "channels": {
            "PRODUCTION": [("show-planning", "text"), ("live-control", "text"), ("clips", "text"), ("broadcast-voice", "voice")],
            "CONTENT": [("guests", "text"), ("assets", "files")],
            "TEAM": [("general", "text")],
        },
        "roles": [],
    },
    "security_ops": {
        "categories": ["ALERTS", "OPERATIONS"],
        "channels": {
            "ALERTS": [("alerts", "text"), ("incidents", "text"), ("camera-events", "text")],
            "OPERATIONS": [("audit-log", "text"), ("security-voice", "voice")],
        },
        "roles": [
            {"name": "Security Admin", "color": "#FF3D3D", "permissions": ["manage_server", "manage_channels", "manage_messages"]},
        ],
    },
    "empty": {"categories": [], "channels": {}, "roles": []},
}


# ── Request Models ──

class CreateServerReq(BaseModel):
    name: str
    description: str = ""
    privacy: str = "private"
    template: str | None = "empty"

class UpdateServerReq(BaseModel):
    name: str | None = None
    description: str | None = None
    icon_emoji: str | None = None
    privacy: str | None = None
    archived: bool | None = None
    sort_order: int | None = None
    pinned: bool | None = None

class CreateCategoryReq(BaseModel):
    name: str

class UpdateCategoryReq(BaseModel):
    name: str | None = None
    sort_order: int | None = None
    collapsed: bool | None = None
    muted: bool | None = None
    permission_synced: bool | None = None

class CreateChannelReq(BaseModel):
    name: str
    type: str = "text"
    category_id: str | None = None

class UpdateChannelReq(BaseModel):
    name: str | None = None
    topic: str | None = None
    sort_order: int | None = None
    private: bool | None = None
    locked: bool | None = None
    slowmode_seconds: int | None = None
    archived: bool | None = None
    muted: bool | None = None
    dex_mode: str | None = None
    dex_enabled: bool | None = None
    memory_scope: str | None = None

class SendMessageReq(BaseModel):
    content: str
    reply_to_id: str | None = None

class EditMessageReq(BaseModel):
    content: str

class PinMessageReq(BaseModel):
    pinned: bool

class ReactionReq(BaseModel):
    emoji: str

class CreateThreadReq(BaseModel):
    name: str
    parent_message_id: str | None = None

class UpdateThreadReq(BaseModel):
    name: str | None = None
    archived: bool | None = None
    locked: bool | None = None

class CreateForumPostReq(BaseModel):
    title: str
    body: str = ""
    tags: list[str] = Field(default_factory=list)

class UpdateForumPostReq(BaseModel):
    title: str | None = None
    body: str | None = None
    tags: list[str] | None = None
    pinned: bool | None = None
    locked: bool | None = None
    closed: bool | None = None

class CreateForumTagReq(BaseModel):
    name: str
    color: str = "#888888"

class CreateRoleReq(BaseModel):
    name: str
    color: str = "#888888"
    permissions: list[str] = Field(default_factory=list)

class UpdateRoleReq(BaseModel):
    name: str | None = None
    color: str | None = None
    icon_emoji: str | None = None
    sort_order: int | None = None
    permissions: list[str] | None = None

class RoleAssignReq(BaseModel):
    role_id: str

class PresenceReq(BaseModel):
    status: str

class TypingReq(BaseModel):
    channel_id: str
    typing: bool = True

class CreateInviteReq(BaseModel):
    channel_id: str | None = None
    max_uses: int | None = None
    expires_hours: int | None = None
    role_on_join: str | None = None

class UpdateMeetingReq(BaseModel):
    objective: str | None = None
    agenda: list[str] | None = None
    notes: str | None = None
    decisions: list[str] | None = None
    mode: str | None = None
    recording_consent: bool | None = None
    ai_assistance: bool | None = None

class AddActionItemReq(BaseModel):
    text: str
    assignee: str = "unassigned"
    due_date: str | None = None
    completed: bool = False

class UpdateDexReq(BaseModel):
    enabled: bool | None = None
    mode: str | None = None
    memory_scope: str | None = None
    autonomy_level: str | None = None
    meeting_listener: bool | None = None
    transcript_enabled: bool | None = None
    action_creation: bool | None = None
    summarization: bool | None = None

class CreateArtifactReq(BaseModel):
    name: str
    type: str = "file"
    metadata: dict = Field(default_factory=dict)


# ── Servers ──

@rooms_router.get("/servers")
async def list_servers(user=Depends(require_clerk_auth)):
    uid = _user_id(user)
    member_server_ids = {m["server_id"] for m in _load("members") if m["user_id"] == uid}
    return [s for s in _load("servers") if s["id"] in member_server_ids or s.get("owner_id") == uid]


@rooms_router.post("/servers")
async def create_server(req: CreateServerReq, user=Depends(require_clerk_auth)):
    servers = _load("servers")
    server = {
        "id": _uid(),
        "name": req.name,
        "description": req.description,
        "icon_emoji": "",
        "owner_id": _user_id(user),
        "privacy": req.privacy,
        "template": req.template,
        "created_at": _now(),
        "updated_at": _now(),
        "archived": False,
        "sort_order": len(servers),
        "pinned": False,
    }
    servers.append(server)
    _save("servers", servers)

    # Apply template
    if req.template and req.template in TEMPLATES:
        tpl = TEMPLATES[req.template]
        cat_map: dict[str, str] = {}
        categories = _load("categories")
        channels = _load("channels")
        roles = _load("roles")

        for i, cat_name in enumerate(tpl.get("categories", [])):
            cat = {
                "id": _uid(),
                "server_id": server["id"],
                "name": cat_name,
                "sort_order": i,
                "collapsed": False,
                "muted": False,
                "permission_synced": True,
            }
            categories.append(cat)
            cat_map[cat_name] = cat["id"]

        _save("categories", categories)

        for cat_name, ch_list in tpl.get("channels", {}).items():
            cat_id = cat_map.get(cat_name)
            for j, (ch_name, ch_type) in enumerate(ch_list):
                ch = {
                    "id": _uid(),
                    "server_id": server["id"],
                    "category_id": cat_id,
                    "name": ch_name,
                    "topic": "",
                    "type": ch_type,
                    "sort_order": j,
                    "private": False,
                    "locked": False,
                    "slowmode_seconds": 0,
                    "archived": False,
                    "unread_count": 0,
                    "mention_count": 0,
                    "muted": False,
                    "last_message_at": None,
                    "dex_mode": "founder_operator",
                    "dex_enabled": True,
                    "memory_scope": "room",
                }
                channels.append(ch)

        _save("channels", channels)

        for role_def in tpl.get("roles", []):
            role = {
                "id": _uid(),
                "server_id": server["id"],
                "name": role_def["name"],
                "color": role_def.get("color", "#888888"),
                "icon_emoji": "",
                "sort_order": len(roles),
                "permissions": role_def.get("permissions", []),
                "is_default": False,
            }
            roles.append(role)

        # Always add default roles
        for default_role in [
            {"name": "Owner", "color": "#FF3D3D", "permissions": [
                "view_server", "manage_server", "manage_roles", "manage_channels",
                "manage_permissions", "create_invites", "view_channel", "send_messages",
                "manage_messages", "create_threads", "manage_threads", "attach_files",
                "add_reactions", "mention_everyone", "join_voice", "speak",
                "mute_members", "deafen_members", "move_members", "share_screen",
                "start_video", "record_meeting", "view_transcripts", "manage_room_memory",
                "manage_dex_mode", "create_work_packets", "approve_room_actions", "invite_guests",
            ]},
            {"name": "Admin", "color": "#FFB800", "permissions": [
                "view_server", "manage_channels", "create_invites", "view_channel",
                "send_messages", "manage_messages", "create_threads", "manage_threads",
                "attach_files", "add_reactions", "mention_everyone", "join_voice",
                "speak", "mute_members", "share_screen", "start_video",
                "view_transcripts", "manage_dex_mode", "invite_guests",
            ]},
            {"name": "Member", "color": "#888888", "permissions": [
                "view_server", "view_channel", "send_messages", "create_threads",
                "attach_files", "add_reactions", "join_voice", "speak",
                "share_screen", "start_video",
            ], "is_default": True},
            {"name": "Guest", "color": "#555555", "permissions": [
                "view_channel", "send_messages", "add_reactions",
            ]},
        ]:
            role = {
                "id": _uid(),
                "server_id": server["id"],
                "name": default_role["name"],
                "color": default_role["color"],
                "icon_emoji": "",
                "sort_order": len(roles),
                "permissions": default_role["permissions"],
                "is_default": default_role.get("is_default", False),
            }
            roles.append(role)

        _save("roles", roles)

    # Ensure default roles exist even without a template
    if not req.template or req.template not in TEMPLATES:
        roles = _load("roles")
        for default_role in [
            {"name": "Owner", "color": "#FF3D3D", "permissions": [
                "view_server", "manage_server", "manage_roles", "manage_channels",
                "manage_permissions", "create_invites", "view_channel", "send_messages",
                "manage_messages", "create_threads", "manage_threads", "attach_files",
                "add_reactions", "mention_everyone", "join_voice", "speak",
                "mute_members", "deafen_members", "move_members", "share_screen",
                "start_video", "record_meeting", "view_transcripts", "manage_room_memory",
                "manage_dex_mode", "create_work_packets", "approve_room_actions", "invite_guests",
            ]},
            {"name": "Admin", "color": "#FFB800", "permissions": [
                "view_server", "manage_channels", "create_invites", "view_channel",
                "send_messages", "manage_messages", "create_threads", "manage_threads",
                "attach_files", "add_reactions", "mention_everyone", "join_voice",
                "speak", "mute_members", "share_screen", "start_video",
                "view_transcripts", "manage_dex_mode", "invite_guests",
            ]},
            {"name": "Member", "color": "#888888", "permissions": [
                "view_server", "view_channel", "send_messages", "create_threads",
                "attach_files", "add_reactions", "join_voice", "speak",
                "share_screen", "start_video",
            ], "is_default": True},
            {"name": "Guest", "color": "#555555", "permissions": [
                "view_channel", "send_messages", "add_reactions",
            ]},
        ]:
            role = {
                "id": _uid(),
                "server_id": server["id"],
                "name": default_role["name"],
                "color": default_role["color"],
                "icon_emoji": "",
                "sort_order": len(roles),
                "permissions": default_role["permissions"],
                "is_default": default_role.get("is_default", False),
            }
            roles.append(role)
        _save("roles", roles)

    # Find the Owner role ID for the creator's member record
    owner_role_id = None
    for r in _load("roles"):
        if r["server_id"] == server["id"] and r["name"] == "Owner":
            owner_role_id = r["id"]
            break

    # Auto-add creator as member with Owner role
    members = _load("members")
    members.append({
        "id": _uid(),
        "server_id": server["id"],
        "user_id": _user_id(user),
        "display_name": _display_name(user),
        "roles": [owner_role_id] if owner_role_id else [],
        "joined_at": _now(),
        "presence": "online",
        "current_channel_id": None,
        "last_active_at": _now(),
        "is_typing": False,
        "is_speaking": False,
        "is_muted": False,
        "is_deafened": False,
    })
    _save("members", members)

    _audit(server["id"], None, "server_created", _user_id(user), {"name": req.name})
    return server


@rooms_router.patch("/servers/{server_id}")
async def update_server(server_id: str, req: UpdateServerReq, user=Depends(require_clerk_auth)):
    _require_server_perm(user, server_id, "manage_server")
    servers = _load("servers")
    for s in servers:
        if s["id"] == server_id:
            for k, v in req.model_dump(exclude_none=True).items():
                s[k] = v
            s["updated_at"] = _now()
            _save("servers", servers)
            _audit(server_id, None, "server_updated", _user_id(user), req.model_dump(exclude_none=True))
            return s
    raise HTTPException(404, "Server not found")


@rooms_router.delete("/servers/{server_id}")
async def delete_server(server_id: str, user=Depends(require_clerk_auth)):
    if not _is_server_owner(user, server_id):
        raise HTTPException(403, "Only the server owner can delete a server")
    servers = _load("servers")
    servers = [s for s in servers if s["id"] != server_id]
    _save("servers", servers)
    _audit(server_id, None, "server_deleted", _user_id(user), {})
    return {"ok": True}


# ── Categories ──

@rooms_router.get("/servers/{server_id}/categories")
async def list_categories(server_id: str, user=Depends(require_clerk_auth)):
    _require_server_member(user, server_id)
    return [c for c in _load("categories") if c["server_id"] == server_id]


@rooms_router.post("/servers/{server_id}/categories")
async def create_category(server_id: str, req: CreateCategoryReq, user=Depends(require_clerk_auth)):
    _require_server_perm(user, server_id, "manage_channels")
    categories = _load("categories")
    cat = {
        "id": _uid(),
        "server_id": server_id,
        "name": req.name,
        "sort_order": len([c for c in categories if c["server_id"] == server_id]),
        "collapsed": False,
        "muted": False,
        "permission_synced": True,
    }
    categories.append(cat)
    _save("categories", categories)
    _audit(server_id, None, "category_created", _user_id(user), {"name": req.name})
    return cat


@rooms_router.patch("/categories/{cat_id}")
async def update_category(cat_id: str, req: UpdateCategoryReq, user=Depends(require_clerk_auth)):
    categories = _load("categories")
    cat = next((c for c in categories if c["id"] == cat_id), None)
    if not cat:
        raise HTTPException(404, "Category not found")
    _require_server_perm(user, cat["server_id"], "manage_channels")
    for k, v in req.model_dump(exclude_none=True).items():
        cat[k] = v
    _save("categories", categories)
    return cat


@rooms_router.delete("/categories/{cat_id}")
async def delete_category(cat_id: str, user=Depends(require_clerk_auth)):
    categories = _load("categories")
    cat = next((c for c in categories if c["id"] == cat_id), None)
    if not cat:
        raise HTTPException(404, "Category not found")
    _require_server_perm(user, cat["server_id"], "manage_channels")
    categories = [c for c in categories if c["id"] != cat_id]
    _save("categories", categories)
    return {"ok": True}


# ── Channels ──

@rooms_router.get("/servers/{server_id}/channels")
async def list_channels(server_id: str, user=Depends(require_clerk_auth)):
    _require_server_member(user, server_id)
    channels = _load("channels")
    user_perms = _effective_permissions(user, server_id)
    is_owner = _is_server_owner(user, server_id)

    server_channels = [c for c in channels if c["server_id"] == server_id]
    visible = []
    for ch in server_channels:
        if not ch.get("private"):
            visible.append(ch)
        elif is_owner or "manage_channels" in user_perms or "administrator" in user_perms:
            visible.append(ch)
    return visible


@rooms_router.post("/servers/{server_id}/channels")
async def create_channel(server_id: str, req: CreateChannelReq, user=Depends(require_clerk_auth)):
    _require_server_perm(user, server_id, "manage_channels")
    channels = _load("channels")
    ch = {
        "id": _uid(),
        "server_id": server_id,
        "category_id": req.category_id,
        "name": req.name,
        "topic": "",
        "type": req.type,
        "sort_order": len([c for c in channels if c["server_id"] == server_id]),
        "private": False,
        "locked": False,
        "slowmode_seconds": 0,
        "archived": False,
        "unread_count": 0,
        "mention_count": 0,
        "muted": False,
        "last_message_at": None,
        "dex_mode": "founder_operator",
        "dex_enabled": True,
        "memory_scope": "room",
    }
    channels.append(ch)
    _save("channels", channels)
    _audit(server_id, ch["id"], "channel_created", _user_id(user), {"name": req.name, "type": req.type})
    _push_room_event("channel.created", {"server_id": server_id, "channel": ch})
    return ch


@rooms_router.patch("/channels/{channel_id}")
async def update_channel(channel_id: str, req: UpdateChannelReq, user=Depends(require_clerk_auth)):
    server_id = _require_channel_access(user, channel_id)
    _require_server_perm(user, server_id, "manage_channels")
    channels = _load("channels")
    for c in channels:
        if c["id"] == channel_id:
            for k, v in req.model_dump(exclude_none=True).items():
                c[k] = v
            _save("channels", channels)
            return c
    raise HTTPException(404, "Channel not found")


@rooms_router.delete("/channels/{channel_id}")
async def delete_channel(channel_id: str, user=Depends(require_clerk_auth)):
    channels = _load("channels")
    ch = next((c for c in channels if c["id"] == channel_id), None)
    if not ch:
        raise HTTPException(404, "Channel not found")
    _require_server_perm(user, ch["server_id"], "manage_channels")
    _audit(ch["server_id"], channel_id, "channel_deleted", _user_id(user), {"name": ch["name"]})
    channels = [c for c in channels if c["id"] != channel_id]
    _save("channels", channels)
    if ch:
        _push_room_event("channel.deleted", {"server_id": ch["server_id"], "channel_id": channel_id})
    return {"ok": True}


# ── Messages ──

@rooms_router.get("/channels/{channel_id}/messages")
async def list_messages(channel_id: str, limit: int = 50, before: str | None = None, user=Depends(require_clerk_auth)):
    _require_channel_access(user, channel_id, "view_channel")
    messages = _load("messages")
    ch_msgs = [m for m in messages if m["channel_id"] == channel_id and not m.get("deleted")]
    ch_msgs.sort(key=lambda m: m["created_at"])

    if before:
        idx = next((i for i, m in enumerate(ch_msgs) if m["id"] == before), None)
        if idx is not None:
            ch_msgs = ch_msgs[:idx]

    return ch_msgs[-limit:]


@rooms_router.post("/channels/{channel_id}/messages")
async def send_message(channel_id: str, req: SendMessageReq, user=Depends(require_clerk_auth)):
    _require_channel_access(user, channel_id, "send_messages")
    messages = _load("messages")

    reply_preview = None
    if req.reply_to_id:
        parent = next((m for m in messages if m["id"] == req.reply_to_id), None)
        if parent:
            reply_preview = parent["content"][:80]

    msg = {
        "id": _uid(),
        "channel_id": channel_id,
        "author_id": _user_id(user),
        "author_name": _display_name(user),
        "content": req.content,
        "created_at": _now(),
        "updated_at": None,
        "edited": False,
        "pinned": False,
        "reply_to_id": req.reply_to_id,
        "reply_preview": reply_preview,
        "thread_id": None,
        "attachments": [],
        "reactions": [],
        "mentions": [],
        "deleted": False,
    }
    messages.append(msg)
    _save("messages", messages)

    # Update channel last_message_at
    channels = _load("channels")
    for c in channels:
        if c["id"] == channel_id:
            c["last_message_at"] = msg["created_at"]
            break
    _save("channels", channels)

    _push_room_event("message.created", {"channel_id": channel_id, "message": msg})
    return msg


@rooms_router.patch("/messages/{message_id}")
async def edit_message(message_id: str, req: EditMessageReq, user=Depends(require_clerk_auth)):
    messages = _load("messages")
    for m in messages:
        if m["id"] == message_id:
            if m["author_id"] != _user_id(user):
                raise HTTPException(403, "Can only edit own messages")
            m["content"] = req.content
            m["edited"] = True
            m["updated_at"] = _now()
            _save("messages", messages)
            _push_room_event("message.updated", {"channel_id": m["channel_id"], "message": m})
            return m
    raise HTTPException(404, "Message not found")


@rooms_router.delete("/messages/{message_id}")
async def delete_message(message_id: str, user=Depends(require_clerk_auth)):
    messages = _load("messages")
    for m in messages:
        if m["id"] == message_id:
            ch_id = m["channel_id"]
            server_id = _channel_server_id(ch_id)
            uid = _user_id(user)
            if m["author_id"] != uid:
                if server_id:
                    perms = _effective_permissions(user, server_id)
                    if "manage_messages" not in perms and "administrator" not in perms and not _is_server_owner(user, server_id):
                        raise HTTPException(403, "Can only delete own messages or with manage_messages permission")
            m["deleted"] = True
            m["content"] = ""
            _save("messages", messages)
            _push_room_event("message.deleted", {"channel_id": ch_id, "message_id": message_id})
            return {"ok": True}
    raise HTTPException(404, "Message not found")


@rooms_router.post("/messages/{message_id}/pin")
async def pin_message(message_id: str, req: PinMessageReq, user=Depends(require_clerk_auth)):
    messages = _load("messages")
    for m in messages:
        if m["id"] == message_id:
            server_id = _channel_server_id(m["channel_id"])
            if server_id:
                _require_server_perm(user, server_id, "manage_messages")
            m["pinned"] = req.pinned
            _save("messages", messages)
            return {"ok": True}
    raise HTTPException(404, "Message not found")


@rooms_router.post("/messages/{message_id}/reactions")
async def add_reaction(message_id: str, req: ReactionReq, user=Depends(require_clerk_auth)):
    messages = _load("messages")
    user_id = _user_id(user)
    for m in messages:
        if m["id"] == message_id:
            existing = next((r for r in m.get("reactions", []) if r["emoji"] == req.emoji), None)
            if existing:
                if user_id not in existing.get("users", []):
                    existing["count"] = existing.get("count", 0) + 1
                    existing.setdefault("users", []).append(user_id)
            else:
                m.setdefault("reactions", []).append({
                    "emoji": req.emoji,
                    "count": 1,
                    "users": [user_id],
                    "me": True,
                })
            _save("messages", messages)
            return {"ok": True}
    raise HTTPException(404, "Message not found")


@rooms_router.delete("/messages/{message_id}/reactions/{emoji}")
async def remove_reaction(message_id: str, emoji: str, user=Depends(require_clerk_auth)):
    messages = _load("messages")
    user_id = _user_id(user)
    for m in messages:
        if m["id"] == message_id:
            for r in m.get("reactions", []):
                if r["emoji"] == emoji and user_id in r.get("users", []):
                    r["users"].remove(user_id)
                    r["count"] = max(0, r.get("count", 1) - 1)
                    if r["count"] <= 0:
                        m["reactions"] = [rx for rx in m["reactions"] if rx["emoji"] != emoji]
                    break
            _save("messages", messages)
            return {"ok": True}
    raise HTTPException(404, "Message not found")


# ── Threads ──

@rooms_router.get("/channels/{channel_id}/threads")
async def list_threads(channel_id: str, user=Depends(require_clerk_auth)):
    _require_channel_access(user, channel_id)
    return [t for t in _load("threads") if t["channel_id"] == channel_id]


@rooms_router.post("/channels/{channel_id}/threads")
async def create_thread(channel_id: str, req: CreateThreadReq, user=Depends(require_clerk_auth)):
    _require_channel_access(user, channel_id, "send_messages")
    threads = _load("threads")
    thread = {
        "id": _uid(),
        "channel_id": channel_id,
        "name": req.name,
        "created_by": _user_id(user),
        "created_at": _now(),
        "message_count": 0,
        "last_message_at": None,
        "archived": False,
        "locked": False,
        "private": False,
        "parent_message_id": req.parent_message_id,
    }
    threads.append(thread)
    _save("threads", threads)
    return thread


@rooms_router.patch("/threads/{thread_id}")
async def update_thread(thread_id: str, req: UpdateThreadReq, user=Depends(require_clerk_auth)):
    threads = _load("threads")
    for t in threads:
        if t["id"] == thread_id:
            for k, v in req.model_dump(exclude_none=True).items():
                t[k] = v
            _save("threads", threads)
            return t
    raise HTTPException(404, "Thread not found")


# ── Forum ──

@rooms_router.get("/channels/{channel_id}/forum/posts")
async def list_forum_posts(channel_id: str, user=Depends(require_clerk_auth)):
    _require_channel_access(user, channel_id)
    return [p for p in _load("forum_posts") if p["channel_id"] == channel_id]


@rooms_router.post("/channels/{channel_id}/forum/posts")
async def create_forum_post(channel_id: str, req: CreateForumPostReq, user=Depends(require_clerk_auth)):
    _require_channel_access(user, channel_id, "send_messages")
    posts = _load("forum_posts")
    post = {
        "id": _uid(),
        "channel_id": channel_id,
        "title": req.title,
        "body": req.body,
        "author_id": _user_id(user),
        "author_name": _display_name(user),
        "tags": req.tags,
        "created_at": _now(),
        "updated_at": None,
        "pinned": False,
        "locked": False,
        "closed": False,
        "reply_count": 0,
        "last_reply_at": None,
    }
    posts.append(post)
    _save("forum_posts", posts)
    return post


@rooms_router.patch("/forum/posts/{post_id}")
async def update_forum_post(post_id: str, req: UpdateForumPostReq, user=Depends(require_clerk_auth)):
    posts = _load("forum_posts")
    for p in posts:
        if p["id"] == post_id:
            for k, v in req.model_dump(exclude_none=True).items():
                p[k] = v
            p["updated_at"] = _now()
            _save("forum_posts", posts)
            return p
    raise HTTPException(404, "Forum post not found")


@rooms_router.get("/channels/{channel_id}/forum/tags")
async def list_forum_tags(channel_id: str, user=Depends(require_clerk_auth)):
    _require_channel_access(user, channel_id)
    return [t for t in _load("forum_tags") if t["channel_id"] == channel_id]


@rooms_router.post("/channels/{channel_id}/forum/tags")
async def create_forum_tag(channel_id: str, req: CreateForumTagReq, user=Depends(require_clerk_auth)):
    _require_channel_access(user, channel_id, "manage_channels")
    tags = _load("forum_tags")
    tag = {
        "id": _uid(),
        "channel_id": channel_id,
        "name": req.name,
        "color": req.color,
    }
    tags.append(tag)
    _save("forum_tags", tags)
    return tag


# ── Roles ──

@rooms_router.get("/servers/{server_id}/roles")
async def list_roles(server_id: str, user=Depends(require_clerk_auth)):
    _require_server_member(user, server_id)
    return [r for r in _load("roles") if r["server_id"] == server_id]


@rooms_router.post("/servers/{server_id}/roles")
async def create_role(server_id: str, req: CreateRoleReq, user=Depends(require_clerk_auth)):
    _require_server_perm(user, server_id, "manage_roles")
    roles = _load("roles")
    role = {
        "id": _uid(),
        "server_id": server_id,
        "name": req.name,
        "color": req.color,
        "icon_emoji": "",
        "sort_order": len([r for r in roles if r["server_id"] == server_id]),
        "permissions": req.permissions,
        "is_default": False,
    }
    roles.append(role)
    _save("roles", roles)
    _audit(server_id, None, "role_created", _user_id(user), {"name": req.name})
    return role


@rooms_router.patch("/roles/{role_id}")
async def update_role(role_id: str, req: UpdateRoleReq, user=Depends(require_clerk_auth)):
    roles = _load("roles")
    role = next((r for r in roles if r["id"] == role_id), None)
    if not role:
        raise HTTPException(404, "Role not found")
    _require_server_perm(user, role["server_id"], "manage_roles")
    for k, v in req.model_dump(exclude_none=True).items():
        role[k] = v
    _save("roles", roles)
    return role


@rooms_router.delete("/roles/{role_id}")
async def delete_role(role_id: str, user=Depends(require_clerk_auth)):
    roles = _load("roles")
    role = next((r for r in roles if r["id"] == role_id), None)
    if not role:
        raise HTTPException(404, "Role not found")
    _require_server_perm(user, role["server_id"], "manage_roles")
    roles = [r for r in roles if r["id"] != role_id]
    _save("roles", roles)
    return {"ok": True}


# ── Members ──

@rooms_router.get("/servers/{server_id}/members")
async def list_members(server_id: str, user=Depends(require_clerk_auth)):
    _require_server_member(user, server_id)
    return [m for m in _load("members") if m["server_id"] == server_id]


@rooms_router.post("/servers/{server_id}/members/{user_id}/roles")
async def assign_member_role(server_id: str, user_id: str, req: RoleAssignReq, user=Depends(require_clerk_auth)):
    _require_server_perm(user, server_id, "manage_roles")
    members = _load("members")
    for m in members:
        if m["server_id"] == server_id and m["user_id"] == user_id:
            if req.role_id not in m.get("roles", []):
                m.setdefault("roles", []).append(req.role_id)
                _save("members", members)
                _audit(server_id, None, "role_assigned", _user_id(user), {"user_id": user_id, "role_id": req.role_id})
            return m
    raise HTTPException(404, "Member not found")


@rooms_router.delete("/servers/{server_id}/members/{user_id}/roles/{role_id}")
async def remove_member_role(server_id: str, user_id: str, role_id: str, user=Depends(require_clerk_auth)):
    _require_server_perm(user, server_id, "manage_roles")
    members = _load("members")
    for m in members:
        if m["server_id"] == server_id and m["user_id"] == user_id:
            m["roles"] = [r for r in m.get("roles", []) if r != role_id]
            _save("members", members)
            return m
    raise HTTPException(404, "Member not found")


@rooms_router.post("/presence")
async def update_presence(req: PresenceReq, user=Depends(require_clerk_auth)):
    members = _load("members")
    user_id = _user_id(user)
    for m in members:
        if m["user_id"] == user_id:
            m["presence"] = req.status
            m["last_active_at"] = _now()
    _save("members", members)
    _push_room_event("presence.updated", {"user_id": user_id, "status": req.status})
    return {"ok": True}


@rooms_router.post("/typing")
async def typing_indicator(req: TypingReq, user=Depends(require_clerk_auth)):
    user_id = _user_id(user)
    event = "typing.started" if req.typing else "typing.stopped"
    _push_room_event(event, {
        "channel_id": req.channel_id,
        "user_id": user_id,
        "user_name": _display_name(user),
    })
    return {"ok": True}


# ── Invites ──

@rooms_router.get("/servers/{server_id}/invites")
async def list_invites(server_id: str, user=Depends(require_clerk_auth)):
    _require_server_member(user, server_id)
    return [inv for inv in _load("invites") if inv["server_id"] == server_id and not inv.get("revoked")]


@rooms_router.post("/servers/{server_id}/invites")
async def create_invite(server_id: str, req: CreateInviteReq, user=Depends(require_clerk_auth)):
    _require_server_perm(user, server_id, "create_invites")
    invites = _load("invites")
    expires_at = None
    if req.expires_hours:
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=req.expires_hours)).isoformat()

    invite = {
        "id": _uid(),
        "server_id": server_id,
        "channel_id": req.channel_id,
        "created_by": _user_id(user),
        "code": secrets.token_urlsafe(16),
        "max_uses": req.max_uses,
        "uses": 0,
        "expires_at": expires_at,
        "role_on_join": req.role_on_join,
        "created_at": _now(),
        "revoked": False,
    }
    invites.append(invite)
    _save("invites", invites)
    _audit(server_id, None, "invite_created", _user_id(user), {"code": invite["code"]})
    return invite


@rooms_router.delete("/invites/{invite_id}")
async def revoke_invite(invite_id: str, user=Depends(require_clerk_auth)):
    invites = _load("invites")
    for inv in invites:
        if inv["id"] == invite_id:
            _require_server_perm(user, inv["server_id"], "manage_server")
            inv["revoked"] = True
            _save("invites", invites)
            return {"ok": True}
    raise HTTPException(404, "Invite not found")


# ── Meeting ──

@rooms_router.get("/channels/{channel_id}/meeting")
async def get_meeting(channel_id: str, user=Depends(require_clerk_auth)):
    _require_channel_access(user, channel_id)
    meetings = _load("meetings")
    meeting = next((m for m in meetings if m["channel_id"] == channel_id), None)
    if not meeting:
        meeting = {
            "id": _uid(),
            "channel_id": channel_id,
            "objective": "",
            "agenda": [],
            "participants": [],
            "notes": "",
            "action_items": [],
            "decisions": [],
            "mode": "team_meeting",
            "started_at": None,
            "ended_at": None,
            "recording_consent": False,
            "ai_assistance": True,
            "transcript_placeholder": True,
        }
        meetings.append(meeting)
        _save("meetings", meetings)
    return meeting


@rooms_router.patch("/channels/{channel_id}/meeting")
async def update_meeting(channel_id: str, req: UpdateMeetingReq, user=Depends(require_clerk_auth)):
    _require_channel_access(user, channel_id)
    meetings = _load("meetings")
    for m in meetings:
        if m["channel_id"] == channel_id:
            for k, v in req.model_dump(exclude_none=True).items():
                m[k] = v
            _save("meetings", meetings)
            return m
    raise HTTPException(404, "Meeting not found")


@rooms_router.post("/channels/{channel_id}/meeting/actions")
async def add_meeting_action(channel_id: str, req: AddActionItemReq, user=Depends(require_clerk_auth)):
    _require_channel_access(user, channel_id)
    meetings = _load("meetings")
    for m in meetings:
        if m["channel_id"] == channel_id:
            item = {
                "id": _uid(),
                "text": req.text,
                "assignee": req.assignee,
                "due_date": req.due_date,
                "completed": req.completed,
            }
            m.setdefault("action_items", []).append(item)
            _save("meetings", meetings)
            return m
    raise HTTPException(404, "Meeting not found")


@rooms_router.post("/channels/{channel_id}/meeting/actions/{item_id}/toggle")
async def toggle_meeting_action(channel_id: str, item_id: str, user=Depends(require_clerk_auth)):
    _require_channel_access(user, channel_id)
    meetings = _load("meetings")
    for m in meetings:
        if m["channel_id"] == channel_id:
            for item in m.get("action_items", []):
                if item["id"] == item_id:
                    item["completed"] = not item.get("completed", False)
                    _save("meetings", meetings)
                    return m
    raise HTTPException(404, "Action item not found")


# ── Voice ──

@rooms_router.get("/channels/{channel_id}/voice")
async def get_voice_state(channel_id: str, user=Depends(require_clerk_auth)):
    _require_channel_access(user, channel_id)
    voice = _load("voice_states")
    state = next((v for v in voice if v["channel_id"] == channel_id), None)
    if not state:
        state = {"channel_id": channel_id, "participants": [], "topic": "", "capacity": 25, "locked": False}
    return state


@rooms_router.post("/channels/{channel_id}/voice/join")
async def join_voice(channel_id: str, user=Depends(require_clerk_auth)):
    _require_channel_access(user, channel_id, "connect")
    voice = _load("voice_states")
    state = next((v for v in voice if v["channel_id"] == channel_id), None)
    if not state:
        state = {"channel_id": channel_id, "participants": [], "topic": "", "capacity": 25, "locked": False}
        voice.append(state)

    user_id = _user_id(user)
    if not any(p["user_id"] == user_id for p in state["participants"]):
        state["participants"].append({
            "user_id": user_id,
            "display_name": _display_name(user),
            "is_speaking": False,
            "is_muted": False,
            "is_deafened": False,
            "joined_at": _now(),
        })
    _save("voice_states", voice)
    return state


@rooms_router.post("/channels/{channel_id}/voice/leave")
async def leave_voice(channel_id: str, user=Depends(require_clerk_auth)):
    _require_channel_access(user, channel_id)
    voice = _load("voice_states")
    user_id = _user_id(user)
    for v in voice:
        if v["channel_id"] == channel_id:
            v["participants"] = [p for p in v["participants"] if p["user_id"] != user_id]
            _save("voice_states", voice)
            return {"ok": True}
    return {"ok": True}


@rooms_router.post("/channels/{channel_id}/voice/token")
async def get_voice_token(channel_id: str, user=Depends(require_clerk_auth)):
    """Generate a LiveKit JWT for joining a voice channel."""
    _require_channel_access(user, channel_id, "connect")

    api_key = os.environ.get("LIVEKIT_API_KEY")
    api_secret = os.environ.get("LIVEKIT_API_SECRET")
    if not api_key or not api_secret:
        raise HTTPException(503, "Voice infrastructure not configured")

    user_id = _user_id(user)
    display = _display_name(user)
    room_name = f"room-{channel_id}"

    now = datetime.now(timezone.utc)
    claims = {
        "iss": api_key,
        "sub": user_id,
        "name": display,
        "nbf": int(now.timestamp()),
        "exp": int((now + timedelta(hours=6)).timestamp()),
        "jti": uuid.uuid4().hex,
        "video": {
            "roomJoin": True,
            "room": room_name,
            "canPublish": True,
            "canSubscribe": True,
            "canPublishData": True,
        },
    }
    token = pyjwt.encode(claims, api_secret, algorithm="HS256")

    livekit_ws = os.environ.get("LIVEKIT_WS_URL", "")
    return {"token": token, "url": livekit_ws, "room": room_name}


# ── DEX Settings ──

@rooms_router.get("/channels/{channel_id}/dex")
async def get_dex_settings(channel_id: str, user=Depends(require_clerk_auth)):
    _require_channel_access(user, channel_id)
    dex = _load("dex_settings")
    settings = next((d for d in dex if d["channel_id"] == channel_id), None)
    if not settings:
        settings = {
            "channel_id": channel_id,
            "enabled": True,
            "mode": "founder_operator",
            "memory_scope": "room",
            "allowed_actions": [],
            "autonomy_level": "suggest",
            "meeting_listener": False,
            "transcript_enabled": False,
            "recording_enabled": False,
            "action_creation": False,
            "approval_required": True,
            "summarization": True,
        }
    return settings


@rooms_router.patch("/channels/{channel_id}/dex")
async def update_dex_settings(channel_id: str, req: UpdateDexReq, user=Depends(require_clerk_auth)):
    server_id = _require_channel_access(user, channel_id)
    _require_server_perm(user, server_id, "manage_channels")
    dex = _load("dex_settings")
    settings = next((d for d in dex if d["channel_id"] == channel_id), None)
    if not settings:
        settings = {
            "channel_id": channel_id,
            "enabled": True,
            "mode": "founder_operator",
            "memory_scope": "room",
            "allowed_actions": [],
            "autonomy_level": "suggest",
            "meeting_listener": False,
            "transcript_enabled": False,
            "recording_enabled": False,
            "action_creation": False,
            "approval_required": True,
            "summarization": True,
        }
        dex.append(settings)

    for k, v in req.model_dump(exclude_none=True).items():
        settings[k] = v
    _save("dex_settings", dex)
    return settings


@rooms_router.post("/channels/{channel_id}/dex/summarize")
async def dex_summarize(channel_id: str, user=Depends(require_clerk_auth)):
    _require_channel_access(user, channel_id)
    messages = _load("messages")
    ch_msgs = [m for m in messages if m["channel_id"] == channel_id and not m.get("deleted")]
    ch_msgs.sort(key=lambda m: m["created_at"])
    recent = ch_msgs[-20:]

    if not recent:
        return {"summary": "No messages in this channel yet."}

    text_lines = [f"{m['author_name']}: {m['content']}" for m in recent]
    summary = f"Room summary ({len(recent)} recent messages):\n"
    summary += f"Participants: {', '.join(set(m['author_name'] for m in recent))}\n"
    summary += f"Period: {recent[0]['created_at'][:10]} to {recent[-1]['created_at'][:10]}\n"
    summary += f"Latest topic: {recent[-1]['content'][:100]}"

    return {"summary": summary}


# ── Audit Log ──

@rooms_router.get("/servers/{server_id}/audit-log")
async def get_audit_log(server_id: str, user=Depends(require_clerk_auth)):
    _require_server_perm(user, server_id, "view_audit_log")
    events = _load("audit_log")
    server_events = [e for e in events if e["server_id"] == server_id]
    return server_events[-100:]


# ── Artifacts ──

@rooms_router.get("/channels/{channel_id}/artifacts")
async def list_artifacts(channel_id: str, user=Depends(require_clerk_auth)):
    _require_channel_access(user, channel_id)
    return [a for a in _load("artifacts") if a["channel_id"] == channel_id]


@rooms_router.post("/channels/{channel_id}/artifacts")
async def create_artifact(channel_id: str, req: CreateArtifactReq, user=Depends(require_clerk_auth)):
    _require_channel_access(user, channel_id, "send_messages")
    artifacts = _load("artifacts")
    artifact = {
        "id": _uid(),
        "channel_id": channel_id,
        "name": req.name,
        "type": req.type,
        "owner_id": _user_id(user),
        "pinned": False,
        "created_at": _now(),
        "metadata": req.metadata,
    }
    artifacts.append(artifact)
    _save("artifacts", artifacts)
    return artifact


# ── Search ──

@rooms_router.get("/servers/{server_id}/search")
async def search_server(server_id: str, q: str = "", user=Depends(require_clerk_auth)):
    _require_server_member(user, server_id)
    if not q:
        return []

    results = []
    query = q.lower()

    # Search messages
    channels = _load("channels")
    server_channel_ids = {c["id"] for c in channels if c["server_id"] == server_id}

    messages = _load("messages")
    for m in messages:
        if m["channel_id"] in server_channel_ids and not m.get("deleted") and query in m.get("content", "").lower():
            results.append({
                "type": "message",
                "id": m["id"],
                "channel_id": m["channel_id"],
                "server_id": server_id,
                "title": m["content"][:60],
                "excerpt": m["content"][:120],
                "author": m["author_name"],
                "timestamp": m["created_at"],
            })

    # Search forum posts
    posts = _load("forum_posts")
    for p in posts:
        if p["channel_id"] in server_channel_ids and (query in p.get("title", "").lower() or query in p.get("body", "").lower()):
            results.append({
                "type": "forum_post",
                "id": p["id"],
                "channel_id": p["channel_id"],
                "server_id": server_id,
                "title": p["title"],
                "excerpt": p["body"][:120],
                "author": p["author_name"],
                "timestamp": p["created_at"],
            })

    # Search threads
    threads = _load("threads")
    for t in threads:
        if t["channel_id"] in server_channel_ids and query in t.get("name", "").lower():
            results.append({
                "type": "thread",
                "id": t["id"],
                "channel_id": t["channel_id"],
                "server_id": server_id,
                "title": t["name"],
                "excerpt": f"{t['message_count']} messages",
                "author": t["created_by"],
                "timestamp": t["created_at"],
            })

    return results[:50]
