"""Tests for substrate.state.stores.entity_store — entity persistence layer."""

import os
import sys
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, "/opt/OS/.claude/worktrees/close-all-gaps-v2")

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("EOS_ORG_ID", "test-org-id")
os.environ.setdefault("EOS_USER_ID", "test-user-id")

import pytest

from substrate.state.stores.entity_store import EntityStore, _ensure_tables


@pytest.fixture(autouse=True)
def reset_tables_flag():
    import substrate.state.stores.entity_store as mod

    mod._TABLES_CREATED = False
    yield
    mod._TABLES_CREATED = False


@pytest.fixture
def mock_conn():
    mock_cur = MagicMock()
    mock_cur.fetchone.return_value = None
    mock_cur.fetchall.return_value = []
    mock_ctx = MagicMock()
    mock_ctx.__enter__ = MagicMock(return_value=mock_cur)
    mock_ctx.__exit__ = MagicMock(return_value=False)
    with patch("substrate.state.stores.entity_store.get_conn", return_value=mock_ctx) as mock_gc:
        yield mock_gc, mock_cur


class TestEnsureTables:
    def test_creates_7_tables(self, mock_conn):
        mock_gc, mock_cur = mock_conn
        _ensure_tables("org-1")

        create_calls = [c for c in mock_cur.execute.call_args_list if "CREATE TABLE" in str(c)]
        assert len(create_calls) == 7

    def test_creates_all_expected_tables(self, mock_conn):
        mock_gc, mock_cur = mock_conn
        _ensure_tables("org-1")

        sql_text = " ".join(str(c) for c in mock_cur.execute.call_args_list)
        for table in [
            "umh_users",
            "umh_portfolios",
            "umh_companies",
            "umh_departments",
            "umh_roles",
            "umh_workflows",
            "umh_dashboards",
        ]:
            assert table in sql_text, f"Missing table: {table}"

    def test_idempotent_after_first_call(self, mock_conn):
        mock_gc, mock_cur = mock_conn
        _ensure_tables("org-1")
        call_count_1 = mock_cur.execute.call_count

        _ensure_tables("org-1")
        call_count_2 = mock_cur.execute.call_count

        assert call_count_2 == call_count_1

    def test_handles_db_error_gracefully(self, mock_conn):
        mock_gc, mock_cur = mock_conn
        mock_cur.execute.side_effect = Exception("connection refused")

        _ensure_tables("org-1")

        import substrate.state.stores.entity_store as mod

        assert not mod._TABLES_CREATED


class TestEntityStoreInit:
    def test_stores_org_id(self, mock_conn):
        store = EntityStore("org-123")
        assert store._org_id == "org-123"

    def test_calls_ensure_tables(self, mock_conn):
        mock_gc, mock_cur = mock_conn
        EntityStore("org-1")
        assert mock_cur.execute.call_count == 7


class TestSaveUser:
    def test_upserts_user(self, mock_conn):
        mock_gc, mock_cur = mock_conn
        store = EntityStore("org-1")
        mock_cur.execute.reset_mock()

        store.save_user("u-1", "a@b.com", "Alice")

        insert_call = mock_cur.execute.call_args
        sql = insert_call[0][0]
        assert "INSERT INTO umh_users" in sql
        assert "ON CONFLICT (id) DO UPDATE" in sql
        params = insert_call[0][1]
        assert params[0] == "u-1"
        assert "a@b.com" in params

    def test_default_role_scope_is_founder(self, mock_conn):
        mock_gc, mock_cur = mock_conn
        store = EntityStore("org-1")
        mock_cur.execute.reset_mock()

        store.save_user("u-1", "a@b.com")

        params = mock_cur.execute.call_args[0][1]
        assert "founder" in params


class TestGetUser:
    def test_returns_dict_when_found(self, mock_conn):
        mock_gc, mock_cur = mock_conn
        mock_cur.fetchone.return_value = {"id": "u-1", "email": "a@b.com"}

        store = EntityStore("org-1")
        result = store.get_user("u-1")

        assert result == {"id": "u-1", "email": "a@b.com"}

    def test_returns_none_when_not_found(self, mock_conn):
        mock_gc, mock_cur = mock_conn
        mock_cur.fetchone.return_value = None

        store = EntityStore("org-1")
        result = store.get_user("nonexistent")

        assert result is None

    def test_returns_none_on_error(self, mock_conn):
        mock_gc, mock_cur = mock_conn
        store = EntityStore("org-1")
        mock_cur.execute.side_effect = Exception("timeout")

        result = store.get_user("u-1")
        assert result is None


class TestListUsers:
    def test_returns_list_of_dicts(self, mock_conn):
        mock_gc, mock_cur = mock_conn
        mock_cur.fetchall.return_value = [
            {"id": "u-1", "email": "a@b.com"},
            {"id": "u-2", "email": "c@d.com"},
        ]

        store = EntityStore("org-1")
        result = store.list_users()

        assert len(result) == 2
        assert result[0]["email"] == "a@b.com"

    def test_returns_empty_on_error(self, mock_conn):
        mock_gc, mock_cur = mock_conn
        store = EntityStore("org-1")
        mock_cur.execute.side_effect = Exception("db down")

        result = store.list_users()
        assert result == []


class TestSaveCompany:
    def test_upserts_company(self, mock_conn):
        mock_gc, mock_cur = mock_conn
        store = EntityStore("org-1")
        mock_cur.execute.reset_mock()

        store.save_company("c-1", "Acme", stage=3, stage_name="growth")

        sql = mock_cur.execute.call_args[0][0]
        assert "INSERT INTO umh_companies" in sql
        params = mock_cur.execute.call_args[0][1]
        assert params[0] == "c-1"
        assert "Acme" in params

    def test_default_org_id_from_store(self, mock_conn):
        mock_gc, mock_cur = mock_conn
        store = EntityStore("org-99")
        mock_cur.execute.reset_mock()

        store.save_company("c-1", "Acme")

        params = mock_cur.execute.call_args[0][1]
        assert "org-99" in params


class TestListCompanies:
    def test_filters_by_org_id(self, mock_conn):
        mock_gc, mock_cur = mock_conn
        store = EntityStore("org-1")
        mock_cur.execute.reset_mock()

        store.list_companies()

        sql = mock_cur.execute.call_args[0][0]
        assert "org_id = %s" in sql
        params = mock_cur.execute.call_args[0][1]
        assert params == ("org-1",)


class TestSaveDepartment:
    def test_upserts_department(self, mock_conn):
        mock_gc, mock_cur = mock_conn
        store = EntityStore("org-1")
        mock_cur.execute.reset_mock()

        store.save_department("d-1", "Sales", "sales", agent_name="eos-sales")

        sql = mock_cur.execute.call_args[0][0]
        assert "INSERT INTO umh_departments" in sql
        params = mock_cur.execute.call_args[0][1]
        assert params[0] == "d-1"
        assert "Sales" in params


class TestSaveRole:
    def test_upserts_role(self, mock_conn):
        mock_gc, mock_cur = mock_conn
        store = EntityStore("org-1")
        mock_cur.execute.reset_mock()

        store.save_role("r-1", "Sales Rep", "sales", operator="ai")

        sql = mock_cur.execute.call_args[0][0]
        assert "INSERT INTO umh_roles" in sql

    def test_list_roles_filters_by_department(self, mock_conn):
        mock_gc, mock_cur = mock_conn
        store = EntityStore("org-1")
        mock_cur.execute.reset_mock()

        store.list_roles(department="sales")

        sql = mock_cur.execute.call_args[0][0]
        assert "department = %s" in sql

    def test_list_roles_all_departments(self, mock_conn):
        mock_gc, mock_cur = mock_conn
        store = EntityStore("org-1")
        mock_cur.execute.reset_mock()

        store.list_roles()

        sql = mock_cur.execute.call_args[0][0]
        assert "department" not in sql


class TestSaveWorkflow:
    def test_upserts_workflow(self, mock_conn):
        mock_gc, mock_cur = mock_conn
        store = EntityStore("org-1")
        mock_cur.execute.reset_mock()

        store.save_workflow("w-1", "Morning Brief", "morning_brief", trigger_type="scheduled")

        sql = mock_cur.execute.call_args[0][0]
        assert "INSERT INTO umh_workflows" in sql

    def test_list_workflows_by_department(self, mock_conn):
        mock_gc, mock_cur = mock_conn
        store = EntityStore("org-1")
        mock_cur.execute.reset_mock()

        store.list_workflows(department="sales")

        sql = mock_cur.execute.call_args[0][0]
        assert "department = %s" in sql


class TestSaveDashboard:
    def test_upserts_dashboard(self, mock_conn):
        mock_gc, mock_cur = mock_conn
        store = EntityStore("org-1")
        mock_cur.execute.reset_mock()

        store.save_dashboard("db-1", role_id="r-1", department="sales")

        sql = mock_cur.execute.call_args[0][0]
        assert "INSERT INTO umh_dashboards" in sql

    def test_list_dashboards_filters_by_org(self, mock_conn):
        mock_gc, mock_cur = mock_conn
        store = EntityStore("org-1")
        mock_cur.execute.reset_mock()

        store.list_dashboards()

        params = mock_cur.execute.call_args[0][1]
        assert params == ("org-1",)


class TestSavePortfolio:
    def test_upserts_portfolio(self, mock_conn):
        mock_gc, mock_cur = mock_conn
        store = EntityStore("org-1")
        mock_cur.execute.reset_mock()

        store.save_portfolio("p-1", "u-1", companies=["c-1", "c-2"])

        sql = mock_cur.execute.call_args[0][0]
        assert "INSERT INTO umh_portfolios" in sql

    def test_get_portfolio_returns_dict(self, mock_conn):
        mock_gc, mock_cur = mock_conn
        mock_cur.fetchone.return_value = {"id": "p-1", "user_id": "u-1"}

        store = EntityStore("org-1")
        result = store.get_portfolio("p-1")

        assert result == {"id": "p-1", "user_id": "u-1"}
