"""UMH Protocol Commons — shared enums, refs, and sub-models.

All types used across multiple protocol layers live here.
Imports: standard library + pydantic only.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SignalModality(StrEnum):
    """Modality of a perceived signal. Defined in canonical synthesis §9.1."""

    TEXT = "text"
    VOICE = "voice"
    AUDIO = "audio"
    VIDEO = "video"
    SCREEN_STATE = "screen_state"
    FILE_EVENT = "file_event"
    SYSTEM_EVENT = "system_event"
    BROWSER_EVENT = "browser_event"
    API_EVENT = "api_event"
    EXECUTION_RESULT = "execution_result"
    BEHAVIORAL_PATTERN = "behavioral_pattern"
    DEVICE_STATE = "device_state"
    ENVIRONMENT_STATE = "environment_state"
    HUMAN_FEEDBACK = "human_feedback"
    SENSOR = "sensor"


class PrimitiveType(StrEnum):
    """Core ontological primitives. Defined in canonical synthesis §6.1."""

    STATE = "state"
    CHANGE = "change"
    CONSTRAINT = "constraint"
    RESOURCE = "resource"
    TIME = "time"
    SIGNAL = "signal"
    FEEDBACK = "feedback"
    GOAL = "goal"
    ACTION = "action"
    OUTCOME = "outcome"


class RelationshipType(StrEnum):
    """Relationship types between primitives/entities."""

    ENABLES = "enables"
    PRODUCES = "produces"
    REQUIRES = "requires"
    CONSTRAINS = "constrains"
    FOLLOWS = "follows"
    MEASURES = "measures"
    CONTAINS = "contains"
    DEPENDS_ON = "depends_on"
    CONFLICTS_WITH = "conflicts_with"
    SUPPORTS = "supports"


class AuthorityLevel(StrEnum):
    """Governance authority levels. Defined in canonical synthesis §12."""

    AUTONOMOUS = "autonomous"
    NOTIFY = "notify"
    APPROVE = "approve"
    ESCALATE = "escalate"
    DENY = "deny"


class RiskLevel(StrEnum):
    """Risk classification. Defined in canonical synthesis §12."""

    READ_ONLY = "read_only"
    REVERSIBLE_WRITE = "reversible_write"
    IRREVERSIBLE_WRITE = "irreversible_write"
    FINANCIAL = "financial"
    SECURITY_SENSITIVE = "security_sensitive"
    IDENTITY_REPUTATION = "identity_reputation"
    DESTRUCTIVE_LOCAL = "destructive_local"
    EXTERNAL_COMMUNICATION = "external_communication"
    LEGAL_COMPLIANCE = "legal_compliance"
    PHYSICAL_WORLD = "physical_world"


class MemoryType(StrEnum):
    """14 memory types. Defined in canonical synthesis §10.2."""

    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    CANONICAL = "canonical"
    INSTANCE = "instance"
    BEHAVIORAL = "behavioral"
    PROCEDURAL = "procedural"
    TRACE_DERIVED = "trace_derived"
    PROFILE = "profile"
    ENVIRONMENT = "environment"
    GOAL = "goal"
    WORLD_STATE = "world_state"
    PATTERN = "pattern"
    POLICY = "policy"


class PromotionStatus(StrEnum):
    """Memory promotion lifecycle. Defined in canonical synthesis §10.3."""

    CANDIDATE = "candidate"
    UNDER_REVIEW = "under_review"
    PROMOTED = "promoted"
    CANONICAL = "canonical"
    DEMOTED = "demoted"
    EXPIRED = "expired"


class MasteryCategory(StrEnum):
    """11 mastery categories. Defined in canonical synthesis §5.11."""

    TOOL = "tool"
    ACTION = "action"
    DOMAIN = "domain"
    ENVIRONMENT = "environment"
    DATA = "data"
    MODEL = "model"
    ADAPTER_BOUNDARY = "adapter_boundary"
    HUMAN_APPROVAL = "human_approval"
    GOVERNANCE = "governance"
    CONTEXT = "context"
    PHYSICAL_WORLD = "physical_world"


class MasteryStatus(StrEnum):
    """Current mastery level for a requirement."""

    NOT_ASSESSED = "not_assessed"
    INSUFFICIENT = "insufficient"
    PROVISIONAL = "provisional"
    SUFFICIENT = "sufficient"
    PROVEN = "proven"
    EXPIRED = "expired"


class ItemStatus(StrEnum):
    """Registry item lifecycle status."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"
    DISABLED = "disabled"


class EnvironmentType(StrEnum):
    """Execution environment types. Defined in canonical synthesis §13.4."""

    VPS = "vps"
    LOCAL_WSL = "local_wsl"
    LOCAL_GUI = "local_gui"
    CONTAINER = "container"
    CLOUD = "cloud"
    SANDBOX = "sandbox"
    MOBILE = "mobile"
    BROWSER = "browser"
    OFFLINE = "offline"


class AdapterCategory(StrEnum):
    """15 adapter categories. Defined in canonical synthesis §14.2."""

    TOOL = "tool"
    SAAS = "saas"
    API = "api"
    CLI = "cli"
    MCP = "mcp"
    ENVIRONMENT = "environment"
    RUNTIME = "runtime"
    MODEL = "model"
    HUMAN_APPROVAL = "human_approval"
    DATA_SOURCE = "data_source"
    FILESYSTEM = "filesystem"
    DATABASE = "database"
    BROWSER = "browser"
    COMPUTER_USE = "computer_use"
    PHYSICAL_WORLD = "physical_world"


class MaturityStatus(StrEnum):
    """Adapter/capability maturity. Referenced in §14.3."""

    EXPERIMENTAL = "experimental"
    PROVISIONAL = "provisional"
    MATURE = "mature"
    PROVEN = "proven"
    DEPRECATED = "deprecated"


class EvidenceType(StrEnum):
    """Proof evidence types. Defined in canonical synthesis §15.2."""

    UNIT_TEST = "unit_test"
    INTEGRATION_TEST = "integration_test"
    SCREENSHOT = "screenshot"
    API_RESPONSE = "api_response"
    LOG_TRACE = "log_trace"
    FILE_HASH = "file_hash"
    USER_CONFIRMATION = "user_confirmation"
    PARITY_CHECK = "parity_check"
    RUNTIME_ASSERTION = "runtime_assertion"


class ConfirmationStatus(StrEnum):
    """Founder/operator confirmation state. Referenced in §15.2."""

    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    CONFIRMED = "confirmed"
    DENIED = "denied"


class PacketStatus(StrEnum):
    """Work packet lifecycle. Referenced in §13.2."""

    CREATED = "created"
    QUEUED = "queued"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ApprovalStatus(StrEnum):
    """Approval state for governed actions. Referenced in §13.2."""

    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"


class SignalType(StrEnum):
    """Internal signal types for organism layer. Defined in §16.2."""

    HEALTH_CHECK = "health_check"
    RESOURCE_WARNING = "resource_warning"
    ANOMALY = "anomaly"
    BACKPRESSURE = "backpressure"
    DEGRADED_MODE = "degraded_mode"
    HEARTBEAT = "heartbeat"
    BUDGET_ALERT = "budget_alert"
    STUCK_LOOP = "stuck_loop"
    RETRY_SUPPRESSION = "retry_suppression"


class Severity(StrEnum):
    """Signal severity levels. Referenced in §16.2."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Ref types (lightweight pointers)
# ---------------------------------------------------------------------------


class EvidenceRef(BaseModel):
    """Pointer to a piece of evidence."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    ref_id: str
    source: str
    evidence_type: EvidenceType | None = None


class EnvironmentRef(BaseModel):
    """Pointer to an environment."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    environment_id: str
    type: EnvironmentType | None = None


class CapabilityRef(BaseModel):
    """Pointer to a capability."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    capability_id: str
    name: str | None = None


class AdapterRef(BaseModel):
    """Pointer to an adapter."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    adapter_id: str
    name: str | None = None


class WorkerRef(BaseModel):
    """Pointer to a worker runtime."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    worker_id: str
    type: str | None = None


class TemplateRef(BaseModel):
    """Pointer to a template."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    template_id: str
    name: str | None = None


class WorkflowRef(BaseModel):
    """Pointer to a workflow."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    workflow_id: str
    name: str | None = None


class MemoryRef(BaseModel):
    """Pointer to a memory record."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    memory_id: str
    type: MemoryType | None = None


class GovernancePolicyRef(BaseModel):
    """Pointer to a governance policy."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    policy_id: str
    name: str | None = None


class AdapterPackageRef(BaseModel):
    """Pointer to an adapter package."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    package_id: str
    name: str | None = None


class MasteryRef(BaseModel):
    """Pointer to a mastery requirement."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    mastery_id: str
    category: MasteryCategory | None = None


class RelationshipRef(BaseModel):
    """Pointer to a relationship."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    relationship_id: str
    type: RelationshipType | None = None


class TestRef(BaseModel):
    """Pointer to a test."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    test_id: str
    name: str | None = None


# ---------------------------------------------------------------------------
# Shared sub-models
# ---------------------------------------------------------------------------


class CostModel(BaseModel):
    """Cost estimation for a capability or action."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    per_call_usd: float | None = None
    monthly_usd: float | None = None
    params: dict[str, Any] = {}


class LatencyModel(BaseModel):
    """Latency estimation for a capability or action."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    p50_ms: float | None = None
    p95_ms: float | None = None
    p99_ms: float | None = None


class Constraint(BaseModel):
    """A named constraint on an action, composition, or environment."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    constraint_id: str
    name: str
    description: str = ""
    type: str = ""


class FailureMode(BaseModel):
    """A known failure mode for a capability, action, or adapter."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    failure_id: str
    name: str
    description: str = ""
    severity: Severity = Severity.ERROR
    mitigation: str = ""


class Slot(BaseModel):
    """A fillable slot in a template or composition."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    slot_id: str
    name: str
    type: str = "string"
    required: bool = True
    default: Any = None
    description: str = ""


class Step(BaseModel):
    """A single step in a plan or composition."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    step_id: str
    name: str
    description: str = ""
    order: int = 0
    depends_on: list[str] = []


class ProofRequirement(BaseModel):
    """What evidence is needed to prove an action completed correctly."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    requirement_id: str
    evidence_type: EvidenceType
    description: str = ""
    required: bool = True


class Benchmark(BaseModel):
    """A quality or performance benchmark."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    benchmark_id: str
    name: str
    metric: str = ""
    threshold: float | None = None
    description: str = ""


class Permission(BaseModel):
    """A specific permission grant. Referenced in §12, used across layers."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    permission_id: str
    name: str
    scope: str = ""
    description: str = ""


class AuthorityContext(BaseModel):
    """Authority context attached to control plane events. Referenced in §8."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    authority_level: AuthorityLevel
    risk_level: RiskLevel | None = None
    requesting_module: str = ""
    justification: str = ""
