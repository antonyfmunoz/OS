"""Tests for umh.protocols.adapters."""

from typing import Any

import pytest
from pydantic import ValidationError

from control_plane.protocols.adapters import (
    AccessPath,
    Adapter,
    AdapterPackage,
    Connection,
    ExternalRequest,
    ExternalResponse,
    NormalizedResult,
    StateSnapshot,
    ValidationResult,
)
from control_plane.protocols.common import (
    AdapterCategory,
    CapabilityRef,
    EnvironmentType,
    MaturityStatus,
)


class TestAdapterProtocol:
    def test_adapter_protocol_methods_present(self) -> None:
        required_methods = [
            "connect",
            "validate_connection",
            "describe_capabilities",
            "translate_request",
            "validate_operation",
            "normalize_result",
            "observe_state",
            "disconnect",
        ]
        for method in required_methods:
            assert hasattr(Adapter, method), f"Adapter missing method: {method}"

    def test_minimal_stub_satisfies_protocol(self) -> None:
        class StubAdapter:
            def connect(self) -> Connection:
                return Connection(connected=True, adapter_id="stub")

            def validate_connection(self) -> ValidationResult:
                return ValidationResult(valid=True)

            def describe_capabilities(self) -> list[CapabilityRef]:
                return []

            def translate_request(self, work_packet: Any) -> ExternalRequest:
                return ExternalRequest(request_id="r-1", method="GET", target="/")

            def validate_operation(self, request: ExternalRequest) -> ValidationResult:
                return ValidationResult(valid=True)

            def normalize_result(self, raw: ExternalResponse) -> NormalizedResult:
                return NormalizedResult(success=True, data=raw.body)

            def observe_state(self) -> StateSnapshot:
                return StateSnapshot(adapter_id="stub", timestamp=0)

            def disconnect(self) -> None:
                pass

        stub = StubAdapter()
        assert isinstance(stub, Adapter)


class TestConnection:
    def test_minimal_construction(self) -> None:
        c = Connection(connected=True, adapter_id="gws-core")
        assert c.SCHEMA_VERSION == "1.0.0"
        assert c.session_id == ""

    def test_roundtrip(self) -> None:
        c = Connection(connected=True, adapter_id="a-1", session_id="s-1")
        assert Connection.model_validate(c.model_dump()) == c

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            Connection(connected=True, adapter_id="x", bad="field")


class TestAdapterPackage:
    def test_minimal_construction(self) -> None:
        ap = AdapterPackage(
            package_id="pkg-1",
            name="Google Docs API",
            external_system="Google Docs",
            category=AdapterCategory.API,
        )
        assert ap.SCHEMA_VERSION == "1.0.0"
        assert ap.maturity_status == MaturityStatus.EXPERIMENTAL
        assert ap.version == "0.1.0"

    def test_roundtrip(self) -> None:
        ap = AdapterPackage(
            package_id="pkg-2",
            name="Gmail API",
            external_system="Gmail",
            category=AdapterCategory.SAAS,
            supported_environments=[EnvironmentType.VPS, EnvironmentType.CLOUD],
            maturity_status=MaturityStatus.MATURE,
            version="1.2.0",
        )
        assert AdapterPackage.model_validate(ap.model_dump()) == ap

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            AdapterPackage(
                package_id="x", name="x", external_system="x",
                category=AdapterCategory.API, bad="field",
            )

    def test_schema_version_present(self) -> None:
        ap = AdapterPackage(
            package_id="x", name="x", external_system="x",
            category=AdapterCategory.TOOL,
        )
        assert ap.SCHEMA_VERSION == "1.0.0"


class TestAccessPath:
    def test_minimal_construction(self) -> None:
        ap = AccessPath(path_id="ap-1", method="API")
        assert ap.SCHEMA_VERSION == "1.0.0"
        assert ap.description == ""
