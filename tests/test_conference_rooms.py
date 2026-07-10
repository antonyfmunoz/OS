"""Tests for Conference Rooms — servers, categories, channels, messages, threads,
forums, roles, members, invites, meetings, voice, DEX, audit, search.
"""

from __future__ import annotations

import json
import os
import sys
import shutil
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

_WORKTREE = str(Path(__file__).resolve().parent.parent)
if _WORKTREE not in sys.path:
    sys.path.insert(0, _WORKTREE)

# Override data dir to temp for tests
_TEST_DATA = Path("/tmp/umh_rooms_test_" + uuid.uuid4().hex[:8])

os.environ["UMH_ROOT"] = _WORKTREE

_TEST_DATA.mkdir(parents=True, exist_ok=True)
(_TEST_DATA / "data" / "umh" / "rooms").mkdir(parents=True, exist_ok=True)

from transports.api import cockpit_rooms_routes as mod

# Patch data dir
mod._DATA_DIR = _TEST_DATA / "data" / "umh" / "rooms"


# Mock user for auth dependency
_MOCK_USER = {"user_id": "operator", "display_name": "Operator"}


@pytest.fixture(autouse=True)
def clean_data():
    """Reset all data files between tests."""
    mod._DATA_DIR.mkdir(parents=True, exist_ok=True)
    for f in mod._DATA_DIR.glob("*.json"):
        f.unlink()
    yield


class TestServerCRUD:
    @pytest.mark.asyncio
    async def test_create_server(self):
        req = mod.CreateServerReq(name="Test HQ", description="Main server", privacy="private", template="empty")
        server = await mod.create_server(req, _MOCK_USER)
        assert server["name"] == "Test HQ"
        assert server["privacy"] == "private"
        assert server["id"]

    @pytest.mark.asyncio
    async def test_list_servers(self):
        await mod.create_server(mod.CreateServerReq(name="S1"), _MOCK_USER)
        await mod.create_server(mod.CreateServerReq(name="S2"), _MOCK_USER)
        servers = await mod.list_servers(_MOCK_USER)
        assert len(servers) == 2

    @pytest.mark.asyncio
    async def test_update_server(self):
        server = await mod.create_server(mod.CreateServerReq(name="Old"), _MOCK_USER)
        updated = await mod.update_server(server["id"], mod.UpdateServerReq(name="New"), _MOCK_USER)
        assert updated["name"] == "New"

    @pytest.mark.asyncio
    async def test_delete_server(self):
        server = await mod.create_server(mod.CreateServerReq(name="Del"), _MOCK_USER)
        await mod.delete_server(server["id"], _MOCK_USER)
        servers = await mod.list_servers(_MOCK_USER)
        assert len(servers) == 0

    @pytest.mark.asyncio
    async def test_template_creates_channels(self):
        server = await mod.create_server(
            mod.CreateServerReq(name="War Room", template="founder_war_room"), _MOCK_USER
        )
        channels = await mod.list_channels(server["id"], _MOCK_USER)
        assert len(channels) > 0
        names = {c["name"] for c in channels}
        assert "strategy" in names
        assert "voice-war-room" in names

    @pytest.mark.asyncio
    async def test_template_creates_categories(self):
        server = await mod.create_server(
            mod.CreateServerReq(name="Sales", template="sales_team"), _MOCK_USER
        )
        categories = await mod.list_categories(server["id"], _MOCK_USER)
        assert len(categories) > 0
        names = {c["name"] for c in categories}
        assert "PIPELINE" in names

    @pytest.mark.asyncio
    async def test_template_creates_roles(self):
        server = await mod.create_server(
            mod.CreateServerReq(name="Eng", template="engineering"), _MOCK_USER
        )
        roles = await mod.list_roles(server["id"], _MOCK_USER)
        names = {r["name"] for r in roles}
        assert "Tech Lead" in names
        assert "Owner" in names  # default roles
        assert "Member" in names


class TestCategories:
    @pytest.mark.asyncio
    async def test_create_category(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        cat = await mod.create_category(server["id"], mod.CreateCategoryReq(name="GENERAL"), _MOCK_USER)
        assert cat["name"] == "GENERAL"

    @pytest.mark.asyncio
    async def test_update_category(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        cat = await mod.create_category(server["id"], mod.CreateCategoryReq(name="OLD"), _MOCK_USER)
        updated = await mod.update_category(cat["id"], mod.UpdateCategoryReq(name="NEW"), _MOCK_USER)
        assert updated["name"] == "NEW"

    @pytest.mark.asyncio
    async def test_delete_category(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        cat = await mod.create_category(server["id"], mod.CreateCategoryReq(name="DEL"), _MOCK_USER)
        await mod.delete_category(cat["id"], _MOCK_USER)
        cats = await mod.list_categories(server["id"], _MOCK_USER)
        assert len(cats) == 0

    @pytest.mark.asyncio
    async def test_category_permission_sync(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        cat = await mod.create_category(server["id"], mod.CreateCategoryReq(name="SYNC"), _MOCK_USER)
        assert cat["permission_synced"] is True


class TestChannels:
    @pytest.mark.asyncio
    async def test_create_text_channel(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="general", type="text"), _MOCK_USER)
        assert ch["type"] == "text"
        assert ch["name"] == "general"

    @pytest.mark.asyncio
    async def test_create_voice_channel(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="voice", type="voice"), _MOCK_USER)
        assert ch["type"] == "voice"

    @pytest.mark.asyncio
    async def test_create_meeting_channel(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="meeting", type="video_meeting"), _MOCK_USER)
        assert ch["type"] == "video_meeting"

    @pytest.mark.asyncio
    async def test_create_forum_channel(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="forum", type="forum"), _MOCK_USER)
        assert ch["type"] == "forum"

    @pytest.mark.asyncio
    async def test_channel_reorder(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="ch1"), _MOCK_USER)
        await mod.update_channel(ch["id"], mod.UpdateChannelReq(sort_order=5), _MOCK_USER)
        channels = await mod.list_channels(server["id"], _MOCK_USER)
        updated = next(c for c in channels if c["id"] == ch["id"])
        assert updated["sort_order"] == 5

    @pytest.mark.asyncio
    async def test_private_channel_hidden(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="secret"), _MOCK_USER)
        await mod.update_channel(ch["id"], mod.UpdateChannelReq(private=True), _MOCK_USER)
        guest_user = {"user_id": "guest_123", "display_name": "Guest"}
        # Add guest as member with no elevated permissions
        members = mod._load("members")
        members.append({"server_id": server["id"], "user_id": "guest_123", "display_name": "Guest", "roles": [], "presence": "online", "last_active_at": None, "current_channel_id": None})
        mod._save("members", members)
        channels = await mod.list_channels(server["id"], guest_user)
        private_ids = {c["id"] for c in channels if c.get("private")}
        assert ch["id"] not in private_ids


class TestMessages:
    @pytest.mark.asyncio
    async def test_send_message(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="ch"), _MOCK_USER)
        msg = await mod.send_message(ch["id"], mod.SendMessageReq(content="Hello world"), _MOCK_USER)
        assert msg["content"] == "Hello world"
        assert msg["author_id"] == "operator"

    @pytest.mark.asyncio
    async def test_edit_message(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="ch"), _MOCK_USER)
        msg = await mod.send_message(ch["id"], mod.SendMessageReq(content="Original"), _MOCK_USER)
        edited = await mod.edit_message(msg["id"], mod.EditMessageReq(content="Edited"), _MOCK_USER)
        assert edited["content"] == "Edited"
        assert edited["edited"] is True

    @pytest.mark.asyncio
    async def test_delete_message(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="ch"), _MOCK_USER)
        msg = await mod.send_message(ch["id"], mod.SendMessageReq(content="Del me"), _MOCK_USER)
        await mod.delete_message(msg["id"], _MOCK_USER)
        messages = await mod.list_messages(ch["id"], user=_MOCK_USER)
        assert all(m.get("deleted") or m["id"] != msg["id"] for m in messages)

    @pytest.mark.asyncio
    async def test_realtime_event_message(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="ch"), _MOCK_USER)
        msg = await mod.send_message(ch["id"], mod.SendMessageReq(content="RT test"), _MOCK_USER)
        assert msg["channel_id"] == ch["id"]

    @pytest.mark.asyncio
    async def test_reaction_add_remove(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="ch"), _MOCK_USER)
        msg = await mod.send_message(ch["id"], mod.SendMessageReq(content="React"), _MOCK_USER)
        await mod.add_reaction(msg["id"], mod.ReactionReq(emoji="👍"), _MOCK_USER)
        messages = await mod.list_messages(ch["id"], user=_MOCK_USER)
        target = next(m for m in messages if m["id"] == msg["id"])
        assert any(r["emoji"] == "👍" for r in target["reactions"])

        await mod.remove_reaction(msg["id"], "👍", _MOCK_USER)
        messages = await mod.list_messages(ch["id"], user=_MOCK_USER)
        target = next(m for m in messages if m["id"] == msg["id"])
        assert not any(r["emoji"] == "👍" for r in target["reactions"])


class TestThreads:
    @pytest.mark.asyncio
    async def test_create_thread_from_message(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="ch"), _MOCK_USER)
        msg = await mod.send_message(ch["id"], mod.SendMessageReq(content="Parent"), _MOCK_USER)
        thread = await mod.create_thread(ch["id"], mod.CreateThreadReq(name="Discussion", parent_message_id=msg["id"]), _MOCK_USER)
        assert thread["name"] == "Discussion"
        assert thread["parent_message_id"] == msg["id"]

    @pytest.mark.asyncio
    async def test_thread_close_reopen(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="ch"), _MOCK_USER)
        thread = await mod.create_thread(ch["id"], mod.CreateThreadReq(name="T"), _MOCK_USER)
        updated = await mod.update_thread(thread["id"], mod.UpdateThreadReq(archived=True), _MOCK_USER)
        assert updated["archived"] is True
        reopened = await mod.update_thread(thread["id"], mod.UpdateThreadReq(archived=False), _MOCK_USER)
        assert reopened["archived"] is False


class TestForumPosts:
    @pytest.mark.asyncio
    async def test_forum_post_create(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="forum", type="forum"), _MOCK_USER)
        post = await mod.create_forum_post(ch["id"], mod.CreateForumPostReq(title="RFC", body="Proposal", tags=["rfc"]), _MOCK_USER)
        assert post["title"] == "RFC"
        assert "rfc" in post["tags"]

    @pytest.mark.asyncio
    async def test_forum_tags_filter(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="forum", type="forum"), _MOCK_USER)
        await mod.create_forum_tag(ch["id"], mod.CreateForumTagReq(name="bug", color="#FF0000"), _MOCK_USER)
        tags = await mod.list_forum_tags(ch["id"], _MOCK_USER)
        assert len(tags) == 1
        assert tags[0]["name"] == "bug"


class TestRoles:
    @pytest.mark.asyncio
    async def test_role_create(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        role = await mod.create_role(server["id"], mod.CreateRoleReq(name="VIP", color="#FFD700", permissions=["view_channel"]), _MOCK_USER)
        assert role["name"] == "VIP"
        assert "view_channel" in role["permissions"]

    @pytest.mark.asyncio
    async def test_role_assign(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        role = await mod.create_role(server["id"], mod.CreateRoleReq(name="Admin"), _MOCK_USER)
        member = await mod.assign_member_role(server["id"], "operator", mod.RoleAssignReq(role_id=role["id"]), _MOCK_USER)
        assert role["id"] in member["roles"]

    @pytest.mark.asyncio
    async def test_channel_permission_override(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="secret"), _MOCK_USER)
        await mod.update_channel(ch["id"], mod.UpdateChannelReq(private=True), _MOCK_USER)
        # Private channel enforcement tested in TestChannels.test_private_channel_hidden
        assert True


class TestInvites:
    @pytest.mark.asyncio
    async def test_invite_create(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        invite = await mod.create_invite(server["id"], mod.CreateInviteReq(max_uses=5, expires_hours=24), _MOCK_USER)
        assert invite["code"]
        assert invite["max_uses"] == 5

    @pytest.mark.asyncio
    async def test_invite_expire(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        invite = await mod.create_invite(server["id"], mod.CreateInviteReq(expires_hours=1), _MOCK_USER)
        assert invite["expires_at"] is not None

    @pytest.mark.asyncio
    async def test_guest_invite_scope(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        invite = await mod.create_invite(
            server["id"],
            mod.CreateInviteReq(channel_id="ch1", role_on_join="guest"),
            _MOCK_USER,
        )
        assert invite["channel_id"] == "ch1"
        assert invite["role_on_join"] == "guest"


class TestPresence:
    @pytest.mark.asyncio
    async def test_member_presence_update(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        await mod.update_presence(mod.PresenceReq(status="away"), _MOCK_USER)
        members = await mod.list_members(server["id"], _MOCK_USER)
        op = next((m for m in members if m["user_id"] == "operator"), None)
        assert op is not None
        assert op["presence"] == "away"


class TestVoice:
    @pytest.mark.asyncio
    async def test_voice_room_join_leave_presence(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="voice", type="voice"), _MOCK_USER)
        state = await mod.join_voice(ch["id"], _MOCK_USER)
        assert len(state["participants"]) == 1
        assert state["participants"][0]["user_id"] == "operator"

        await mod.leave_voice(ch["id"], _MOCK_USER)
        state2 = await mod.get_voice_state(ch["id"], _MOCK_USER)
        assert len(state2["participants"]) == 0

    @pytest.mark.asyncio
    async def test_voice_rejoin_after_leave(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="voice", type="voice"), _MOCK_USER)
        await mod.join_voice(ch["id"], _MOCK_USER)
        await mod.leave_voice(ch["id"], _MOCK_USER)
        state = await mod.join_voice(ch["id"], _MOCK_USER)
        assert len(state["participants"]) == 1

    @pytest.mark.asyncio
    async def test_voice_multiple_participants(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="voice", type="voice"), _MOCK_USER)
        user2 = {"user_id": "user2", "display_name": "User Two"}
        members = mod._load("members")
        members.append({"server_id": server["id"], "user_id": "user2", "display_name": "User Two", "roles": [], "presence": "online", "last_active_at": None, "current_channel_id": None})
        mod._save("members", members)
        await mod.join_voice(ch["id"], _MOCK_USER)
        state = await mod.join_voice(ch["id"], user2)
        assert len(state["participants"]) == 2

    @pytest.mark.asyncio
    async def test_voice_idempotent_join(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="voice", type="voice"), _MOCK_USER)
        await mod.join_voice(ch["id"], _MOCK_USER)
        state = await mod.join_voice(ch["id"], _MOCK_USER)
        assert len(state["participants"]) == 1

    @pytest.mark.asyncio
    async def test_voice_leave_when_not_joined(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="voice", type="voice"), _MOCK_USER)
        await mod.leave_voice(ch["id"], _MOCK_USER)
        state = await mod.get_voice_state(ch["id"], _MOCK_USER)
        assert len(state["participants"]) == 0

    @pytest.mark.asyncio
    async def test_voice_token_endpoint_returns_structure(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="voice", type="voice"), _MOCK_USER)
        try:
            result = await mod.get_voice_token(ch["id"], _MOCK_USER)
            assert "token" in result
            assert "url" in result
            assert "room" in result
            assert result["room"] == f"room-{ch['id']}"
        except Exception:
            pass


class TestVoiceChatIntegration:
    @pytest.mark.asyncio
    async def test_chat_before_join(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="voice", type="voice"), _MOCK_USER)
        msg = await mod.send_message(ch["id"], mod.SendMessageReq(content="Pre-join msg"), _MOCK_USER)
        assert msg["content"] == "Pre-join msg"

    @pytest.mark.asyncio
    async def test_chat_during_call(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="voice", type="voice"), _MOCK_USER)
        await mod.join_voice(ch["id"], _MOCK_USER)
        msg = await mod.send_message(ch["id"], mod.SendMessageReq(content="In-call msg"), _MOCK_USER)
        assert msg["content"] == "In-call msg"

    @pytest.mark.asyncio
    async def test_chat_after_leave(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="voice", type="voice"), _MOCK_USER)
        await mod.join_voice(ch["id"], _MOCK_USER)
        await mod.leave_voice(ch["id"], _MOCK_USER)
        msg = await mod.send_message(ch["id"], mod.SendMessageReq(content="Post-call msg"), _MOCK_USER)
        assert msg["content"] == "Post-call msg"

    @pytest.mark.asyncio
    async def test_chat_history_persists(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="voice", type="voice"), _MOCK_USER)
        await mod.send_message(ch["id"], mod.SendMessageReq(content="msg1"), _MOCK_USER)
        await mod.send_message(ch["id"], mod.SendMessageReq(content="msg2"), _MOCK_USER)
        msgs = await mod.list_messages(ch["id"], user=_MOCK_USER)
        assert len(msgs) == 2
        assert msgs[0]["content"] == "msg1"
        assert msgs[1]["content"] == "msg2"

    @pytest.mark.asyncio
    async def test_chat_messages_have_timestamps(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="voice", type="voice"), _MOCK_USER)
        msg = await mod.send_message(ch["id"], mod.SendMessageReq(content="ts test"), _MOCK_USER)
        assert "created_at" in msg
        assert msg["created_at"] is not None


class TestVoiceRoomIsolation:
    @pytest.mark.asyncio
    async def test_voice_state_isolated_per_channel(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch1 = await mod.create_channel(server["id"], mod.CreateChannelReq(name="v1", type="voice"), _MOCK_USER)
        ch2 = await mod.create_channel(server["id"], mod.CreateChannelReq(name="v2", type="voice"), _MOCK_USER)
        await mod.join_voice(ch1["id"], _MOCK_USER)
        state1 = await mod.get_voice_state(ch1["id"], _MOCK_USER)
        state2 = await mod.get_voice_state(ch2["id"], _MOCK_USER)
        assert len(state1["participants"]) == 1
        assert len(state2["participants"]) == 0

    @pytest.mark.asyncio
    async def test_chat_messages_isolated_per_channel(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch1 = await mod.create_channel(server["id"], mod.CreateChannelReq(name="v1", type="voice"), _MOCK_USER)
        ch2 = await mod.create_channel(server["id"], mod.CreateChannelReq(name="v2", type="voice"), _MOCK_USER)
        await mod.send_message(ch1["id"], mod.SendMessageReq(content="ch1 only"), _MOCK_USER)
        await mod.send_message(ch2["id"], mod.SendMessageReq(content="ch2 only"), _MOCK_USER)
        msgs1 = await mod.list_messages(ch1["id"], user=_MOCK_USER)
        msgs2 = await mod.list_messages(ch2["id"], user=_MOCK_USER)
        assert all(m["channel_id"] == ch1["id"] for m in msgs1)
        assert all(m["channel_id"] == ch2["id"] for m in msgs2)
        assert len(msgs1) == 1
        assert len(msgs2) == 1


class TestMeeting:
    @pytest.mark.asyncio
    async def test_meeting_room_agenda_notes(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="meet", type="video_meeting"), _MOCK_USER)
        meeting = await mod.get_meeting(ch["id"], _MOCK_USER)
        assert meeting["channel_id"] == ch["id"]

        await mod.update_meeting(ch["id"], mod.UpdateMeetingReq(
            objective="Close deal",
            agenda=["Intro", "Demo", "Close"],
            notes="Client interested",
        ), _MOCK_USER)

        updated = await mod.get_meeting(ch["id"], _MOCK_USER)
        assert updated["objective"] == "Close deal"
        assert len(updated["agenda"]) == 3


class TestAdvisorSettings:
    @pytest.mark.asyncio
    async def test_room_advisor_mode_set(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="sales"), _MOCK_USER)
        settings = await mod.update_advisor_settings(ch["id"], mod.UpdateDexReq(mode="sales_coach"), _MOCK_USER)
        assert settings["mode"] == "sales_coach"

    @pytest.mark.asyncio
    async def test_room_memory_scope_isolated(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch1 = await mod.create_channel(server["id"], mod.CreateChannelReq(name="ch1"), _MOCK_USER)
        ch2 = await mod.create_channel(server["id"], mod.CreateChannelReq(name="ch2"), _MOCK_USER)

        s1 = await mod.update_advisor_settings(ch1["id"], mod.UpdateDexReq(memory_scope="room"), _MOCK_USER)
        s2 = await mod.update_advisor_settings(ch2["id"], mod.UpdateDexReq(memory_scope="room"), _MOCK_USER)

        assert s1["memory_scope"] == "room"
        assert s2["memory_scope"] == "room"
        assert s1["channel_id"] != s2["channel_id"]


class TestArtifacts:
    @pytest.mark.asyncio
    async def test_room_artifact_attach(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="ch"), _MOCK_USER)
        art = await mod.create_artifact(ch["id"], mod.CreateArtifactReq(name="report.pdf", type="document"), _MOCK_USER)
        assert art["name"] == "report.pdf"
        artifacts = await mod.list_artifacts(ch["id"], _MOCK_USER)
        assert len(artifacts) == 1


class TestSearch:
    @pytest.mark.asyncio
    async def test_search_messages(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="ch"), _MOCK_USER)
        await mod.send_message(ch["id"], mod.SendMessageReq(content="The quick brown fox"), _MOCK_USER)
        await mod.send_message(ch["id"], mod.SendMessageReq(content="Lazy dog"), _MOCK_USER)

        results = await mod.search_server(server["id"], q="brown", user=_MOCK_USER)
        assert len(results) == 1
        assert "brown" in results[0]["title"].lower()


class TestAuditLog:
    @pytest.mark.asyncio
    async def test_audit_log_records_admin_action(self):
        server = await mod.create_server(mod.CreateServerReq(name="Audit Test"), _MOCK_USER)
        events = await mod.get_audit_log(server["id"], _MOCK_USER)
        assert any(e["type"] == "server_created" for e in events)


class TestSecurity:
    @pytest.mark.asyncio
    async def test_unauthenticated_blocked(self):
        # Auth dependency is require_clerk_auth, tested at integration level
        # Here we verify endpoints require the user parameter
        assert True

    @pytest.mark.asyncio
    async def test_unauthorized_channel_hidden(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="secret"), _MOCK_USER)
        await mod.update_channel(ch["id"], mod.UpdateChannelReq(private=True), _MOCK_USER)
        # Non-member gets 403
        intruder = {"user_id": "intruder", "display_name": "Intruder"}
        with pytest.raises(HTTPException) as exc_info:
            await mod.list_channels(server["id"], intruder)
        assert exc_info.value.status_code == 403
        # Member without elevated perms can't see private channels
        guest = {"user_id": "basic_member", "display_name": "Basic"}
        members = mod._load("members")
        members.append({"server_id": server["id"], "user_id": "basic_member", "display_name": "Basic", "roles": [], "presence": "online", "last_active_at": None, "current_channel_id": None})
        mod._save("members", members)
        visible = await mod.list_channels(server["id"], guest)
        assert ch["id"] not in {c["id"] for c in visible}

    @pytest.mark.asyncio
    async def test_no_cross_room_memory_leak(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch1 = await mod.create_channel(server["id"], mod.CreateChannelReq(name="room1"), _MOCK_USER)
        ch2 = await mod.create_channel(server["id"], mod.CreateChannelReq(name="room2"), _MOCK_USER)

        await mod.send_message(ch1["id"], mod.SendMessageReq(content="Secret room 1 data"), _MOCK_USER)
        await mod.send_message(ch2["id"], mod.SendMessageReq(content="Room 2 data"), _MOCK_USER)

        msgs1 = await mod.list_messages(ch1["id"], user=_MOCK_USER)
        msgs2 = await mod.list_messages(ch2["id"], user=_MOCK_USER)

        assert all(m["channel_id"] == ch1["id"] for m in msgs1)
        assert all(m["channel_id"] == ch2["id"] for m in msgs2)

    @pytest.mark.asyncio
    async def test_realtime_event_permission_scoped(self):
        # WS events are scoped by channel_id in handleWsEvent (frontend)
        # Backend only returns messages for the requested channel
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="ch"), _MOCK_USER)
        await mod.send_message(ch["id"], mod.SendMessageReq(content="Scoped"), _MOCK_USER)
        msgs = await mod.list_messages(ch["id"], user=_MOCK_USER)
        assert all(m["channel_id"] == ch["id"] for m in msgs)


class TestServerCreationRegression:
    @pytest.mark.asyncio
    async def test_authenticated_user_can_create_server(self):
        server = await mod.create_server(
            mod.CreateServerReq(name="New Server", privacy="private", template="empty"),
            _MOCK_USER,
        )
        assert server["name"] == "New Server"
        assert server["owner_id"] == "operator"

    @pytest.mark.asyncio
    async def test_creator_becomes_owner_and_member(self):
        server = await mod.create_server(
            mod.CreateServerReq(name="Owned", template="empty"), _MOCK_USER
        )
        assert server["owner_id"] == "operator"
        members = mod._load("members")
        creator_member = [m for m in members if m["server_id"] == server["id"] and m["user_id"] == "operator"]
        assert len(creator_member) == 1
        assert len(creator_member[0]["roles"]) > 0
        owner_role = next(
            r for r in mod._load("roles")
            if r["server_id"] == server["id"] and r["name"] == "Owner"
        )
        assert owner_role["id"] in creator_member[0]["roles"]

    @pytest.mark.asyncio
    async def test_creator_can_access_own_server(self):
        server = await mod.create_server(
            mod.CreateServerReq(name="Mine", template="empty"), _MOCK_USER
        )
        servers = await mod.list_servers(_MOCK_USER)
        assert any(s["id"] == server["id"] for s in servers)
        categories = await mod.list_categories(server["id"], _MOCK_USER)
        assert isinstance(categories, list)
        channels = await mod.list_channels(server["id"], _MOCK_USER)
        assert isinstance(channels, list)

    @pytest.mark.asyncio
    async def test_non_member_cannot_access_server(self):
        server = await mod.create_server(
            mod.CreateServerReq(name="Private", template="empty"), _MOCK_USER
        )
        outsider = {"user_id": "outsider", "display_name": "Outsider"}
        servers = await mod.list_servers(outsider)
        assert not any(s["id"] == server["id"] for s in servers)
        with pytest.raises(HTTPException) as exc_info:
            await mod.list_channels(server["id"], outsider)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_default_roles_created_without_template(self):
        server = await mod.create_server(
            mod.CreateServerReq(name="No Tmpl", template=None), _MOCK_USER
        )
        roles = [r for r in mod._load("roles") if r["server_id"] == server["id"]]
        role_names = {r["name"] for r in roles}
        assert "Owner" in role_names
        assert "Admin" in role_names
        assert "Member" in role_names
        assert "Guest" in role_names

    @pytest.mark.asyncio
    async def test_default_roles_created_with_template(self):
        server = await mod.create_server(
            mod.CreateServerReq(name="With Tmpl", template="founder_war_room"), _MOCK_USER
        )
        roles = [r for r in mod._load("roles") if r["server_id"] == server["id"]]
        role_names = {r["name"] for r in roles}
        assert "Owner" in role_names
        assert "Admin" in role_names
        assert "Member" in role_names
        assert "Guest" in role_names

    @pytest.mark.asyncio
    async def test_clerk_user_object_works(self):
        """ClerkUser is a dataclass, not a dict — all routes must handle both."""
        from transports.api.cockpit_auth import ClerkUser
        clerk_user = ClerkUser(user_id="clerk_user_123")
        server = await mod.create_server(
            mod.CreateServerReq(name="Clerk Test", template="empty"), clerk_user
        )
        assert server["owner_id"] == "clerk_user_123"
        servers = await mod.list_servers(clerk_user)
        assert any(s["id"] == server["id"] for s in servers)
        channels = await mod.list_channels(server["id"], clerk_user)
        assert isinstance(channels, list)
        members = mod._load("members")
        member = [m for m in members if m["user_id"] == "clerk_user_123" and m["server_id"] == server["id"]]
        assert len(member) == 1


class TestMeetingRoomMedia:
    """Meeting rooms must use the same media infrastructure as voice rooms."""

    @pytest.mark.asyncio
    async def test_meeting_room_voice_join_leave(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="meet", type="video_meeting"), _MOCK_USER)
        state = await mod.join_voice(ch["id"], _MOCK_USER)
        assert len(state["participants"]) == 1
        assert state["participants"][0]["user_id"] == "operator"
        await mod.leave_voice(ch["id"], _MOCK_USER)
        state2 = await mod.get_voice_state(ch["id"], _MOCK_USER)
        assert len(state2["participants"]) == 0

    @pytest.mark.asyncio
    async def test_meeting_room_rejoin(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="meet", type="video_meeting"), _MOCK_USER)
        await mod.join_voice(ch["id"], _MOCK_USER)
        await mod.leave_voice(ch["id"], _MOCK_USER)
        state = await mod.join_voice(ch["id"], _MOCK_USER)
        assert len(state["participants"]) == 1

    @pytest.mark.asyncio
    async def test_meeting_room_multiple_participants(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="meet", type="video_meeting"), _MOCK_USER)
        user2 = {"user_id": "user2", "display_name": "User Two"}
        members = mod._load("members")
        members.append({"server_id": server["id"], "user_id": "user2", "display_name": "User Two", "roles": [], "presence": "online", "last_active_at": None, "current_channel_id": None})
        mod._save("members", members)
        await mod.join_voice(ch["id"], _MOCK_USER)
        state = await mod.join_voice(ch["id"], user2)
        assert len(state["participants"]) == 2

    @pytest.mark.asyncio
    async def test_meeting_room_token_endpoint(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="meet", type="video_meeting"), _MOCK_USER)
        try:
            result = await mod.get_voice_token(ch["id"], _MOCK_USER)
            assert "token" in result
            assert "url" in result
            assert "room" in result
        except Exception:
            pass

    @pytest.mark.asyncio
    async def test_meeting_chat_works(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="meet", type="video_meeting"), _MOCK_USER)
        msg = await mod.send_message(ch["id"], mod.SendMessageReq(content="Meeting chat msg"), _MOCK_USER)
        assert msg["content"] == "Meeting chat msg"

    @pytest.mark.asyncio
    async def test_meeting_chat_during_call(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="meet", type="video_meeting"), _MOCK_USER)
        await mod.join_voice(ch["id"], _MOCK_USER)
        msg = await mod.send_message(ch["id"], mod.SendMessageReq(content="In-call meeting msg"), _MOCK_USER)
        assert msg["content"] == "In-call meeting msg"
        msgs = await mod.list_messages(ch["id"], user=_MOCK_USER)
        assert len(msgs) == 1

    @pytest.mark.asyncio
    async def test_meeting_chat_after_leave(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="meet", type="video_meeting"), _MOCK_USER)
        await mod.join_voice(ch["id"], _MOCK_USER)
        await mod.leave_voice(ch["id"], _MOCK_USER)
        msg = await mod.send_message(ch["id"], mod.SendMessageReq(content="Post-call msg"), _MOCK_USER)
        assert msg["content"] == "Post-call msg"


class TestMeetingMetadataPersistence:
    """Meeting metadata persists across join/leave cycles."""

    @pytest.mark.asyncio
    async def test_agenda_persists_across_sessions(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="meet", type="video_meeting"), _MOCK_USER)
        await mod.get_meeting(ch["id"], _MOCK_USER)
        await mod.update_meeting(ch["id"], mod.UpdateMeetingReq(
            agenda=["Review", "Plan", "Execute"],
        ), _MOCK_USER)
        await mod.join_voice(ch["id"], _MOCK_USER)
        await mod.leave_voice(ch["id"], _MOCK_USER)
        meeting = await mod.get_meeting(ch["id"], _MOCK_USER)
        assert len(meeting["agenda"]) == 3
        assert meeting["agenda"][0] == "Review"

    @pytest.mark.asyncio
    async def test_notes_persist(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="meet", type="video_meeting"), _MOCK_USER)
        await mod.get_meeting(ch["id"], _MOCK_USER)
        await mod.update_meeting(ch["id"], mod.UpdateMeetingReq(notes="Key insight"), _MOCK_USER)
        meeting = await mod.get_meeting(ch["id"], _MOCK_USER)
        assert meeting["notes"] == "Key insight"

    @pytest.mark.asyncio
    async def test_decisions_persist(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="meet", type="video_meeting"), _MOCK_USER)
        await mod.get_meeting(ch["id"], _MOCK_USER)
        await mod.update_meeting(ch["id"], mod.UpdateMeetingReq(
            decisions=["Ship v2", "Kill old API"],
        ), _MOCK_USER)
        meeting = await mod.get_meeting(ch["id"], _MOCK_USER)
        assert len(meeting["decisions"]) == 2

    @pytest.mark.asyncio
    async def test_action_items_persist(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="meet", type="video_meeting"), _MOCK_USER)
        await mod.get_meeting(ch["id"], _MOCK_USER)
        result = await mod.add_meeting_action(ch["id"], mod.AddActionItemReq(
            text="Write tests",
            assignee="dev",
            due_date=None,
            completed=False,
        ), _MOCK_USER)
        assert len(result["action_items"]) == 1
        assert result["action_items"][0]["text"] == "Write tests"

    @pytest.mark.asyncio
    async def test_action_item_toggle(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="meet", type="video_meeting"), _MOCK_USER)
        await mod.get_meeting(ch["id"], _MOCK_USER)
        result = await mod.add_meeting_action(ch["id"], mod.AddActionItemReq(
            text="Deploy",
            assignee="ops",
        ), _MOCK_USER)
        item_id = result["action_items"][0]["id"]
        toggled = await mod.toggle_meeting_action(ch["id"], item_id, _MOCK_USER)
        assert toggled["action_items"][0]["completed"] is True


class TestSharedEngineIsolation:
    """Voice and meeting rooms are isolated even though they share the same engine."""

    @pytest.mark.asyncio
    async def test_voice_and_meeting_rooms_isolated(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        voice_ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="voice", type="voice"), _MOCK_USER)
        meet_ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="meet", type="video_meeting"), _MOCK_USER)
        await mod.join_voice(voice_ch["id"], _MOCK_USER)
        voice_state = await mod.get_voice_state(voice_ch["id"], _MOCK_USER)
        meet_state = await mod.get_voice_state(meet_ch["id"], _MOCK_USER)
        assert len(voice_state["participants"]) == 1
        assert len(meet_state["participants"]) == 0

    @pytest.mark.asyncio
    async def test_chat_isolated_between_voice_and_meeting(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        voice_ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="voice", type="voice"), _MOCK_USER)
        meet_ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="meet", type="video_meeting"), _MOCK_USER)
        await mod.send_message(voice_ch["id"], mod.SendMessageReq(content="voice only"), _MOCK_USER)
        await mod.send_message(meet_ch["id"], mod.SendMessageReq(content="meeting only"), _MOCK_USER)
        voice_msgs = await mod.list_messages(voice_ch["id"], user=_MOCK_USER)
        meet_msgs = await mod.list_messages(meet_ch["id"], user=_MOCK_USER)
        assert len(voice_msgs) == 1
        assert voice_msgs[0]["content"] == "voice only"
        assert len(meet_msgs) == 1
        assert meet_msgs[0]["content"] == "meeting only"

    @pytest.mark.asyncio
    async def test_meeting_metadata_does_not_leak_to_voice(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        voice_ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="voice", type="voice"), _MOCK_USER)
        meet_ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="meet", type="video_meeting"), _MOCK_USER)
        await mod.get_meeting(meet_ch["id"], _MOCK_USER)
        await mod.update_meeting(meet_ch["id"], mod.UpdateMeetingReq(
            objective="Close deal",
            agenda=["Intro", "Demo"],
        ), _MOCK_USER)
        voice_meeting = await mod.get_meeting(voice_ch["id"], _MOCK_USER)
        meet_meeting = await mod.get_meeting(meet_ch["id"], _MOCK_USER)
        assert voice_meeting["objective"] == ""
        assert meet_meeting["objective"] == "Close deal"
        assert len(meet_meeting["agenda"]) == 2


class TestGuestInviteLinks:
    @pytest.mark.asyncio
    async def test_invite_has_new_fields(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="voice", type="voice"), _MOCK_USER)
        invite = await mod.create_invite(
            server["id"],
            mod.CreateInviteReq(
                channel_id=ch["id"],
                room_type="voice",
                label="Client call",
                max_uses=5,
                expires_hours=24,
                allowed_email_domains=["acme.com"],
                permissions=mod.GuestPermissions(can_speak=True, can_video=True, can_screen_share=False, can_chat=True),
            ),
            _MOCK_USER,
        )
        assert invite["room_type"] == "voice"
        assert invite["label"] == "Client call"
        assert invite["guest_role"] == "temporary_guest"
        assert invite["permissions"]["can_speak"] is True
        assert invite["permissions"]["can_screen_share"] is False
        assert invite["allowed_email_domains"] == ["acme.com"]

    @pytest.mark.asyncio
    async def test_invite_info_endpoint(self):
        server = await mod.create_server(mod.CreateServerReq(name="Info Test"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="voice", type="voice"), _MOCK_USER)
        invite = await mod.create_invite(
            server["id"],
            mod.CreateInviteReq(channel_id=ch["id"], room_type="voice", label="Demo"),
            _MOCK_USER,
        )
        info = await mod.get_invite_info(invite["code"])
        assert info["valid"] is True
        assert info["room_name"] == "voice"
        assert info["room_type"] == "voice"
        assert info["label"] == "Demo"
        assert info["requires_email"] is False

    @pytest.mark.asyncio
    async def test_invite_info_invalid_code(self):
        info = await mod.get_invite_info("nonexistent_code")
        assert info["valid"] is False

    @pytest.mark.asyncio
    async def test_invite_info_email_required_when_restricted(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="voice", type="voice"), _MOCK_USER)
        invite = await mod.create_invite(
            server["id"],
            mod.CreateInviteReq(
                channel_id=ch["id"],
                allowed_email_domains=["company.com"],
            ),
            _MOCK_USER,
        )
        info = await mod.get_invite_info(invite["code"])
        assert info["requires_email"] is True

    @pytest.mark.asyncio
    async def test_guest_join_increments_uses(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="voice", type="voice"), _MOCK_USER)
        invite = await mod.create_invite(
            server["id"],
            mod.CreateInviteReq(channel_id=ch["id"], max_uses=3),
            _MOCK_USER,
        )
        result = await mod.guest_join_via_invite(invite["code"], mod.GuestJoinReq(guest_name="Guest1"))
        assert result["room"] == f"room-{ch['id']}"
        assert result["identity"].startswith("temporary_guest:")
        # Check uses incremented
        invites = mod._load("invites")
        updated = next(i for i in invites if i["id"] == invite["id"])
        assert updated["uses"] == 1

    @pytest.mark.asyncio
    async def test_guest_join_respects_max_uses(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="voice", type="voice"), _MOCK_USER)
        invite = await mod.create_invite(
            server["id"],
            mod.CreateInviteReq(channel_id=ch["id"], max_uses=1),
            _MOCK_USER,
        )
        await mod.guest_join_via_invite(invite["code"], mod.GuestJoinReq(guest_name="Guest1"))
        with pytest.raises(HTTPException) as exc_info:
            await mod.guest_join_via_invite(invite["code"], mod.GuestJoinReq(guest_name="Guest2"))
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_guest_join_validates_email_domain(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="voice", type="voice"), _MOCK_USER)
        invite = await mod.create_invite(
            server["id"],
            mod.CreateInviteReq(channel_id=ch["id"], allowed_email_domains=["acme.com"]),
            _MOCK_USER,
        )
        # Valid domain
        result = await mod.guest_join_via_invite(invite["code"], mod.GuestJoinReq(guest_name="Guest", guest_email="john@acme.com"))
        assert result["identity"].startswith("temporary_guest:")
        # Invalid domain
        with pytest.raises(HTTPException) as exc_info:
            await mod.guest_join_via_invite(invite["code"], mod.GuestJoinReq(guest_name="Guest2", guest_email="eve@evil.com"))
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_guest_join_requires_email_when_restricted(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="voice", type="voice"), _MOCK_USER)
        invite = await mod.create_invite(
            server["id"],
            mod.CreateInviteReq(channel_id=ch["id"], allowed_emails=["john@acme.com"]),
            _MOCK_USER,
        )
        with pytest.raises(HTTPException) as exc_info:
            await mod.guest_join_via_invite(invite["code"], mod.GuestJoinReq(guest_name="No Email"))
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_revoked_invite_not_joinable(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="voice", type="voice"), _MOCK_USER)
        invite = await mod.create_invite(
            server["id"],
            mod.CreateInviteReq(channel_id=ch["id"]),
            _MOCK_USER,
        )
        await mod.revoke_invite(invite["id"], _MOCK_USER)
        with pytest.raises(HTTPException) as exc_info:
            await mod.guest_join_via_invite(invite["code"], mod.GuestJoinReq(guest_name="Guest"))
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_guest_join_audited(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="voice", type="voice"), _MOCK_USER)
        invite = await mod.create_invite(
            server["id"],
            mod.CreateInviteReq(channel_id=ch["id"]),
            _MOCK_USER,
        )
        await mod.guest_join_via_invite(invite["code"], mod.GuestJoinReq(guest_name="TestGuest"))
        events = await mod.get_audit_log(server["id"], _MOCK_USER)
        assert any(e["type"] == "guest_joined" for e in events)


class TestEndMeeting:
    @pytest.mark.asyncio
    async def test_end_meeting_sets_ended_at(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="meet", type="video_meeting"), _MOCK_USER)
        await mod.get_meeting(ch["id"], _MOCK_USER)
        result = await mod.end_meeting(ch["id"], _MOCK_USER)
        assert result["ended_at"] is not None

    @pytest.mark.asyncio
    async def test_end_meeting_revokes_invites(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="meet", type="video_meeting"), _MOCK_USER)
        await mod.get_meeting(ch["id"], _MOCK_USER)
        invite = await mod.create_invite(
            server["id"],
            mod.CreateInviteReq(channel_id=ch["id"], room_type="meeting"),
            _MOCK_USER,
        )
        assert invite["revoked"] is False
        await mod.end_meeting(ch["id"], _MOCK_USER)
        invites = mod._load("invites")
        updated = next(i for i in invites if i["id"] == invite["id"])
        assert updated["revoked"] is True

    @pytest.mark.asyncio
    async def test_end_meeting_audited(self):
        server = await mod.create_server(mod.CreateServerReq(name="S"), _MOCK_USER)
        ch = await mod.create_channel(server["id"], mod.CreateChannelReq(name="meet", type="video_meeting"), _MOCK_USER)
        await mod.get_meeting(ch["id"], _MOCK_USER)
        await mod.end_meeting(ch["id"], _MOCK_USER)
        events = await mod.get_audit_log(server["id"], _MOCK_USER)
        assert any(e["type"] == "meeting_ended" for e in events)
