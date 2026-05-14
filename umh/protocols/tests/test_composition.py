"""Tests for umh.protocols.composition."""

import pytest
from pydantic import ValidationError

from umh.protocols.composition import (
    Capability,
    ExecutableComposition,
    MasteryRequirement,
    RegistryItem,
    Template,
)
from umh.protocols.common import (
    AuthorityLevel,
    ItemStatus,
    MasteryCategory,
    MasteryStatus,
    RiskLevel,
)


class TestRegistryItem:
    def test_minimal_construction(self) -> None:
        ri = RegistryItem(id="ri-1", name="shell_command", type="capability", version="1.0.0")
        assert ri.SCHEMA_VERSION == "1.0.0"
        assert ri.status == ItemStatus.ACTIVE
        assert ri.reliability == 1.0

    def test_roundtrip(self) -> None:
        ri = RegistryItem(
            id="ri-2", name="google_docs_api", type="adapter",
            version="2.1.0", authority_required=AuthorityLevel.NOTIFY,
        )
        assert RegistryItem.model_validate(ri.model_dump()) == ri

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            RegistryItem(id="x", name="x", type="x", version="x", bad="field")

    def test_schema_version_present(self) -> None:
        ri = RegistryItem(id="x", name="x", type="x", version="x")
        assert ri.SCHEMA_VERSION == "1.0.0"

    def test_required_field_missing(self) -> None:
        with pytest.raises(ValidationError):
            RegistryItem(id="x", name="x")  # type: ignore[call-arg]


class TestTemplate:
    def test_minimal_construction(self) -> None:
        t = Template(id="t-1", name="outreach_email", domain="sales", purpose="send cold email")
        assert t.SCHEMA_VERSION == "1.0.0"
        assert t.immutable_primitives == []

    def test_roundtrip(self) -> None:
        t = Template(id="t-2", name="deploy", domain="software", purpose="deploy service")
        assert Template.model_validate(t.model_dump()) == t

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            Template(id="x", name="x", domain="x", purpose="x", extra="bad")


class TestCapability:
    def test_minimal_construction(self) -> None:
        c = Capability(capability_id="cap-1", name="shell_command")
        assert c.SCHEMA_VERSION == "1.0.0"
        assert c.authority_required == AuthorityLevel.AUTONOMOUS
        assert c.reliability == 1.0

    def test_roundtrip(self) -> None:
        c = Capability(
            capability_id="cap-2", name="api_call",
            authority_required=AuthorityLevel.NOTIFY,
        )
        assert Capability.model_validate(c.model_dump()) == c

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            Capability(capability_id="x", name="x", bogus=True)


class TestExecutableComposition:
    def test_minimal_construction(self) -> None:
        ec = ExecutableComposition(composition_id="comp-1", goal="deploy app")
        assert ec.SCHEMA_VERSION == "1.0.0"
        assert ec.steps == []
        assert ec.selected_template is None

    def test_roundtrip(self) -> None:
        ec = ExecutableComposition(composition_id="comp-2", goal="send email")
        assert ExecutableComposition.model_validate(ec.model_dump()) == ec


class TestMasteryRequirement:
    def test_minimal_construction(self) -> None:
        mr = MasteryRequirement(
            mastery_id="m-1",
            category=MasteryCategory.TOOL,
            target="google_docs_api",
        )
        assert mr.SCHEMA_VERSION == "1.0.0"
        assert mr.current_status == MasteryStatus.NOT_ASSESSED
        assert mr.risk_level == RiskLevel.READ_ONLY

    def test_roundtrip(self) -> None:
        mr = MasteryRequirement(
            mastery_id="m-2",
            category=MasteryCategory.ADAPTER_BOUNDARY,
            target="gws_core",
            current_status=MasteryStatus.PROVEN,
        )
        assert MasteryRequirement.model_validate(mr.model_dump()) == mr

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            MasteryRequirement(
                mastery_id="x", category=MasteryCategory.TOOL,
                target="x", bad="field",
            )
