"""Tests for cc_sdk error-leak detection."""

import os
import sys

import pytest

sys.path.insert(0, os.environ.get("UMH_ROOT") or "/opt/OS")

from adapters.models.cc_sdk import _is_error_leak


ANTHROPIC_AUTH_ERROR = (
    "Failed to authenticate with the API. Your API key may be invalid, "
    "expired, or revoked. Please check your API key and try again. If you "
    "continue to experience issues, please contact support@anthropic.com.\n\n"
    "Error details:\n"
    "  Type: authentication_error\n"
    "  Status: 401\n"
    "  Message: Your credit balance is too low to access the Anthropic API. "
    "Please go to Plans & Billing to upgrade or purchase credits."
)

VALID_LLM_RESPONSE = (
    '{"observations": [{"primitive_type": "constraint", '
    '"label": "Founder must close first 10 sales", '
    '"description": "Hiring a salesperson for an unproven process trains someone to fail.", '
    '"confidence": 0.92, "source_reference": "test.md:1-5", '
    '"evidence": "Founder closes first.", "is_inferred": false}], '
    '"relationships": []}'
)

MCP_SHUTDOWN_PARTIAL = (
    '{"observations": [{"primitive_type": "state", '
    '"label": "Current revenue is pre-revenue", '
    '"description": "No sales closed yet.", '
    '"confidence": 0.85, "source_reference": "doc:1", '
    '"evidence": "Pre-revenue stage.", "is_inferred": false}], '
    '"relationships": []}'
)


class TestAuthErrorReturnsNone:
    def test_exact_anthropic_auth_error(self):
        assert _is_error_leak(ANTHROPIC_AUTH_ERROR) is True

    def test_auth_error_with_different_message(self):
        text = (
            "Error details:\n"
            "  Type: authentication_error\n"
            "  Status: 401\n"
            "  Message: Invalid API key provided."
        )
        assert _is_error_leak(text) is True


class TestValidContentNotFlagged:
    def test_structured_json_response(self):
        assert _is_error_leak(VALID_LLM_RESPONSE) is False

    def test_plain_text_analysis(self):
        text = (
            "The business model has three key constraints: "
            "1) founder must close first sales, "
            "2) organic growth before paid, "
            "3) product-market fit before scaling."
        )
        assert _is_error_leak(text) is False

    def test_text_about_authentication_concepts(self):
        text = (
            "The authentication system uses OAuth 2.0 with JWT tokens. "
            "When a user's session expires, they receive an error message "
            "and must re-authenticate. Rate limiting is applied per-endpoint."
        )
        assert _is_error_leak(text) is False


class TestMCPShutdownPartialOutputValid:
    def test_mcp_shutdown_with_valid_json(self):
        assert _is_error_leak(MCP_SHUTDOWN_PARTIAL) is False

    def test_partial_analysis_text(self):
        text = (
            "Based on the document analysis, the key insight is that "
            "direct outreach via DM converts better than content marketing "
            "in the early stages. The founder should focus on"
        )
        assert _is_error_leak(text) is False


class TestEachHighConfidenceSignature:
    def test_authentication_error(self):
        assert _is_error_leak("Type: authentication_error") is True

    def test_rate_limit_error(self):
        assert _is_error_leak("Type: rate_limit_error\nStatus: 429") is True

    def test_overloaded_error(self):
        assert _is_error_leak("Anthropic API overloaded_error — please retry") is True

    def test_invalid_request_error(self):
        assert _is_error_leak("Type: invalid_request_error\nStatus: 400") is True

    def test_credit_balance(self):
        assert _is_error_leak("Your credit balance is too low") is True

    def test_invalid_x_api_key(self):
        assert _is_error_leak("invalid x-api-key header provided") is True

    def test_case_insensitive(self):
        assert _is_error_leak("AUTHENTICATION_ERROR occurred") is True
        assert _is_error_leak("Credit Balance is insufficient") is True


class TestEmptyStringReturnsNone:
    def test_empty_string(self):
        assert _is_error_leak("") is False

    def test_whitespace_only(self):
        assert _is_error_leak("   \n\t  ") is False
