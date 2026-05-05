"""Tests for Wave 4: infrastructure extraction + compatibility wrappers."""

import sys

sys.path.insert(0, "/opt/OS")


# ─── system_context extraction ────────────────────────────────────────────────


class TestSystemContext:
    def test_dataclass_fields(self):
        from umh.environments.system_context import SystemContext

        ctx = SystemContext(org_id="test", user_id="user1")
        assert ctx.org_id == "test"
        assert ctx.user_id == "user1"
        assert ctx.portfolio_id is None
        assert ctx.active_venture_id is None
        assert ctx.active_agent_id is None
        assert ctx.ventures == []

    def test_backward_compat_alias(self):
        from umh.environments.system_context import EOSContext, SystemContext

        assert EOSContext is SystemContext

    def test_load_ventures_from_env_empty(self, monkeypatch):
        monkeypatch.delenv("VENTURES_JSON", raising=False)
        from umh.environments.system_context import load_ventures_from_env

        assert load_ventures_from_env() == []

    def test_load_ventures_from_env_json(self, monkeypatch):
        import json

        monkeypatch.setenv("VENTURES_JSON", json.dumps([{"id": "v1"}]))
        from umh.environments.system_context import load_ventures_from_env

        result = load_ventures_from_env()
        assert len(result) == 1
        assert result[0]["id"] == "v1"

    def test_load_ventures_from_env_invalid_json(self, monkeypatch):
        monkeypatch.setenv("VENTURES_JSON", "not json")
        from umh.environments.system_context import load_ventures_from_env

        assert load_ventures_from_env() == []

    def test_load_context_from_env(self, monkeypatch):
        monkeypatch.setenv("EOS_ORG_ID", "org123")
        monkeypatch.setenv("EOS_USER_ID", "user456")
        monkeypatch.delenv("EOS_PORTFOLIO_ID", raising=False)
        monkeypatch.delenv("VENTURES_JSON", raising=False)
        from umh.environments.system_context import load_context_from_env

        ctx = load_context_from_env()
        assert ctx.org_id == "org123"
        assert ctx.user_id == "user456"

    def test_context_uses_env_vars(self, monkeypatch):
        monkeypatch.setenv("EOS_ORG_ID", "custom_org")
        monkeypatch.setenv("EOS_USER_ID", "custom_user")
        monkeypatch.setenv("EOS_PORTFOLIO_ID", "custom_port")
        from umh.environments.system_context import SystemContext

        ctx = SystemContext(
            org_id="custom_org",
            user_id="custom_user",
            portfolio_id="custom_port",
        )
        assert ctx.org_id == "custom_org"
        assert ctx.user_id == "custom_user"
        assert ctx.portfolio_id == "custom_port"


# ─── neon extraction ─────────────────────────────────────────────────────────


class TestNeonAdapter:
    def test_imports(self):
        from umh.storage.adapters.neon import (
            get_conn,
            resolve_skill,
            resolve_venture,
        )

        assert callable(get_conn)
        assert callable(resolve_venture)
        assert callable(resolve_skill)

    def test_resolve_venture_none(self):
        from umh.storage.adapters.neon import resolve_venture

        assert resolve_venture(None) is None
        assert resolve_venture("") is None

    def test_resolve_skill_none(self):
        from umh.storage.adapters.neon import resolve_skill

        assert resolve_skill(None) is None
        assert resolve_skill("") is None

    def test_get_database_url_missing(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        from umh.storage.adapters import neon

        neon._dotenv_loaded = True
        try:
            neon._get_database_url()
            assert False, "Should have raised"
        except RuntimeError as e:
            assert "DATABASE_URL" in str(e)
        finally:
            neon._dotenv_loaded = False

    def test_lazy_init_constants(self, monkeypatch):
        monkeypatch.setenv("EOS_ORG_ID", "test_org")
        monkeypatch.setenv("EOS_USER_ID", "test_user")
        from umh.storage.adapters import neon

        neon._dotenv_loaded = True
        neon._init_module_constants()
        assert neon.ORG_ID == "test_org"
        assert neon.USER_ID == "test_user"
        neon._dotenv_loaded = False


# ─── business_instance extraction ─────────────────────────────────────────────


class TestBusinessInstance:
    def test_dataclass_defaults(self):
        from umh.workstation.business import BusinessInstance

        bis = BusinessInstance(
            org_id="o1",
            venture_id="v1",
            name="Test",
            industry="tech",
            business_model="saas",
        )
        assert bis.current_stage == 1
        assert bis.stage_name == "Validation"
        assert bis.ai_name == "DEX"
        assert bis.monthly_revenue == 0.0

    def test_stage_names_complete(self):
        from umh.workstation.business import STAGE_NAMES

        assert len(STAGE_NAMES) == 6
        assert STAGE_NAMES[1] == "Validation"
        assert STAGE_NAMES[6] == "Portfolio"

    def test_stage_guidance_complete(self):
        from umh.workstation.business import STAGE_GUIDANCE

        assert len(STAGE_GUIDANCE) == 6
        for stage in range(1, 7):
            g = STAGE_GUIDANCE[stage]
            assert "focus" in g
            assert "next_actions" in g
            assert "what_not_to_do" in g

    def test_stage_proof_gates_complete(self):
        from umh.workstation.business import STAGE_PROOF_GATES

        assert len(STAGE_PROOF_GATES) == 6

    def test_get_ai_name_default(self):
        from umh.workstation.business import get_ai_name

        class FakeCtx:
            org_id = "fake"

        assert get_ai_name(FakeCtx()) == "DEX"


# ─── compatibility wrappers ──────────────────────────────────────────────────


class TestCompatibilityWrappers:
    def test_context_wrapper_re_exports(self):
        from umh.environments.system_context import EOSContext, load_context_from_env
        from umh.environments.system_context import (
            SystemContext,
            load_context_from_env as umh_load,
        )

        assert EOSContext is SystemContext
        assert load_context_from_env is umh_load

    def test_db_wrapper_functions(self):
        from umh.storage.adapters.neon import get_conn, resolve_skill, resolve_venture
        from umh.storage.adapters.neon import (
            get_conn as umh_get_conn,
            resolve_skill as umh_resolve_skill,
            resolve_venture as umh_resolve_venture,
        )

        assert get_conn is umh_get_conn
        assert resolve_venture is umh_resolve_venture
        assert resolve_skill is umh_resolve_skill

    def test_business_instance_wrapper(self):
        from umh.workstation.business import (
            BusinessInstance,
            BusinessInstanceManager,
            get_ai_name,
        )
        from umh.workstation.business import (
            BusinessInstance as UmhBI,
            BusinessInstanceManager as UmhBIM,
            get_ai_name as umh_get_ai_name,
        )

        assert BusinessInstance is UmhBI
        assert BusinessInstanceManager is UmhBIM
        assert get_ai_name is umh_get_ai_name


# ─── interface packages ──────────────────────────────────────────────────────


class TestInterfacePackages:
    def test_discord_interface_importable(self):
        import umh.interfaces.discord

        assert umh.interfaces.discord is not None

    def test_telegram_interface_importable(self):
        import umh.interfaces.telegram

        assert umh.interfaces.telegram is not None

    def test_cli_interface_importable(self):
        import umh.interfaces.cli

        assert hasattr(umh.interfaces.cli, "main")
