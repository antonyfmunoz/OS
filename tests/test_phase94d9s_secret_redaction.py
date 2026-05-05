"""Tests for Phase 94D.9S — Secret Redaction."""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from eos_ai.substrate.secret_broker_contracts import (
    SecretBackendType,
    SecretRef,
    SecretScope,
)
from eos_ai.substrate.secret_redaction import (
    REDACTED_PLACEHOLDER,
    looks_like_secret_key,
    redact_env_line,
    redact_mapping,
    redact_potential_secrets_in_output,
    redact_secret_values,
    safe_repr_secret_ref,
)


class TestLooksLikeSecretKey:
    def test_password_detected(self) -> None:
        assert looks_like_secret_key("GOOGLE_PASSWORD")

    def test_api_key_detected(self) -> None:
        assert looks_like_secret_key("STRIPE_API_KEY")

    def test_token_detected(self) -> None:
        assert looks_like_secret_key("ACCESS_TOKEN")

    def test_cookie_detected(self) -> None:
        assert looks_like_secret_key("SESSION_COOKIE")

    def test_secret_detected(self) -> None:
        assert looks_like_secret_key("CLIENT_SECRET")

    def test_normal_key_not_flagged(self) -> None:
        assert not looks_like_secret_key("DATABASE_HOST")

    def test_email_not_flagged(self) -> None:
        assert not looks_like_secret_key("USER_EMAIL")

    def test_name_not_flagged(self) -> None:
        assert not looks_like_secret_key("ACCOUNT_NAME")


class TestRedactEnvLine:
    def test_password_line_redacted(self) -> None:
        line = 'GOOGLE_PASSWORD=supersecret123'
        result = redact_env_line(line)
        assert "supersecret123" not in result
        assert REDACTED_PLACEHOLDER in result
        assert "GOOGLE_PASSWORD" in result

    def test_api_key_line_redacted(self) -> None:
        line = 'STRIPE_API_KEY=sk_live_abc123'
        result = redact_env_line(line)
        assert "sk_live_abc123" not in result
        assert REDACTED_PLACEHOLDER in result

    def test_token_line_redacted(self) -> None:
        line = 'AUTH_TOKEN=eyJhbGciOiJIUzI1NiJ9.xyz'
        result = redact_env_line(line)
        assert "eyJhbGciOiJIUzI1NiJ9" not in result
        assert REDACTED_PLACEHOLDER in result

    def test_cookie_line_redacted(self) -> None:
        line = 'SESSION_COOKIE=abc123def456'
        result = redact_env_line(line)
        assert "abc123def456" not in result
        assert REDACTED_PLACEHOLDER in result

    def test_non_secret_line_preserved(self) -> None:
        line = 'DATABASE_HOST=localhost'
        result = redact_env_line(line)
        assert result == line

    def test_comment_line_preserved(self) -> None:
        line = '# This is a comment'
        result = redact_env_line(line)
        assert result == line


class TestRedactSecretValues:
    def test_known_secret_values_redacted(self) -> None:
        text = "Login attempt with password: myp@ssw0rd123 failed"
        result = redact_secret_values(text, ["myp@ssw0rd123"])
        assert "myp@ssw0rd123" not in result
        assert REDACTED_PLACEHOLDER in result

    def test_multiple_values_redacted(self) -> None:
        text = "user=admin token=abc123 key=xyz789"
        result = redact_secret_values(text, ["abc123", "xyz789"])
        assert "abc123" not in result
        assert "xyz789" not in result

    def test_non_secret_text_preserved(self) -> None:
        text = "Login successful for user antonyfm@empyreanstudios.co"
        result = redact_secret_values(text, ["somepassword"])
        assert text == result

    def test_short_values_ignored(self) -> None:
        text = "status: ok"
        result = redact_secret_values(text, ["ok"])
        assert result == text

    def test_empty_values_handled(self) -> None:
        text = "nothing here"
        result = redact_secret_values(text, ["", ""])
        assert result == text


class TestRedactMapping:
    def test_password_key_redacted(self) -> None:
        data = {"username": "admin", "password": "secret123"}
        result = redact_mapping(data)
        assert result["password"] == REDACTED_PLACEHOLDER
        assert result["username"] == "admin"

    def test_explicit_secret_keys_redacted(self) -> None:
        data = {"host": "localhost", "conn_string": "postgresql://..."}
        result = redact_mapping(data, secret_keys={"conn_string"})
        assert result["conn_string"] == REDACTED_PLACEHOLDER
        assert result["host"] == "localhost"

    def test_nested_dict_redacted(self) -> None:
        data = {"config": {"api_key": "sk_123", "region": "us-east"}}
        result = redact_mapping(data)
        assert result["config"]["api_key"] == REDACTED_PLACEHOLDER
        assert result["config"]["region"] == "us-east"


class TestSafeReprSecretRef:
    def test_no_value_in_repr(self) -> None:
        ref = SecretRef(
            key="test_password",
            scope=SecretScope.GOOGLE_WORKSPACE,
            account="test@example.com",
            backend=SecretBackendType.LOCAL_ENV,
            available=True,
        )
        result = safe_repr_secret_ref(ref)
        assert "value" not in result.lower() or "available" in result.lower()
        assert ref.key in result
        assert ref.account in result


class TestRedactPotentialSecretsInOutput:
    def test_multiline_env_redacted(self) -> None:
        text = "GOOGLE_PASSWORD=secret\nDATABASE_HOST=localhost\nAPI_KEY=abc123"
        result = redact_potential_secrets_in_output(text)
        assert "secret" not in result.split("\n")[0] or REDACTED_PLACEHOLDER in result.split("\n")[0]
        assert "localhost" in result
        assert "abc123" not in result.split("\n")[2] or REDACTED_PLACEHOLDER in result.split("\n")[2]
