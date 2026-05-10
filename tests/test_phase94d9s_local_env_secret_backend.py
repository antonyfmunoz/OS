"""Tests for Phase 94D.9S — Local .env Secret Backend."""

from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"

from eos_ai.substrate.local_env_secret_backend import (
    DEFAULT_SECRET_PATH,
    build_secret_ref_from_key,
    get_secret_value_for_local_action,
    has_secret,
    list_available_secret_refs,
    load_env_file_keys_only,
    reject_repo_env_files,
    validate_env_path_is_outside_repo,
)
from eos_ai.substrate.secret_broker_contracts import (
    SecretBackendType,
    SecretScope,
    SecretUseStatus,
)


class TestValidateEnvPath:
    def test_repo_path_rejected(self) -> None:
        errors = validate_env_path_is_outside_repo(f"{_ROOT}/.env")
        assert len(errors) > 0
        assert "inside repository" in errors[0].lower()

    def test_repo_subdir_rejected(self) -> None:
        errors = validate_env_path_is_outside_repo(f"{_ROOT}/eos_ai/.env")
        assert len(errors) > 0

    def test_home_umh_path_allowed(self) -> None:
        errors = validate_env_path_is_outside_repo("/root/.umh/secrets/.env")
        assert errors == []

    def test_tmp_path_allowed(self) -> None:
        errors = validate_env_path_is_outside_repo("/tmp/test_secrets/.env")
        assert errors == []

    def test_reject_repo_env_files(self) -> None:
        assert reject_repo_env_files(f"{_ROOT}/.env") is True
        assert reject_repo_env_files("/root/.umh/secrets/.env") is False


class TestLoadKeysOnly:
    def test_returns_keys_not_values(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", dir="/tmp", delete=False) as f:
            f.write("GOOGLE_PASSWORD=supersecret123\n")
            f.write("WHOP_EMAIL=test@test.com\n")
            f.write("# comment line\n")
            f.write("API_KEY=sk_live_abc\n")
            path = f.name

        try:
            keys = load_env_file_keys_only(path)
            assert "GOOGLE_PASSWORD" in keys
            assert "WHOP_EMAIL" in keys
            assert "API_KEY" in keys
            assert "supersecret123" not in keys
            assert "sk_live_abc" not in keys
        finally:
            os.unlink(path)

    def test_missing_file_returns_empty(self) -> None:
        keys = load_env_file_keys_only("/tmp/nonexistent_xyz_test.env")
        assert keys == []

    def test_repo_path_returns_empty(self) -> None:
        keys = load_env_file_keys_only(f"{_ROOT}/.env")
        assert keys == []


class TestHasSecret:
    def test_detects_existing_key(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", dir="/tmp", delete=False) as f:
            f.write("GOOGLE_PASSWORD=test\n")
            f.write("WHOP_EMAIL=test@test.com\n")
            path = f.name

        try:
            assert has_secret(path, "GOOGLE_PASSWORD") is True
            assert has_secret(path, "WHOP_EMAIL") is True
            assert has_secret(path, "NONEXISTENT_KEY") is False
        finally:
            os.unlink(path)

    def test_missing_file_returns_false(self) -> None:
        assert has_secret("/tmp/nonexistent_xyz.env", "ANY_KEY") is False


class TestGetSecretValue:
    def test_returns_available_for_existing_key(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", dir="/tmp", delete=False) as f:
            f.write("TEST_SECRET=the_value\n")
            path = f.name

        try:
            status, value = get_secret_value_for_local_action(path, "TEST_SECRET")
            assert status == SecretUseStatus.AVAILABLE
            assert value == "the_value"
        finally:
            os.unlink(path)

    def test_returns_unavailable_for_missing_key(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", dir="/tmp", delete=False) as f:
            f.write("OTHER_KEY=value\n")
            path = f.name

        try:
            status, value = get_secret_value_for_local_action(path, "MISSING")
            assert status == SecretUseStatus.UNAVAILABLE
            assert value == ""
        finally:
            os.unlink(path)

    def test_returns_unavailable_for_missing_file(self) -> None:
        status, value = get_secret_value_for_local_action("/tmp/no_such_file.env", "KEY")
        assert status == SecretUseStatus.UNAVAILABLE
        assert value == ""

    def test_repo_path_returns_unavailable(self) -> None:
        status, value = get_secret_value_for_local_action(f"{_ROOT}/.env", "KEY")
        assert status == SecretUseStatus.UNAVAILABLE
        assert value == ""


class TestBuildSecretRef:
    def test_secret_value_not_in_repr(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", dir="/tmp", delete=False) as f:
            f.write("GOOGLE_PASSWORD=supersecretpassword\n")
            path = f.name

        try:
            ref = build_secret_ref_from_key("GOOGLE_PASSWORD", path=path)
            r = repr(ref)
            assert "supersecretpassword" not in r
            assert ref.available is True
            assert ref.scope == SecretScope.GOOGLE_WORKSPACE
        finally:
            os.unlink(path)

    def test_infers_google_scope(self) -> None:
        ref = build_secret_ref_from_key("GOOGLE_ANTONYFM_PASSWORD", path="/tmp/no.env")
        assert ref.scope == SecretScope.GOOGLE_WORKSPACE

    def test_infers_whop_scope(self) -> None:
        ref = build_secret_ref_from_key("WHOP_API_KEY", path="/tmp/no.env")
        assert ref.scope == SecretScope.WHOP

    def test_infers_generic_scope(self) -> None:
        ref = build_secret_ref_from_key("RANDOM_THING", path="/tmp/no.env")
        assert ref.scope == SecretScope.GENERIC

    def test_unavailable_when_file_missing(self) -> None:
        ref = build_secret_ref_from_key("ANY_KEY", path="/tmp/no_such.env")
        assert ref.available is False


class TestListAvailableRefs:
    def test_returns_refs_without_values(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", dir="/tmp", delete=False) as f:
            f.write("GOOGLE_PASSWORD=secret1\n")
            f.write("STRIPE_API_KEY=sk_live_abc\n")
            path = f.name

        try:
            refs = list_available_secret_refs(path)
            assert len(refs) == 2
            for ref in refs:
                r = repr(ref)
                assert "secret1" not in r
                assert "sk_live_abc" not in r
                assert ref.backend == SecretBackendType.LOCAL_ENV
        finally:
            os.unlink(path)
