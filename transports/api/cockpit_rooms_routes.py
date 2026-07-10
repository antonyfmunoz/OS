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

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from transports.api.cockpit_auth import require_clerk_auth
from transports.api.governed import governed_mutation

logger = logging.getLogger(__name__)

rooms_router = APIRouter(prefix="/rooms", tags=["rooms"])
rooms_public_router = APIRouter(prefix="/rooms", tags=["rooms-public"])


# ── Realtime broadcast ──

def _push_room_event(event_type: str, payload: dict) -> None:
    """Push a room event into the cockpit WS pulse stream."""
    try:
        from transports.api.cockpit_core_routes import push_organism_event
        push_organism_event({"type": "room_event", "event": event_type, **payload})
    except Exception:
        logger.debug("room event broadcast skipped (cockpit not loaded)")


# ── Storage ──

_DATA_DIR = Path(os.environ.get("UMH_ROOMS_DATA", "/var/lib/umh/rooms"))
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


# ── Guest JWT verification ──


def _verify_guest_token(authorization: str | None) -> dict:
    """Verify a LiveKit guest JWT and return its claims (sub, name, video.room).

    Raises HTTPException on missing/invalid/expired token.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing guest token")
    token = authorization[7:]
    api_secret = os.environ.get("LIVEKIT_API_SECRET", "")
    if not api_secret:
        raise HTTPException(500, "LiveKit not configured")
    try:
        claims = pyjwt.decode(token, api_secret, algorithms=["HS256"])
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except pyjwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
    if not claims.get("sub"):
        raise HTTPException(401, "Token missing identity")
    return claims


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

class GuestPermissions(BaseModel):
    can_speak: bool = True
    can_video: bool = True
    can_screen_share: bool = False
    can_chat: bool = True

class CreateInviteReq(BaseModel):
    channel_id: str | None = None
    room_type: str = "voice"
    label: str | None = None
    max_uses: int | None = None
    expires_hours: float | None = None
    allowed_email_domains: list[str] | None = None
    allowed_emails: list[str] | None = None
    permissions: GuestPermissions = Field(default_factory=GuestPermissions)
    role_on_join: str | None = None

class GuestJoinReq(BaseModel):
    guest_name: str = Field(..., min_length=1, max_length=40)
    guest_email: str | None = Field(None, max_length=254)
    mic_enabled: bool = True
    video_enabled: bool = False

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
def list_servers(user=Depends(require_clerk_auth)):
    uid = _user_id(user)
    member_server_ids = {m["server_id"] for m in _load("members") if m["user_id"] == uid}
    return [s for s in _load("servers") if s["id"] in member_server_ids or s.get("owner_id") == uid]


@rooms_router.post("/servers")
def create_server(req: CreateServerReq, user=Depends(require_clerk_auth)):
    uid = _user_id(user)
    dname = _display_name(user)

    def _do_create():
        servers = _load("servers")
        server = {
            "id": _uid(),
            "name": req.name,
            "description": req.description,
            "icon_emoji": "",
            "owner_id": uid,
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

        owner_role_id = None
        for r in _load("roles"):
            if r["server_id"] == server["id"] and r["name"] == "Owner":
                owner_role_id = r["id"]
                break

        members = _load("members")
        members.append({
            "id": _uid(),
            "server_id": server["id"],
            "user_id": uid,
            "display_name": dname,
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

        _audit(server["id"], None, "server_created", uid, {"name": req.name})
        return f"created server {req.name}", True

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"create server {req.name}",
        execute_fn=_do_create,
        source="cockpit",
    )
    return resp.to_http_dict()


@rooms_router.patch("/servers/{server_id}")
def update_server(server_id: str, req: UpdateServerReq, user=Depends(require_clerk_auth)):
    _require_server_perm(user, server_id, "manage_server")
    updates = req.model_dump(exclude_none=True)
    uid = _user_id(user)

    def _do_update():
        servers = _load("servers")
        for s in servers:
            if s["id"] == server_id:
                for k, v in updates.items():
                    s[k] = v
                s["updated_at"] = _now()
                _save("servers", servers)
                _audit(server_id, None, "server_updated", uid, updates)
                return f"updated server {server_id}", True
        return "server not found", False

    resp = governed_mutation(
        mutation_name="settings_update",
        intent=f"update server {server_id}",
        execute_fn=_do_update,
        source="cockpit",
    )
    return resp.to_http_dict()


@rooms_router.delete("/servers/{server_id}")
def delete_server(server_id: str, user=Depends(require_clerk_auth)):
    if not _is_server_owner(user, server_id):
        raise HTTPException(403, "Only the server owner can delete a server")
    uid = _user_id(user)

    def _do_delete():
        servers = _load("servers")
        servers = [s for s in servers if s["id"] != server_id]
        _save("servers", servers)
        _audit(server_id, None, "server_deleted", uid, {})
        return f"deleted server {server_id}", True

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"delete server {server_id}",
        execute_fn=_do_delete,
        source="cockpit",
    )
    return resp.to_http_dict()


# ── Categories ──

@rooms_router.get("/servers/{server_id}/categories")
def list_categories(server_id: str, user=Depends(require_clerk_auth)):
    _require_server_member(user, server_id)
    return [c for c in _load("categories") if c["server_id"] == server_id]


@rooms_router.post("/servers/{server_id}/categories")
def create_category(server_id: str, req: CreateCategoryReq, user=Depends(require_clerk_auth)):
    _require_server_perm(user, server_id, "manage_channels")
    uid = _user_id(user)

    def _do_create():
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
        _audit(server_id, None, "category_created", uid, {"name": req.name})
        return f"created category {req.name}", True

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"create category {req.name} in server {server_id}",
        execute_fn=_do_create,
        source="cockpit",
    )
    return resp.to_http_dict()


@rooms_router.patch("/categories/{cat_id}")
def update_category(cat_id: str, req: UpdateCategoryReq, user=Depends(require_clerk_auth)):
    categories = _load("categories")
    cat = next((c for c in categories if c["id"] == cat_id), None)
    if not cat:
        raise HTTPException(404, "Category not found")
    _require_server_perm(user, cat["server_id"], "manage_channels")
    updates = req.model_dump(exclude_none=True)

    def _do_update():
        cats = _load("categories")
        for c in cats:
            if c["id"] == cat_id:
                for k, v in updates.items():
                    c[k] = v
                _save("categories", cats)
                return f"updated category {cat_id}", True
        return "category not found", False

    resp = governed_mutation(
        mutation_name="settings_update",
        intent=f"update category {cat_id}",
        execute_fn=_do_update,
        source="cockpit",
    )
    return resp.to_http_dict()


@rooms_router.delete("/categories/{cat_id}")
def delete_category(cat_id: str, user=Depends(require_clerk_auth)):
    categories = _load("categories")
    cat = next((c for c in categories if c["id"] == cat_id), None)
    if not cat:
        raise HTTPException(404, "Category not found")
    _require_server_perm(user, cat["server_id"], "manage_channels")

    def _do_delete():
        cats = _load("categories")
        cats = [c for c in cats if c["id"] != cat_id]
        _save("categories", cats)
        return f"deleted category {cat_id}", True

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"delete category {cat_id}",
        execute_fn=_do_delete,
        source="cockpit",
    )
    return resp.to_http_dict()


# ── Channels ──

@rooms_router.get("/servers/{server_id}/channels")
def list_channels(server_id: str, user=Depends(require_clerk_auth)):
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
def create_channel(server_id: str, req: CreateChannelReq, user=Depends(require_clerk_auth)):
    _require_server_perm(user, server_id, "manage_channels")
    uid = _user_id(user)

    def _do_create():
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
        _audit(server_id, ch["id"], "channel_created", uid, {"name": req.name, "type": req.type})
        _push_room_event("channel.created", {"server_id": server_id, "channel": ch})
        return f"created channel {req.name}", True

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"create channel {req.name} in server {server_id}",
        execute_fn=_do_create,
        source="cockpit",
    )
    return resp.to_http_dict()


@rooms_router.patch("/channels/{channel_id}")
def update_channel(channel_id: str, req: UpdateChannelReq, user=Depends(require_clerk_auth)):
    server_id = _require_channel_access(user, channel_id)
    _require_server_perm(user, server_id, "manage_channels")
    updates = req.model_dump(exclude_none=True)

    def _do_update():
        channels = _load("channels")
        for c in channels:
            if c["id"] == channel_id:
                for k, v in updates.items():
                    c[k] = v
                _save("channels", channels)
                return f"updated channel {channel_id}", True
        return "channel not found", False

    resp = governed_mutation(
        mutation_name="settings_update",
        intent=f"update channel {channel_id}",
        execute_fn=_do_update,
        source="cockpit",
    )
    return resp.to_http_dict()


@rooms_router.delete("/channels/{channel_id}")
def delete_channel(channel_id: str, user=Depends(require_clerk_auth)):
    channels = _load("channels")
    ch = next((c for c in channels if c["id"] == channel_id), None)
    if not ch:
        raise HTTPException(404, "Channel not found")
    _require_server_perm(user, ch["server_id"], "manage_channels")
    uid = _user_id(user)
    ch_server = ch["server_id"]
    ch_name = ch["name"]

    def _do_delete():
        chans = _load("channels")
        _audit(ch_server, channel_id, "channel_deleted", uid, {"name": ch_name})
        chans = [c for c in chans if c["id"] != channel_id]
        _save("channels", chans)
        _push_room_event("channel.deleted", {"server_id": ch_server, "channel_id": channel_id})
        return f"deleted channel {channel_id}", True

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"delete channel {channel_id}",
        execute_fn=_do_delete,
        source="cockpit",
    )
    return resp.to_http_dict()


# ── Messages ──

@rooms_router.get("/channels/{channel_id}/messages")
def list_messages(channel_id: str, limit: int = 50, before: str | None = None, user=Depends(require_clerk_auth)):
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
def send_message(channel_id: str, req: SendMessageReq, user=Depends(require_clerk_auth)):
    _require_channel_access(user, channel_id, "send_messages")
    uid = _user_id(user)
    dname = _display_name(user)

    def _do_send():
        messages = _load("messages")
        reply_preview = None
        if req.reply_to_id:
            parent = next((m for m in messages if m["id"] == req.reply_to_id), None)
            if parent:
                reply_preview = parent["content"][:80]

        msg = {
            "id": _uid(),
            "channel_id": channel_id,
            "author_id": uid,
            "author_name": dname,
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

        channels = _load("channels")
        for c in channels:
            if c["id"] == channel_id:
                c["last_message_at"] = msg["created_at"]
                break
        _save("channels", channels)

        _push_room_event("message.created", {"channel_id": channel_id, "message": msg})
        return f"sent message to {channel_id}", True

    resp = governed_mutation(
        mutation_name="conversation_send",
        intent=f"send message to channel {channel_id}",
        execute_fn=_do_send,
        source="cockpit",
    )
    return resp.to_http_dict()


@rooms_router.patch("/messages/{message_id}")
def edit_message(message_id: str, req: EditMessageReq, user=Depends(require_clerk_auth)):
    messages = _load("messages")
    target = next((m for m in messages if m["id"] == message_id), None)
    if not target:
        raise HTTPException(404, "Message not found")
    if target["author_id"] != _user_id(user):
        raise HTTPException(403, "Can only edit own messages")

    def _do_edit():
        msgs = _load("messages")
        for m in msgs:
            if m["id"] == message_id:
                m["content"] = req.content
                m["edited"] = True
                m["updated_at"] = _now()
                _save("messages", msgs)
                _push_room_event("message.updated", {"channel_id": m["channel_id"], "message": m})
                return f"edited message {message_id}", True
        return "message not found", False

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"edit message {message_id}",
        execute_fn=_do_edit,
        source="cockpit",
    )
    return resp.to_http_dict()


@rooms_router.delete("/messages/{message_id}")
def delete_message(message_id: str, user=Depends(require_clerk_auth)):
    messages = _load("messages")
    target = next((m for m in messages if m["id"] == message_id), None)
    if not target:
        raise HTTPException(404, "Message not found")
    ch_id = target["channel_id"]
    server_id = _channel_server_id(ch_id)
    uid = _user_id(user)
    if target["author_id"] != uid:
        if server_id:
            perms = _effective_permissions(user, server_id)
            if "manage_messages" not in perms and "administrator" not in perms and not _is_server_owner(user, server_id):
                raise HTTPException(403, "Can only delete own messages or with manage_messages permission")

    def _do_delete():
        msgs = _load("messages")
        for m in msgs:
            if m["id"] == message_id:
                m["deleted"] = True
                m["content"] = ""
                _save("messages", msgs)
                _push_room_event("message.deleted", {"channel_id": ch_id, "message_id": message_id})
                return f"deleted message {message_id}", True
        return "message not found", False

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"delete message {message_id}",
        execute_fn=_do_delete,
        source="cockpit",
    )
    return resp.to_http_dict()


@rooms_router.post("/messages/{message_id}/pin")
def pin_message(message_id: str, req: PinMessageReq, user=Depends(require_clerk_auth)):
    messages = _load("messages")
    target = next((m for m in messages if m["id"] == message_id), None)
    if not target:
        raise HTTPException(404, "Message not found")
    server_id = _channel_server_id(target["channel_id"])
    if server_id:
        _require_server_perm(user, server_id, "manage_messages")

    def _do_pin():
        msgs = _load("messages")
        for m in msgs:
            if m["id"] == message_id:
                m["pinned"] = req.pinned
                _save("messages", msgs)
                return f"{'pinned' if req.pinned else 'unpinned'} message {message_id}", True
        return "message not found", False

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"{'pin' if req.pinned else 'unpin'} message {message_id}",
        execute_fn=_do_pin,
        source="cockpit",
    )
    return resp.to_http_dict()


@rooms_router.post("/messages/{message_id}/reactions")
def add_reaction(message_id: str, req: ReactionReq, user=Depends(require_clerk_auth)):
    user_id = _user_id(user)

    def _do_react():
        messages = _load("messages")
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
                return f"reacted {req.emoji} to {message_id}", True
        return "message not found", False

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"add reaction {req.emoji} to message {message_id}",
        execute_fn=_do_react,
        source="cockpit",
    )
    return resp.to_http_dict()


@rooms_router.delete("/messages/{message_id}/reactions/{emoji}")
def remove_reaction(message_id: str, emoji: str, user=Depends(require_clerk_auth)):
    user_id = _user_id(user)

    def _do_unreact():
        messages = _load("messages")
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
                return f"removed reaction {emoji} from {message_id}", True
        return "message not found", False

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"remove reaction {emoji} from message {message_id}",
        execute_fn=_do_unreact,
        source="cockpit",
    )
    return resp.to_http_dict()


# ── Threads ──

@rooms_router.get("/channels/{channel_id}/threads")
def list_threads(channel_id: str, user=Depends(require_clerk_auth)):
    _require_channel_access(user, channel_id)
    return [t for t in _load("threads") if t["channel_id"] == channel_id]


@rooms_router.post("/channels/{channel_id}/threads")
def create_thread(channel_id: str, req: CreateThreadReq, user=Depends(require_clerk_auth)):
    _require_channel_access(user, channel_id, "send_messages")
    uid = _user_id(user)

    def _do_create():
        threads = _load("threads")
        thread = {
            "id": _uid(),
            "channel_id": channel_id,
            "name": req.name,
            "created_by": uid,
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
        return f"created thread {req.name}", True

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"create thread {req.name} in channel {channel_id}",
        execute_fn=_do_create,
        source="cockpit",
    )
    return resp.to_http_dict()


@rooms_router.patch("/threads/{thread_id}")
def update_thread(thread_id: str, req: UpdateThreadReq, user=Depends(require_clerk_auth)):
    updates = req.model_dump(exclude_none=True)

    def _do_update():
        threads = _load("threads")
        for t in threads:
            if t["id"] == thread_id:
                for k, v in updates.items():
                    t[k] = v
                _save("threads", threads)
                return f"updated thread {thread_id}", True
        return "thread not found", False

    resp = governed_mutation(
        mutation_name="settings_update",
        intent=f"update thread {thread_id}",
        execute_fn=_do_update,
        source="cockpit",
    )
    return resp.to_http_dict()


# ── Forum ──

@rooms_router.get("/channels/{channel_id}/forum/posts")
def list_forum_posts(channel_id: str, user=Depends(require_clerk_auth)):
    _require_channel_access(user, channel_id)
    return [p for p in _load("forum_posts") if p["channel_id"] == channel_id]


@rooms_router.post("/channels/{channel_id}/forum/posts")
def create_forum_post(channel_id: str, req: CreateForumPostReq, user=Depends(require_clerk_auth)):
    _require_channel_access(user, channel_id, "send_messages")
    uid = _user_id(user)
    dname = _display_name(user)

    def _do_create():
        posts = _load("forum_posts")
        post = {
            "id": _uid(),
            "channel_id": channel_id,
            "title": req.title,
            "body": req.body,
            "author_id": uid,
            "author_name": dname,
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
        return f"created forum post {req.title}", True

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"create forum post {req.title} in channel {channel_id}",
        execute_fn=_do_create,
        source="cockpit",
    )
    return resp.to_http_dict()


@rooms_router.patch("/forum/posts/{post_id}")
def update_forum_post(post_id: str, req: UpdateForumPostReq, user=Depends(require_clerk_auth)):
    updates = req.model_dump(exclude_none=True)

    def _do_update():
        posts = _load("forum_posts")
        for p in posts:
            if p["id"] == post_id:
                for k, v in updates.items():
                    p[k] = v
                p["updated_at"] = _now()
                _save("forum_posts", posts)
                return f"updated forum post {post_id}", True
        return "forum post not found", False

    resp = governed_mutation(
        mutation_name="settings_update",
        intent=f"update forum post {post_id}",
        execute_fn=_do_update,
        source="cockpit",
    )
    return resp.to_http_dict()


@rooms_router.get("/channels/{channel_id}/forum/tags")
def list_forum_tags(channel_id: str, user=Depends(require_clerk_auth)):
    _require_channel_access(user, channel_id)
    return [t for t in _load("forum_tags") if t["channel_id"] == channel_id]


@rooms_router.post("/channels/{channel_id}/forum/tags")
def create_forum_tag(channel_id: str, req: CreateForumTagReq, user=Depends(require_clerk_auth)):
    _require_channel_access(user, channel_id, "manage_channels")

    def _do_create():
        tags = _load("forum_tags")
        tag = {
            "id": _uid(),
            "channel_id": channel_id,
            "name": req.name,
            "color": req.color,
        }
        tags.append(tag)
        _save("forum_tags", tags)
        return f"created forum tag {req.name}", True

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"create forum tag {req.name} in channel {channel_id}",
        execute_fn=_do_create,
        source="cockpit",
    )
    return resp.to_http_dict()


# ── Roles ──

@rooms_router.get("/servers/{server_id}/roles")
def list_roles(server_id: str, user=Depends(require_clerk_auth)):
    _require_server_member(user, server_id)
    return [r for r in _load("roles") if r["server_id"] == server_id]


@rooms_router.post("/servers/{server_id}/roles")
def create_role(server_id: str, req: CreateRoleReq, user=Depends(require_clerk_auth)):
    _require_server_perm(user, server_id, "manage_roles")
    uid = _user_id(user)

    def _do_create():
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
        _audit(server_id, None, "role_created", uid, {"name": req.name})
        return f"created role {req.name}", True

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"create role {req.name} in server {server_id}",
        execute_fn=_do_create,
        source="cockpit",
    )
    return resp.to_http_dict()


@rooms_router.patch("/roles/{role_id}")
def update_role(role_id: str, req: UpdateRoleReq, user=Depends(require_clerk_auth)):
    roles = _load("roles")
    role = next((r for r in roles if r["id"] == role_id), None)
    if not role:
        raise HTTPException(404, "Role not found")
    _require_server_perm(user, role["server_id"], "manage_roles")
    updates = req.model_dump(exclude_none=True)

    def _do_update():
        rs = _load("roles")
        for r in rs:
            if r["id"] == role_id:
                for k, v in updates.items():
                    r[k] = v
                _save("roles", rs)
                return f"updated role {role_id}", True
        return "role not found", False

    resp = governed_mutation(
        mutation_name="settings_update",
        intent=f"update role {role_id}",
        execute_fn=_do_update,
        source="cockpit",
    )
    return resp.to_http_dict()


@rooms_router.delete("/roles/{role_id}")
def delete_role(role_id: str, user=Depends(require_clerk_auth)):
    roles = _load("roles")
    role = next((r for r in roles if r["id"] == role_id), None)
    if not role:
        raise HTTPException(404, "Role not found")
    _require_server_perm(user, role["server_id"], "manage_roles")

    def _do_delete():
        rs = _load("roles")
        rs = [r for r in rs if r["id"] != role_id]
        _save("roles", rs)
        return f"deleted role {role_id}", True

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"delete role {role_id}",
        execute_fn=_do_delete,
        source="cockpit",
    )
    return resp.to_http_dict()


# ── Members ──

@rooms_router.get("/servers/{server_id}/members")
def list_members(server_id: str, user=Depends(require_clerk_auth)):
    _require_server_member(user, server_id)
    return [m for m in _load("members") if m["server_id"] == server_id]


@rooms_router.post("/servers/{server_id}/members/{user_id}/roles")
def assign_member_role(server_id: str, user_id: str, req: RoleAssignReq, user=Depends(require_clerk_auth)):
    _require_server_perm(user, server_id, "manage_roles")
    caller = _user_id(user)

    def _do_assign():
        members = _load("members")
        for m in members:
            if m["server_id"] == server_id and m["user_id"] == user_id:
                if req.role_id not in m.get("roles", []):
                    m.setdefault("roles", []).append(req.role_id)
                    _save("members", members)
                    _audit(server_id, None, "role_assigned", caller, {"user_id": user_id, "role_id": req.role_id})
                return f"assigned role {req.role_id} to {user_id}", True
        return "member not found", False

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"assign role {req.role_id} to member {user_id} in server {server_id}",
        execute_fn=_do_assign,
        source="cockpit",
    )
    return resp.to_http_dict()


@rooms_router.delete("/servers/{server_id}/members/{user_id}/roles/{role_id}")
def remove_member_role(server_id: str, user_id: str, role_id: str, user=Depends(require_clerk_auth)):
    _require_server_perm(user, server_id, "manage_roles")

    def _do_remove():
        members = _load("members")
        for m in members:
            if m["server_id"] == server_id and m["user_id"] == user_id:
                m["roles"] = [r for r in m.get("roles", []) if r != role_id]
                _save("members", members)
                return f"removed role {role_id} from {user_id}", True
        return "member not found", False

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"remove role {role_id} from member {user_id} in server {server_id}",
        execute_fn=_do_remove,
        source="cockpit",
    )
    return resp.to_http_dict()


@rooms_router.post("/presence")
def update_presence(req: PresenceReq, user=Depends(require_clerk_auth)):
    uid = _user_id(user)

    def _do_presence():
        members = _load("members")
        for m in members:
            if m["user_id"] == uid:
                m["presence"] = req.status
                m["last_active_at"] = _now()
        _save("members", members)
        _push_room_event("presence.updated", {"user_id": uid, "status": req.status})
        return f"presence set to {req.status}", True

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"update presence to {req.status}",
        execute_fn=_do_presence,
        source="cockpit",
    )
    return resp.to_http_dict()


@rooms_router.post("/typing")
def typing_indicator(req: TypingReq, user=Depends(require_clerk_auth)):
    uid = _user_id(user)
    display = _display_name(user)

    def _do_typing():
        event = "typing.started" if req.typing else "typing.stopped"
        _push_room_event(event, {
            "channel_id": req.channel_id,
            "user_id": uid,
            "user_name": display,
        })
        return f"typing {'started' if req.typing else 'stopped'}", True

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"typing indicator in channel {req.channel_id}",
        execute_fn=_do_typing,
        source="cockpit",
    )
    return resp.to_http_dict()


# ── Invites ──

@rooms_router.get("/servers/{server_id}/invites")
def list_invites(server_id: str, user=Depends(require_clerk_auth)):
    _require_server_member(user, server_id)
    return [inv for inv in _load("invites") if inv["server_id"] == server_id and not inv.get("revoked")]


@rooms_router.post("/servers/{server_id}/invites")
def create_invite(server_id: str, req: CreateInviteReq, user=Depends(require_clerk_auth)):
    _require_server_perm(user, server_id, "create_invites")
    caller = _user_id(user)

    def _do_create():
        invites = _load("invites")
        expires_at = None
        if req.expires_hours:
            expires_at = (datetime.now(timezone.utc) + timedelta(hours=req.expires_hours)).isoformat()

        invite = {
            "id": _uid(),
            "server_id": server_id,
            "channel_id": req.channel_id,
            "room_type": req.room_type,
            "created_by": caller,
            "code": secrets.token_urlsafe(16),
            "label": req.label,
            "max_uses": req.max_uses,
            "uses": 0,
            "expires_at": expires_at,
            "allowed_email_domains": req.allowed_email_domains,
            "allowed_emails": req.allowed_emails,
            "guest_role": "temporary_guest",
            "permissions": req.permissions.model_dump(),
            "role_on_join": req.role_on_join,
            "created_at": _now(),
            "revoked": False,
        }
        invites.append(invite)
        _save("invites", invites)
        _audit(server_id, None, "invite_created", caller, {"code": invite["code"]})
        return f"created invite for server {server_id}", True

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"create invite for server {server_id}",
        execute_fn=_do_create,
        source="cockpit",
    )
    return resp.to_http_dict()


@rooms_router.delete("/invites/{invite_id}")
def revoke_invite(invite_id: str, user=Depends(require_clerk_auth)):
    invites = _load("invites")
    inv_match = next((inv for inv in invites if inv["id"] == invite_id), None)
    if not inv_match:
        raise HTTPException(404, "Invite not found")
    _require_server_perm(user, inv_match["server_id"], "manage_server")

    def _do_revoke():
        inv_list = _load("invites")
        for inv in inv_list:
            if inv["id"] == invite_id:
                inv["revoked"] = True
                _save("invites", inv_list)
                return f"revoked invite {invite_id}", True
        return "invite not found", False

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"revoke invite {invite_id}",
        execute_fn=_do_revoke,
        source="cockpit",
    )
    return resp.to_http_dict()


def _find_invite_by_code(code: str) -> dict | None:
    invites = _load("invites")
    for inv in invites:
        if inv.get("code") == code and not inv.get("revoked"):
            return inv
    return None


def _validate_invite(invite: dict) -> str | None:
    """Returns error message if invite is invalid, None if valid."""
    if invite.get("revoked"):
        return "Invite has been revoked"
    if invite.get("expires_at"):
        from datetime import datetime as dt
        try:
            exp = dt.fromisoformat(invite["expires_at"])
            if exp < dt.now(timezone.utc):
                return "Invite has expired"
        except (ValueError, TypeError):
            pass
    if invite.get("max_uses") is not None and invite.get("uses", 0) >= invite["max_uses"]:
        return "Invite has reached maximum uses"
    return None


@rooms_public_router.get("/invite/{code}/info")
def get_invite_info(code: str):
    """Public endpoint — no auth required. Returns invite metadata for guest join page."""
    invite = _find_invite_by_code(code)
    if not invite:
        return {"valid": False, "error": "Invalid or expired invite link"}

    validation_error = _validate_invite(invite)
    if validation_error:
        return {"valid": False, "error": validation_error}

    # Look up room and server names
    channel_id = invite.get("channel_id")
    room_name = "Room"
    server_name = "Server"
    if channel_id:
        channels = _load("channels")
        ch = next((c for c in channels if c["id"] == channel_id), None)
        if ch:
            room_name = ch.get("name", "Room")
            servers = _load("servers")
            srv = next((s for s in servers if s["id"] == ch.get("server_id")), None)
            if srv:
                server_name = srv.get("name", "Server")

    requires_email = bool(
        invite.get("allowed_email_domains") or invite.get("allowed_emails")
    )

    return {
        "valid": True,
        "room_name": room_name,
        "room_type": invite.get("room_type", "voice"),
        "server_name": server_name,
        "label": invite.get("label"),
        "permissions": invite.get("permissions", {"can_speak": True, "can_video": True, "can_screen_share": False, "can_chat": True}),
        "requires_email": requires_email,
        "expires_at": invite.get("expires_at"),
    }


@rooms_public_router.post("/invite/{code}/join")
def guest_join_via_invite(code: str, req: GuestJoinReq):
    """Public endpoint — no auth required. Validates invite and returns a LiveKit token for the guest."""
    invite = _find_invite_by_code(code)
    if not invite:
        raise HTTPException(404, "Invalid or expired invite link")

    validation_error = _validate_invite(invite)
    if validation_error:
        raise HTTPException(403, validation_error)

    # Validate email restrictions
    if invite.get("allowed_emails") and req.guest_email:
        if req.guest_email.lower() not in [e.lower() for e in invite["allowed_emails"]]:
            raise HTTPException(403, "Email not authorized for this invite")
    if invite.get("allowed_email_domains") and req.guest_email:
        domain = req.guest_email.split("@")[-1].lower() if "@" in req.guest_email else ""
        if domain not in [d.lower() for d in invite["allowed_email_domains"]]:
            raise HTTPException(403, "Email domain not authorized for this invite")
    if (invite.get("allowed_emails") or invite.get("allowed_email_domains")) and not req.guest_email:
        raise HTTPException(400, "Email required for this invite")

    channel_id = invite.get("channel_id")
    if not channel_id:
        raise HTTPException(400, "Invite has no channel")

    invite_id = invite["id"]
    server_id = invite.get("server_id", "")
    result_holder: dict = {}

    def _do_join():
        invites = _load("invites")
        for inv in invites:
            if inv["id"] == invite_id:
                inv["uses"] = inv.get("uses", 0) + 1
                break
        _save("invites", invites)

        room_name = f"room-{channel_id}"
        guest_identity = f"temporary_guest:{invite_id}:{secrets.token_urlsafe(8)}"

        api_key = os.environ.get("LIVEKIT_API_KEY", "")
        api_secret = os.environ.get("LIVEKIT_API_SECRET", "")
        livekit_ws = os.environ.get("LIVEKIT_WS_URL", "")
        cockpit_domain = os.environ.get("COCKPIT_DOMAIN", "")
        if cockpit_domain:
            livekit_ws = f"wss://{cockpit_domain}/livekit/"

        permissions_data = invite.get("permissions", {})
        publish_sources: list[str] = []
        if permissions_data.get("can_speak", False):
            publish_sources.append("microphone")
        if permissions_data.get("can_video", False):
            publish_sources.append("camera")
        if permissions_data.get("can_screen_share", False):
            publish_sources.extend(["screen_share", "screen_share_audio"])

        if api_key and api_secret:
            now = datetime.now(timezone.utc)
            claims = {
                "iss": api_key,
                "sub": guest_identity,
                "name": req.guest_name,
                "nbf": int(now.timestamp()),
                "exp": int((now + timedelta(hours=2)).timestamp()),
                "jti": uuid.uuid4().hex,
                "video": {
                    "roomJoin": True,
                    "room": room_name,
                    "canPublish": len(publish_sources) > 0,
                    "canPublishSources": publish_sources,
                    "canSubscribe": True,
                    "canPublishData": permissions_data.get("can_chat", True),
                },
            }
            jwt_token = pyjwt.encode(claims, api_secret, algorithm="HS256")
        else:
            jwt_token = f"guest-token-{guest_identity}"

        _audit(
            server_id,
            channel_id,
            "guest_joined",
            guest_identity,
            {"invite_id": invite_id, "guest_name": req.guest_name, "guest_email": req.guest_email},
        )
        result_holder["token"] = jwt_token
        result_holder["url"] = livekit_ws
        result_holder["room"] = room_name
        result_holder["identity"] = guest_identity
        return f"guest {req.guest_name} joined via invite {invite_id}", True

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"guest join via invite {code}",
        execute_fn=_do_join,
        source="cockpit",
    )
    if resp.success and result_holder:
        return result_holder
    return resp.to_http_dict()


# ── Room Chat (persistent, survives reconnect/refresh) ──


class RoomChatReq(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    sender_type: str = "owner"


@rooms_router.get("/channels/{channel_id}/room-chat")
def list_room_chat(channel_id: str, limit: int = 100, user=Depends(require_clerk_auth)):
    _require_channel_access(user, channel_id, "view_channel")
    msgs = _load("room_chat")
    ch_msgs = [m for m in msgs if m["channel_id"] == channel_id]
    ch_msgs.sort(key=lambda m: m["created_at"])
    return ch_msgs[-limit:]


@rooms_router.post("/channels/{channel_id}/room-chat")
def send_room_chat(channel_id: str, req: RoomChatReq, user=Depends(require_clerk_auth)):
    _require_channel_access(user, channel_id)
    uid = _user_id(user)
    display = _display_name(user)

    def _do_send():
        msg = {
            "id": _uid(),
            "channel_id": channel_id,
            "sender_identity": uid,
            "sender_display_name": display,
            "sender_type": "owner",
            "body": req.content,
            "created_at": _now(),
        }
        msgs = _load("room_chat")
        ch_msgs = [m for m in msgs if m["channel_id"] == channel_id]
        if len(ch_msgs) >= _GUEST_CHAT_PER_CHANNEL_CAP:
            keep_ids = {m["id"] for m in ch_msgs[-(_GUEST_CHAT_PER_CHANNEL_CAP - 1):]}
            msgs = [m for m in msgs if m["channel_id"] != channel_id or m["id"] in keep_ids]
        msgs.append(msg)
        _save("room_chat", msgs)
        _push_room_event("room_chat.message", {"channel_id": channel_id, "message": msg})
        return f"sent room chat in {channel_id}", True

    resp = governed_mutation(
        mutation_name="conversation_send",
        intent=f"send room chat in channel {channel_id}",
        execute_fn=_do_send,
        source="cockpit",
    )
    return resp.to_http_dict()


class GuestChatReq(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


_GUEST_CHAT_MAX_LIMIT = 200
_GUEST_CHAT_PER_CHANNEL_CAP = 5000


@rooms_public_router.get("/invite/{code}/chat")
def guest_list_room_chat(
    code: str,
    limit: int = 100,
    authorization: str | None = Header(None),
):
    claims = _verify_guest_token(authorization)
    invite = _find_invite_by_code(code)
    if not invite:
        raise HTTPException(404, "Invalid invite")
    validation_error = _validate_invite(invite)
    if validation_error:
        raise HTTPException(403, validation_error)
    permissions = invite.get("permissions", {})
    if not permissions.get("can_chat", True):
        raise HTTPException(403, "Chat not permitted")
    channel_id = invite.get("channel_id")
    if not channel_id:
        raise HTTPException(400, "Invite has no channel")
    room_claim = (claims.get("video") or {}).get("room", "")
    if room_claim != f"room-{channel_id}":
        raise HTTPException(403, "Token does not match this room")
    clamped = min(max(limit, 1), _GUEST_CHAT_MAX_LIMIT)
    msgs = _load("room_chat")
    ch_msgs = [m for m in msgs if m["channel_id"] == channel_id]
    ch_msgs.sort(key=lambda m: m["created_at"])
    return ch_msgs[-clamped:]


@rooms_public_router.post("/invite/{code}/chat")
def guest_send_room_chat(
    code: str,
    req: GuestChatReq,
    authorization: str | None = Header(None),
):
    claims = _verify_guest_token(authorization)
    invite = _find_invite_by_code(code)
    if not invite:
        raise HTTPException(404, "Invalid invite")
    validation_error = _validate_invite(invite)
    if validation_error:
        raise HTTPException(403, validation_error)
    permissions = invite.get("permissions", {})
    if not permissions.get("can_chat", True):
        raise HTTPException(403, "Chat not permitted")
    channel_id = invite.get("channel_id")
    if not channel_id:
        raise HTTPException(400, "Invite has no channel")
    room_claim = (claims.get("video") or {}).get("room", "")
    if room_claim != f"room-{channel_id}":
        raise HTTPException(403, "Token does not match this room")
    guest_identity = claims["sub"]
    guest_name = claims.get("name", "Guest")
    invite_id = invite["id"]

    def _do_guest_chat():
        msg = {
            "id": _uid(),
            "channel_id": channel_id,
            "sender_identity": guest_identity,
            "sender_display_name": guest_name,
            "sender_type": "guest",
            "body": req.content,
            "created_at": _now(),
            "invite_id": invite_id,
        }
        msgs = _load("room_chat")
        ch_msgs = [m for m in msgs if m["channel_id"] == channel_id]
        if len(ch_msgs) >= _GUEST_CHAT_PER_CHANNEL_CAP:
            keep_ids = {m["id"] for m in ch_msgs[-(_GUEST_CHAT_PER_CHANNEL_CAP - 1):]}
            msgs = [m for m in msgs if m["channel_id"] != channel_id or m["id"] in keep_ids]
        msgs.append(msg)
        _save("room_chat", msgs)
        _push_room_event("room_chat.message", {"channel_id": channel_id, "message": msg})
        return f"guest chat sent in {channel_id}", True

    resp = governed_mutation(
        mutation_name="conversation_send",
        intent=f"guest send room chat in channel {channel_id}",
        execute_fn=_do_guest_chat,
        source="cockpit",
    )
    return resp.to_http_dict()


# ── Meeting ──

@rooms_router.get("/channels/{channel_id}/meeting")
def get_meeting(channel_id: str, user=Depends(require_clerk_auth)):
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
def update_meeting(channel_id: str, req: UpdateMeetingReq, user=Depends(require_clerk_auth)):
    _require_channel_access(user, channel_id)
    updates = req.model_dump(exclude_none=True)

    def _do_update():
        meetings = _load("meetings")
        for m in meetings:
            if m["channel_id"] == channel_id:
                for k, v in updates.items():
                    m[k] = v
                _save("meetings", meetings)
                return f"updated meeting in {channel_id}", True
        return "meeting not found", False

    resp = governed_mutation(
        mutation_name="settings_update",
        intent=f"update meeting in channel {channel_id}",
        execute_fn=_do_update,
        source="cockpit",
    )
    return resp.to_http_dict()


@rooms_router.post("/channels/{channel_id}/meeting/actions")
def add_meeting_action(channel_id: str, req: AddActionItemReq, user=Depends(require_clerk_auth)):
    _require_channel_access(user, channel_id)

    def _do_add():
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
                return f"added action item to meeting in {channel_id}", True
        return "meeting not found", False

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"add action item to meeting in channel {channel_id}",
        execute_fn=_do_add,
        source="cockpit",
    )
    return resp.to_http_dict()


@rooms_router.post("/channels/{channel_id}/meeting/actions/{item_id}/toggle")
def toggle_meeting_action(channel_id: str, item_id: str, user=Depends(require_clerk_auth)):
    _require_channel_access(user, channel_id)

    def _do_toggle():
        meetings = _load("meetings")
        for m in meetings:
            if m["channel_id"] == channel_id:
                for item in m.get("action_items", []):
                    if item["id"] == item_id:
                        item["completed"] = not item.get("completed", False)
                        _save("meetings", meetings)
                        return f"toggled action item {item_id}", True
        return "action item not found", False

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"toggle meeting action item {item_id} in channel {channel_id}",
        execute_fn=_do_toggle,
        source="cockpit",
    )
    return resp.to_http_dict()


@rooms_router.post("/channels/{channel_id}/meeting/end")
def end_meeting(channel_id: str, user=Depends(require_clerk_auth)):
    _require_channel_access(user, channel_id)
    uid = _user_id(user)

    def _do_end():
        meetings = _load("meetings")
        for m in meetings:
            if m["channel_id"] == channel_id:
                m["ended_at"] = _now()
                _save("meetings", meetings)
                invites = _load("invites")
                for inv in invites:
                    if inv.get("channel_id") == channel_id and not inv.get("revoked"):
                        inv["revoked"] = True
                _save("invites", invites)
                _audit(
                    _find_server_for_channel(channel_id),
                    channel_id,
                    "meeting_ended",
                    uid,
                    {},
                )
                return f"ended meeting in {channel_id}", True
        return "meeting not found", False

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"end meeting in channel {channel_id}",
        execute_fn=_do_end,
        source="cockpit",
    )
    return resp.to_http_dict()


def _find_server_for_channel(channel_id: str) -> str:
    channels = _load("channels")
    ch = next((c for c in channels if c["id"] == channel_id), None)
    return ch.get("server_id", "") if ch else ""


# ── Voice ──

@rooms_router.get("/channels/{channel_id}/voice")
def get_voice_state(channel_id: str, user=Depends(require_clerk_auth)):
    _require_channel_access(user, channel_id)
    voice = _load("voice_states")
    state = next((v for v in voice if v["channel_id"] == channel_id), None)
    if not state:
        state = {"channel_id": channel_id, "participants": [], "topic": "", "capacity": 25, "locked": False}
    return state


@rooms_router.post("/channels/{channel_id}/voice/join")
def join_voice(channel_id: str, user=Depends(require_clerk_auth)):
    _require_channel_access(user, channel_id, "connect")
    uid = _user_id(user)
    display = _display_name(user)

    def _do_join():
        voice = _load("voice_states")
        state = next((v for v in voice if v["channel_id"] == channel_id), None)
        if not state:
            state = {"channel_id": channel_id, "participants": [], "topic": "", "capacity": 25, "locked": False}
            voice.append(state)

        if not any(p["user_id"] == uid for p in state["participants"]):
            state["participants"].append({
                "user_id": uid,
                "display_name": display,
                "is_speaking": False,
                "is_muted": False,
                "is_deafened": False,
                "joined_at": _now(),
            })
        _save("voice_states", voice)
        return f"joined voice in {channel_id}", True

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"join voice channel {channel_id}",
        execute_fn=_do_join,
        source="cockpit",
    )
    return resp.to_http_dict()


@rooms_router.post("/channels/{channel_id}/voice/leave")
def leave_voice(channel_id: str, user=Depends(require_clerk_auth)):
    _require_channel_access(user, channel_id)
    uid = _user_id(user)

    def _do_leave():
        voice = _load("voice_states")
        for v in voice:
            if v["channel_id"] == channel_id:
                v["participants"] = [p for p in v["participants"] if p["user_id"] != uid]
                _save("voice_states", voice)
                return f"left voice in {channel_id}", True
        return f"left voice in {channel_id}", True

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"leave voice channel {channel_id}",
        execute_fn=_do_leave,
        source="cockpit",
    )
    return resp.to_http_dict()


@rooms_router.post("/channels/{channel_id}/voice/token")
def get_voice_token(channel_id: str, user=Depends(require_clerk_auth)):
    """Generate a LiveKit JWT for joining a voice channel."""
    _require_channel_access(user, channel_id, "connect")

    api_key = os.environ.get("LIVEKIT_API_KEY")
    api_secret = os.environ.get("LIVEKIT_API_SECRET")
    if not api_key or not api_secret:
        raise HTTPException(503, "Voice infrastructure not configured")

    uid = _user_id(user)
    display = _display_name(user)
    result_holder: dict = {}

    def _do_token():
        room_name = f"room-{channel_id}"
        now = datetime.now(timezone.utc)
        claims = {
            "iss": api_key,
            "sub": uid,
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
                "canPublishSources": ["camera", "microphone", "screen_share", "screen_share_audio"],
            },
        }
        token = pyjwt.encode(claims, api_secret, algorithm="HS256")
        livekit_ws = os.environ.get("LIVEKIT_WS_URL", "")
        cockpit_domain = os.environ.get("COCKPIT_DOMAIN", "")
        if cockpit_domain:
            livekit_ws = f"wss://{cockpit_domain}/livekit/"
        result_holder["token"] = token
        result_holder["url"] = livekit_ws
        result_holder["room"] = room_name
        return f"generated voice token for {channel_id}", True

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"generate voice token for channel {channel_id}",
        execute_fn=_do_token,
        source="cockpit",
    )
    if resp.success and result_holder:
        return result_holder
    return resp.to_http_dict()


# ── Advisor Settings ──

@rooms_router.get("/channels/{channel_id}/dex")
def get_advisor_settings(channel_id: str, user=Depends(require_clerk_auth)):
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
def update_advisor_settings(channel_id: str, req: UpdateDexReq, user=Depends(require_clerk_auth)):
    server_id = _require_channel_access(user, channel_id)
    _require_server_perm(user, server_id, "manage_channels")
    updates = req.model_dump(exclude_none=True)

    def _do_update():
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

        for k, v in updates.items():
            settings[k] = v
        _save("dex_settings", dex)
        return f"updated advisor settings for {channel_id}", True

    resp = governed_mutation(
        mutation_name="settings_update",
        intent=f"update advisor settings for channel {channel_id}",
        execute_fn=_do_update,
        source="cockpit",
    )
    return resp.to_http_dict()


@rooms_router.post("/channels/{channel_id}/dex/summarize")
def advisor_summarize(channel_id: str, user=Depends(require_clerk_auth)):
    _require_channel_access(user, channel_id)

    def _do_summarize():
        messages = _load("messages")
        ch_msgs = [m for m in messages if m["channel_id"] == channel_id and not m.get("deleted")]
        ch_msgs.sort(key=lambda m: m["created_at"])
        recent = ch_msgs[-20:]

        if not recent:
            return "No messages in this channel yet.", True

        summary = f"Room summary ({len(recent)} recent messages):\n"
        summary += f"Participants: {', '.join(set(m['author_name'] for m in recent))}\n"
        summary += f"Period: {recent[0]['created_at'][:10]} to {recent[-1]['created_at'][:10]}\n"
        summary += f"Latest topic: {recent[-1]['content'][:100]}"
        return summary, True

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"advisor summarize channel {channel_id}",
        execute_fn=_do_summarize,
        source="cockpit",
    )
    return resp.to_http_dict()


# ── Audit Log ──

@rooms_router.get("/servers/{server_id}/audit-log")
def get_audit_log(server_id: str, user=Depends(require_clerk_auth)):
    _require_server_perm(user, server_id, "view_audit_log")
    events = _load("audit_log")
    server_events = [e for e in events if e["server_id"] == server_id]
    return server_events[-100:]


# ── Artifacts ──

@rooms_router.get("/channels/{channel_id}/artifacts")
def list_artifacts(channel_id: str, user=Depends(require_clerk_auth)):
    _require_channel_access(user, channel_id)
    return [a for a in _load("artifacts") if a["channel_id"] == channel_id]


@rooms_router.post("/channels/{channel_id}/artifacts")
def create_artifact(channel_id: str, req: CreateArtifactReq, user=Depends(require_clerk_auth)):
    _require_channel_access(user, channel_id, "send_messages")
    uid = _user_id(user)

    def _do_create():
        artifacts = _load("artifacts")
        artifact = {
            "id": _uid(),
            "channel_id": channel_id,
            "name": req.name,
            "type": req.type,
            "owner_id": uid,
            "pinned": False,
            "created_at": _now(),
            "metadata": req.metadata,
        }
        artifacts.append(artifact)
        _save("artifacts", artifacts)
        return f"created artifact {req.name} in {channel_id}", True

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"create artifact {req.name} in channel {channel_id}",
        execute_fn=_do_create,
        source="cockpit",
    )
    return resp.to_http_dict()


# ── Search ──

@rooms_router.get("/servers/{server_id}/search")
def search_server(server_id: str, q: str = "", user=Depends(require_clerk_auth)):
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
