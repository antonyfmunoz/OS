"""Structural tests for all 14 Tier 3 domain store classes."""

import inspect
import os
import sys

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))
from dotenv import load_dotenv
load_dotenv(os.path.join("/opt/OS", "runtime", ".env"))
load_dotenv(os.path.join("/opt/OS", "services", ".env"))


# ── EntityLinkStore ──────────────────────────────────────────────────────────

def test_entity_link_store_import():
    from substrate.state.stores.entity_link_store import EntityLinkStore
    assert hasattr(EntityLinkStore, "insert_link")

def test_entity_link_store_signature():
    from substrate.state.stores.entity_link_store import EntityLinkStore
    params = list(inspect.signature(EntityLinkStore.insert_link).parameters)
    assert "org_id" in params and "relationship" in params


# ── ContextCompactionStore ───────────────────────────────────────────────────

def test_context_compaction_store_import():
    from substrate.state.stores.context_compaction_store import ContextCompactionStore
    assert hasattr(ContextCompactionStore, "insert_compaction")

def test_context_compaction_store_signature():
    from substrate.state.stores.context_compaction_store import ContextCompactionStore
    params = list(inspect.signature(ContextCompactionStore.insert_compaction).parameters)
    assert "session_id" in params and "generation" in params


# ── AgentRegistryStore ───────────────────────────────────────────────────────

def test_agent_registry_store_import():
    from substrate.state.stores.agent_registry_store import AgentRegistryStore
    assert hasattr(AgentRegistryStore, "register_agent")

def test_agent_registry_store_signature():
    from substrate.state.stores.agent_registry_store import AgentRegistryStore
    params = list(inspect.signature(AgentRegistryStore.register_agent).parameters)
    assert "org_id" in params and "name" in params


# ── EmbeddingStore ───────────────────────────────────────────────────────────

def test_embedding_store_import():
    from substrate.state.stores.embedding_store import EmbeddingStore
    assert hasattr(EmbeddingStore, "upsert_embedding")

def test_embedding_store_return_type():
    from substrate.state.stores.embedding_store import EmbeddingStore
    hints = EmbeddingStore.upsert_embedding.__annotations__
    assert hints.get("return") is bool


# ── HiggsFieldStore ──────────────────────────────────────────────────────────

def test_higgsfield_store_import():
    from substrate.state.stores.higgsfield_store import HiggsFieldStore
    assert hasattr(HiggsFieldStore, "insert_job")
    assert hasattr(HiggsFieldStore, "update_status")

def test_higgsfield_store_insert_signature():
    from substrate.state.stores.higgsfield_store import HiggsFieldStore
    params = list(inspect.signature(HiggsFieldStore.insert_job).parameters)
    assert "request_id" in params and "model_id" in params


# ── EmailFolderStore ─────────────────────────────────────────────────────────

def test_email_folder_store_import():
    from substrate.state.stores.email_folder_store import EmailFolderStore
    assert hasattr(EmailFolderStore, "seed_folders")
    assert hasattr(EmailFolderStore, "update_purpose")


# ── VentureStore ─────────────────────────────────────────────────────────────

def test_venture_store_import():
    from substrate.state.stores.venture_store import VentureStore
    assert hasattr(VentureStore, "save_venture")

def test_venture_store_signature():
    from substrate.state.stores.venture_store import VentureStore
    params = list(inspect.signature(VentureStore.save_venture).parameters)
    assert "org_id" in params and "venture_id_slug" in params


# ── ApprovalStore ────────────────────────────────────────────────────────────

def test_approval_store_import():
    from substrate.state.stores.approval_store import ApprovalStore
    assert hasattr(ApprovalStore, "create_approval")
    assert hasattr(ApprovalStore, "approve")
    assert hasattr(ApprovalStore, "reject")

def test_approval_store_create_return():
    from substrate.state.stores.approval_store import ApprovalStore
    hints = ApprovalStore.create_approval.__annotations__
    assert hints.get("return") is str


# ── SkillStore ───────────────────────────────────────────────────────────────

def test_skill_store_import():
    from substrate.state.stores.skill_store import SkillStore
    assert hasattr(SkillStore, "get_by_name")
    assert hasattr(SkillStore, "upsert_skill")
    assert hasattr(SkillStore, "update_skill_content")
    assert hasattr(SkillStore, "update_skill_content_by_name")

def test_skill_store_get_by_name_signature():
    from substrate.state.stores.skill_store import SkillStore
    params = list(inspect.signature(SkillStore.get_by_name).parameters)
    assert "org_id" in params and "name" in params


# ── PreferenceStore ──────────────────────────────────────────────────────────

def test_preference_store_import():
    from substrate.state.stores.preference_store import PreferenceStore
    assert hasattr(PreferenceStore, "ensure_defaults")
    assert hasattr(PreferenceStore, "set_field")

def test_preference_store_field_validation():
    from substrate.state.stores.preference_store import PreferenceStore
    import pytest
    store = PreferenceStore()
    with pytest.raises(ValueError):
        store.set_field("org", "invalid_field", "val")


# ── TaskStore ────────────────────────────────────────────────────────────────

def test_task_store_import():
    from substrate.state.stores.task_store import TaskStore
    assert hasattr(TaskStore, "create_task")
    assert hasattr(TaskStore, "update_status")
    assert hasattr(TaskStore, "set_notion_page_id")


# ── PermissionStore ──────────────────────────────────────────────────────────

def test_permission_store_import():
    from substrate.state.stores.permission_store import PermissionStore
    assert hasattr(PermissionStore, "grant_permission")
    assert hasattr(PermissionStore, "revoke_permission")
    assert hasattr(PermissionStore, "register_product")


# ── ProfileStore ─────────────────────────────────────────────────────────────

def test_profile_store_import():
    from substrate.state.stores.profile_store import ProfileStore
    assert hasattr(ProfileStore, "upsert_human_profile")
    assert hasattr(ProfileStore, "upsert_user_profile")
    assert hasattr(ProfileStore, "upsert_intelligence_profile")


# ── GoalStore ────────────────────────────────────────────────────────────────

def test_goal_store_import():
    from substrate.state.stores.goal_store import GoalStore
    assert hasattr(GoalStore, "upsert_goal")
    assert hasattr(GoalStore, "batch_update_rankings")
    assert hasattr(GoalStore, "update_performance")
    assert hasattr(GoalStore, "insert_outcome")

def test_goal_store_upsert_signature():
    from substrate.state.stores.goal_store import GoalStore
    params = list(inspect.signature(GoalStore.upsert_goal).parameters)
    assert len(params) == 19  # self + 18 columns
