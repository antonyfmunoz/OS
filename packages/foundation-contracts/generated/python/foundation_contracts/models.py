"""Generated foundation contract Pydantic models. Do not hand-edit."""

from __future__ import annotations

import re

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RecurrenceRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    frequency: Literal['daily', 'weekly', 'monthly', 'yearly']
    interval: int = Field(ge=1)
    count: int | None = Field(default=None, ge=1)
    until_at: str | None = Field(default=None)
    by_weekday: list[Literal['MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU']] | None = Field(default=None)
    exceptions: list[str] | None = Field(default=None)


class CalendarResource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['Resource']
    schema_version: Literal['1.0.0']
    name: str = Field(min_length=1)
    resource_type: Literal['person', 'room', 'equipment', 'service', 'pool']
    capacity: int = Field(ge=1)
    status: Literal['active', 'unavailable', 'archived']
    created_at: str
    updated_at: str
    version: int = Field(ge=1)
    extensions: dict[str, Any] | None = Field(default=None)

    @field_validator('extensions')
    @classmethod
    def _validate_extensions_property_names(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        pattern = re.compile('^[a-z][a-z0-9-]*(\\.[a-z][a-z0-9-]*)*\\.v[0-9]+$')
        invalid = [key for key in value if not pattern.match(key)]
        if invalid:
            raise ValueError(f'invalid extension namespace(s): {invalid}')
        return value


class FieldValue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field_id: str = Field(min_length=1)
    field_type: Literal['text', 'rich_text', 'number', 'boolean', 'date', 'datetime', 'select', 'multi_select', 'person_ref', 'organization_ref', 'relation', 'file_ref', 'url', 'email', 'phone', 'formula', 'rollup']
    value: str | float | bool | list[str] | dict[str, Any] | None


class Table(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['Table']
    schema_version: Literal['1.0.0']
    database_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    status: Literal['active', 'archived']
    created_at: str
    updated_at: str
    version: int = Field(ge=1)


class ActorRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    actorType: Literal['human', 'agent', 'service', 'system']
    actorId: str = Field(min_length=1)
    roleId: str | None = Field(default=None, min_length=1)
    delegatedBy: ActorRef | None = Field(default=None)


class ObjectRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    objectType: str = Field(min_length=1)
    objectId: str = Field(min_length=1)
    version: int | None = Field(default=None, ge=0)


class RuntimeBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    runtimeId: str = Field(min_length=1)
    runtimeKind: Literal['umh-native', 'projection-local', 'connected-federated', 'adapter']
    projectionId: str | None = Field(default=None, min_length=1)
    serviceName: str | None = Field(default=None, min_length=1)
    contractVersion: str = Field(pattern='^1\\.[0-9]+\\.[0-9]+$')


class File(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['File']
    schema_version: Literal['1.0.0']
    name: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    mime_type: str | None = Field(default=None)
    size_bytes: int | None = Field(default=None, ge=0)
    status: Literal['uploading', 'processing', 'ready', 'quarantined', 'archived', 'trashed', 'deleted']
    storage_binding: dict[str, Any]
    owner_ref: ObjectRef
    created_by: ActorRef
    created_at: str
    updated_at: str
    current_version_id: str | None = Field(default=None)
    visibility: str | None = Field(default=None)
    authority_scope: dict[str, Any] | None = Field(default=None)
    provenance: dict[str, Any] | None = Field(default=None)
    version: int = Field(ge=1)
    extensions: dict[str, Any] | None = Field(default=None)

    @field_validator('extensions')
    @classmethod
    def _validate_extensions_property_names(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        pattern = re.compile('^[a-z][a-z0-9-]*(\\.[a-z][a-z0-9-]*)*\\.v[0-9]+$')
        invalid = [key for key in value if not pattern.match(key)]
        if invalid:
            raise ValueError(f'invalid extension namespace(s): {invalid}')
        return value


class RegisterFilePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    mime_type: str | None = Field(default=None)
    size_bytes: int | None = Field(default=None, ge=0)
    storage_binding: dict[str, Any]
    owner_ref: ObjectRef
    extensions: dict[str, Any] | None = Field(default=None)

    @field_validator('extensions')
    @classmethod
    def _validate_extensions_property_names(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        pattern = re.compile('^[a-z][a-z0-9-]*(\\.[a-z][a-z0-9-]*)*\\.v[0-9]+$')
        invalid = [key for key in value if not pattern.match(key)]
        if invalid:
            raise ValueError(f'invalid extension namespace(s): {invalid}')
        return value


class FinancialAccount(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['Account']
    schema_version: Literal['1.0.0']
    name: str = Field(min_length=1)
    account_type: Literal['asset', 'liability', 'equity', 'income', 'expense']
    currency: str = Field(pattern='^[A-Z]{3}$')
    status: Literal['active', 'closed', 'archived']
    owner_ref: ObjectRef
    created_at: str
    updated_at: str
    version: int = Field(ge=1)
    extensions: dict[str, Any] | None = Field(default=None)

    @field_validator('extensions')
    @classmethod
    def _validate_extensions_property_names(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        pattern = re.compile('^[a-z][a-z0-9-]*(\\.[a-z][a-z0-9-]*)*\\.v[0-9]+$')
        invalid = [key for key in value if not pattern.match(key)]
        if invalid:
            raise ValueError(f'invalid extension namespace(s): {invalid}')
        return value


class Allocation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['Allocation']
    schema_version: Literal['1.0.0']
    source_transaction_ref: ObjectRef
    allocation_target_ref: ObjectRef
    amount: float
    currency: str = Field(pattern='^[A-Z]{3}$')
    status: Literal['active', 'reversed']
    created_at: str
    version: int = Field(ge=1)


class FinancialPeriod(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['FinancialPeriod']
    schema_version: Literal['1.0.0']
    name: str = Field(min_length=1)
    start_at: str
    end_at: str
    status: Literal['open', 'closed', 'locked']
    version: int = Field(ge=1)


class FormDestinationBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    binding_type: Literal['database_table', 'webhook', 'none']
    target_ref: ObjectRef
    field_mappings: list[dict[str, Any]]


class FormField(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['FormField']
    schema_version: Literal['1.0.0']
    form_id: str = Field(min_length=1)
    form_version: int = Field(ge=1)
    label: str = Field(min_length=1)
    field_type: Literal['text', 'long_text', 'number', 'boolean', 'date', 'datetime', 'select', 'multi_select', 'email', 'phone', 'url', 'file_ref', 'consent_ack', 'hidden']
    required: bool
    validation_rules: dict[str, Any] | None = Field(default=None)
    options: list[str] | None = Field(default=None)
    destination_field_id: str | None = Field(default=None)
    position: int = Field(ge=0)
    status: Literal['active', 'removed']


class Form(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['Form']
    schema_version: Literal['1.0.0']
    name: str = Field(min_length=1)
    description: str | None = Field(default=None)
    status: Literal['draft', 'published', 'closed', 'archived']
    current_version: int = Field(ge=1)
    fields: list[FormField]
    destination_binding: FormDestinationBinding | None = Field(default=None)
    privacy_policy_ref: ObjectRef | None = Field(default=None)
    owner_ref: ObjectRef
    created_by: ActorRef
    created_at: str
    updated_at: str
    version: int = Field(ge=1)
    extensions: dict[str, Any] | None = Field(default=None)

    @field_validator('extensions')
    @classmethod
    def _validate_extensions_property_names(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        pattern = re.compile('^[a-z][a-z0-9-]*(\\.[a-z][a-z0-9-]*)*\\.v[0-9]+$')
        invalid = [key for key in value if not pattern.match(key)]
        if invalid:
            raise ValueError(f'invalid extension namespace(s): {invalid}')
        return value


class SubmissionValue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field_id: str = Field(min_length=1)
    field_type: Literal['text', 'long_text', 'number', 'boolean', 'date', 'datetime', 'select', 'multi_select', 'email', 'phone', 'url', 'file_ref', 'consent_ack', 'hidden']
    value: str | float | bool | list[str] | dict[str, Any] | None


class ContactPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['ContactPoint']
    schema_version: Literal['1.0.0']
    owner_ref: ObjectRef
    kind: Literal['email', 'phone', 'social', 'messaging-address', 'website']
    value: str = Field(min_length=1)
    label: str | None = Field(default=None)
    is_primary: bool | None = Field(default=None)
    verification_state: Literal['unverified', 'pending', 'verified', 'failed']
    consent_ref: ObjectRef | None = Field(default=None)
    provenance: dict[str, Any]
    created_at: str
    updated_at: str
    version: int = Field(ge=1)
    extensions: dict[str, Any] | None = Field(default=None)

    @field_validator('extensions')
    @classmethod
    def _validate_extensions_property_names(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        pattern = re.compile('^[a-z][a-z0-9-]*(\\.[a-z][a-z0-9-]*)*\\.v[0-9]+$')
        invalid = [key for key in value if not pattern.match(key)]
        if invalid:
            raise ValueError(f'invalid extension namespace(s): {invalid}')
        return value


class CreatePersonPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    display_name: str = Field(min_length=1)
    given_name: str | None = Field(default=None)
    family_name: str | None = Field(default=None)
    preferred_name: str | None = Field(default=None)
    locale: str | None = Field(default=None)
    timezone: str | None = Field(default=None)
    extensions: dict[str, Any] | None = Field(default=None)

    @field_validator('extensions')
    @classmethod
    def _validate_extensions_property_names(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        pattern = re.compile('^[a-z][a-z0-9-]*(\\.[a-z][a-z0-9-]*)*\\.v[0-9]+$')
        invalid = [key for key in value if not pattern.match(key)]
        if invalid:
            raise ValueError(f'invalid extension namespace(s): {invalid}')
        return value


class CreateRelationshipPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject_ref: ObjectRef
    object_ref: ObjectRef
    relationship_class: str = Field(min_length=1)
    lifecycle_stage: str | None = Field(default=None)
    owner_actor_ref: ActorRef | None = Field(default=None)
    source: str = Field(min_length=1)
    started_at: str | None = Field(default=None)
    extensions: dict[str, Any] | None = Field(default=None)

    @field_validator('extensions')
    @classmethod
    def _validate_extensions_property_names(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        pattern = re.compile('^[a-z][a-z0-9-]*(\\.[a-z][a-z0-9-]*)*\\.v[0-9]+$')
        invalid = [key for key in value if not pattern.match(key)]
        if invalid:
            raise ValueError(f'invalid extension namespace(s): {invalid}')
        return value


class ExternalIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['ExternalIdentity']
    schema_version: Literal['1.0.0']
    owner_ref: ObjectRef
    provider: str = Field(min_length=1)
    provider_subject_id: str = Field(min_length=1)
    handle: str | None = Field(default=None)
    profile_url: str | None = Field(default=None)
    status: Literal['active', 'unverified', 'revoked', 'archived']
    verified_at: str | None = Field(default=None)
    created_at: str
    updated_at: str
    version: int = Field(ge=1)
    extensions: dict[str, Any] | None = Field(default=None)

    @field_validator('extensions')
    @classmethod
    def _validate_extensions_property_names(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        pattern = re.compile('^[a-z][a-z0-9-]*(\\.[a-z][a-z0-9-]*)*\\.v[0-9]+$')
        invalid = [key for key in value if not pattern.match(key)]
        if invalid:
            raise ValueError(f'invalid extension namespace(s): {invalid}')
        return value


class Facet(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['Facet']
    schema_version: Literal['1.0.0']
    relationship_id: str = Field(min_length=1)
    facet_key: Literal['customer', 'prospect', 'employee', 'candidate', 'vendor', 'investor', 'audience', 'sponsor', 'affiliate', 'collaborator', 'friend', 'family', 'mentor']
    status: Literal['active', 'inactive', 'archived']
    effective_from: str | None = Field(default=None)
    effective_to: str | None = Field(default=None)
    projection_namespace: str | None = Field(default=None)
    metadata: dict[str, Any] | None = Field(default=None)
    created_at: str
    updated_at: str
    version: int = Field(ge=1)
    extensions: dict[str, Any] | None = Field(default=None)

    @field_validator('extensions')
    @classmethod
    def _validate_extensions_property_names(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        pattern = re.compile('^[a-z][a-z0-9-]*(\\.[a-z][a-z0-9-]*)*\\.v[0-9]+$')
        invalid = [key for key in value if not pattern.match(key)]
        if invalid:
            raise ValueError(f'invalid extension namespace(s): {invalid}')
        return value


class FollowUp(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['FollowUp']
    schema_version: Literal['1.0.0']
    relationship_id: str = Field(min_length=1)
    opportunity_id: str | None = Field(default=None)
    task_ref: ObjectRef | None = Field(default=None)
    due_at: str
    status: Literal['open', 'completed', 'canceled']
    owner_actor_ref: ActorRef
    reason: str | None = Field(default=None)
    created_at: str
    updated_at: str
    version: int = Field(ge=1)


class Opportunity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['Opportunity']
    schema_version: Literal['1.0.0']
    relationship_id: str = Field(min_length=1)
    pipeline_id: str = Field(min_length=1)
    stage_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    status: Literal['open', 'won', 'lost', 'canceled']
    amount: float | None = Field(default=None)
    currency: str | None = Field(default=None, pattern='^[A-Z]{3}$')
    probability: float | None = Field(default=None, ge=0, le=1)
    expected_close_at: str | None = Field(default=None)
    owner_actor_ref: ActorRef | None = Field(default=None)
    source: str = Field(min_length=1)
    created_at: str
    updated_at: str
    version: int = Field(ge=1)
    extensions: dict[str, Any] | None = Field(default=None)

    @field_validator('extensions')
    @classmethod
    def _validate_extensions_property_names(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        pattern = re.compile('^[a-z][a-z0-9-]*(\\.[a-z][a-z0-9-]*)*\\.v[0-9]+$')
        invalid = [key for key in value if not pattern.match(key)]
        if invalid:
            raise ValueError(f'invalid extension namespace(s): {invalid}')
        return value


class Organization(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['Organization']
    schema_version: Literal['1.0.0']
    display_name: str = Field(min_length=1)
    status: Literal['active', 'archived', 'merged']
    legal_name: str | None = Field(default=None)
    organization_kind: str | None = Field(default=None)
    website: str | None = Field(default=None)
    locale: str | None = Field(default=None)
    timezone: str | None = Field(default=None)
    created_at: str
    updated_at: str
    version: int = Field(ge=1)
    extensions: dict[str, Any] | None = Field(default=None)

    @field_validator('extensions')
    @classmethod
    def _validate_extensions_property_names(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        pattern = re.compile('^[a-z][a-z0-9-]*(\\.[a-z][a-z0-9-]*)*\\.v[0-9]+$')
        invalid = [key for key in value if not pattern.match(key)]
        if invalid:
            raise ValueError(f'invalid extension namespace(s): {invalid}')
        return value


class Person(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['Person']
    schema_version: Literal['1.0.0']
    display_name: str = Field(min_length=1)
    status: Literal['active', 'archived', 'merged']
    given_name: str | None = Field(default=None)
    family_name: str | None = Field(default=None)
    preferred_name: str | None = Field(default=None)
    locale: str | None = Field(default=None)
    timezone: str | None = Field(default=None)
    avatar_file_id: str | None = Field(default=None)
    created_at: str
    updated_at: str
    version: int = Field(ge=1)
    extensions: dict[str, Any] | None = Field(default=None)

    @field_validator('extensions')
    @classmethod
    def _validate_extensions_property_names(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        pattern = re.compile('^[a-z][a-z0-9-]*(\\.[a-z][a-z0-9-]*)*\\.v[0-9]+$')
        invalid = [key for key in value if not pattern.match(key)]
        if invalid:
            raise ValueError(f'invalid extension namespace(s): {invalid}')
        return value


class Pipeline(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['Pipeline']
    schema_version: Literal['1.0.0']
    name: str = Field(min_length=1)
    status: Literal['active', 'archived']
    projection_namespace: str | None = Field(default=None)
    created_at: str
    updated_at: str
    version: int = Field(ge=1)


class Relationship(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['Relationship']
    schema_version: Literal['1.0.0']
    subject_ref: ObjectRef
    object_ref: ObjectRef
    relationship_class: str = Field(min_length=1)
    lifecycle_stage: str | None = Field(default=None)
    status: Literal['active', 'blocked', 'archived']
    owner_actor_ref: ActorRef | None = Field(default=None)
    source: str = Field(min_length=1)
    started_at: str | None = Field(default=None)
    ended_at: str | None = Field(default=None)
    created_at: str
    updated_at: str
    version: int = Field(ge=1)
    extensions: dict[str, Any] | None = Field(default=None)

    @field_validator('extensions')
    @classmethod
    def _validate_extensions_property_names(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        pattern = re.compile('^[a-z][a-z0-9-]*(\\.[a-z][a-z0-9-]*)*\\.v[0-9]+$')
        invalid = [key for key in value if not pattern.match(key)]
        if invalid:
            raise ValueError(f'invalid extension namespace(s): {invalid}')
        return value


class Stage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['Stage']
    schema_version: Literal['1.0.0']
    pipeline_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    ordinal: int = Field(ge=0)
    terminal_kind: Literal['none', 'won', 'lost']
    entry_policy: dict[str, Any] | None = Field(default=None)
    exit_policy: dict[str, Any] | None = Field(default=None)
    created_at: str
    updated_at: str
    version: int = Field(ge=1)


class Assignment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['Assignment']
    schema_version: Literal['1.0.0']
    conversation_id: str = Field(min_length=1)
    actor_ref: ActorRef
    queue: str | None = Field(default=None)
    status: Literal['active', 'released']
    assigned_at: str
    released_at: str | None = Field(default=None)
    created_at: str
    updated_at: str
    version: int = Field(ge=1)


class MessageAttachment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['Attachment']
    schema_version: Literal['1.0.0']
    message_id: str = Field(min_length=1)
    file_ref: ObjectRef | None = Field(default=None)
    external_media_id: str | None = Field(default=None)
    attachment_kind: str = Field(min_length=1)
    filename: str | None = Field(default=None)
    mime_type: str | None = Field(default=None)
    size_bytes: int | None = Field(default=None, ge=0)
    duration_ms: int | None = Field(default=None, ge=0)
    provider_metadata: dict[str, Any] | None = Field(default=None)
    created_at: str
    version: int = Field(ge=1)


class ChannelBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['ChannelBinding']
    schema_version: Literal['1.0.0']
    provider: str = Field(min_length=1)
    connection_ref: ObjectRef
    channel_kind: Literal['native', 'email', 'sms', 'whatsapp', 'instagram', 'messenger', 'x', 'other']
    external_thread_id: str | None = Field(default=None)
    status: Literal['pending', 'active', 'disabled', 'revoked', 'error']
    capabilities: list[str] = Field(min_length=1)
    created_at: str
    updated_at: str
    version: int = Field(ge=1)
    extensions: dict[str, Any] | None = Field(default=None)

    @field_validator('extensions')
    @classmethod
    def _validate_extensions_property_names(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        pattern = re.compile('^[a-z][a-z0-9-]*(\\.[a-z][a-z0-9-]*)*\\.v[0-9]+$')
        invalid = [key for key in value if not pattern.match(key)]
        if invalid:
            raise ValueError(f'invalid extension namespace(s): {invalid}')
        return value


class Conversation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['Conversation']
    schema_version: Literal['1.0.0']
    relationship_refs: list[ObjectRef] | None = Field(default=None)
    participant_refs: list[ObjectRef] | None = Field(default=None)
    status: Literal['open', 'pending', 'snoozed', 'closed', 'spam']
    priority: Literal['low', 'normal', 'high', 'urgent']
    queue: str | None = Field(default=None)
    assigned_actor_ref: ActorRef | None = Field(default=None)
    subject: str | None = Field(default=None)
    channel_binding_refs: list[ObjectRef] | None = Field(default=None)
    snoozed_until: str | None = Field(default=None)
    last_message_at: str | None = Field(default=None)
    ai_mode: Literal['observe', 'suggest', 'approval', 'delegated']
    created_at: str
    updated_at: str
    version: int = Field(ge=1)
    extensions: dict[str, Any] | None = Field(default=None)

    @field_validator('extensions')
    @classmethod
    def _validate_extensions_property_names(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        pattern = re.compile('^[a-z][a-z0-9-]*(\\.[a-z][a-z0-9-]*)*\\.v[0-9]+$')
        invalid = [key for key in value if not pattern.match(key)]
        if invalid:
            raise ValueError(f'invalid extension namespace(s): {invalid}')
        return value


class InternalNote(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['InternalNote']
    schema_version: Literal['1.0.0']
    conversation_id: str = Field(min_length=1)
    body: str = Field(min_length=1)
    author_actor_ref: ActorRef
    visibility: Literal['private', 'team', 'organization']
    created_at: str
    updated_at: str
    version: int = Field(ge=1)


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['Message']
    schema_version: Literal['1.0.0']
    conversation_id: str = Field(min_length=1)
    sender_participant_ref: ObjectRef | None = Field(default=None)
    sender_actor_ref: ActorRef | None = Field(default=None)
    direction: Literal['inbound', 'outbound', 'internal']
    body: str
    body_format: Literal['plain', 'markdown', 'html']
    status: Literal['draft', 'queued', 'sent', 'delivered', 'read', 'failed', 'bounced', 'rejected', 'received']
    reply_to_message_id: str | None = Field(default=None)
    provider_message_id: str | None = Field(default=None)
    idempotency_key: str | None = Field(default=None)
    sent_at: str | None = Field(default=None)
    received_at: str | None = Field(default=None)
    created_at: str
    updated_at: str
    version: int = Field(ge=1)
    extensions: dict[str, Any] | None = Field(default=None)

    @field_validator('extensions')
    @classmethod
    def _validate_extensions_property_names(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        pattern = re.compile('^[a-z][a-z0-9-]*(\\.[a-z][a-z0-9-]*)*\\.v[0-9]+$')
        invalid = [key for key in value if not pattern.match(key)]
        if invalid:
            raise ValueError(f'invalid extension namespace(s): {invalid}')
        return value


class MessageParticipant(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['Participant']
    schema_version: Literal['1.0.0']
    conversation_id: str = Field(min_length=1)
    entity_ref: ObjectRef | None = Field(default=None)
    external_identity_ref: ObjectRef | None = Field(default=None)
    role: Literal['sender', 'recipient', 'assignee', 'observer', 'system']
    status: Literal['active', 'left', 'blocked', 'provisional']
    joined_at: str | None = Field(default=None)
    left_at: str | None = Field(default=None)
    created_at: str
    updated_at: str
    version: int = Field(ge=1)
    extensions: dict[str, Any] | None = Field(default=None)

    @field_validator('extensions')
    @classmethod
    def _validate_extensions_property_names(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        pattern = re.compile('^[a-z][a-z0-9-]*(\\.[a-z][a-z0-9-]*)*\\.v[0-9]+$')
        invalid = [key for key in value if not pattern.match(key)]
        if invalid:
            raise ValueError(f'invalid extension namespace(s): {invalid}')
        return value


class QueueMessagePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    conversation_id: str = Field(min_length=1)
    sender_participant_ref: ObjectRef | None = Field(default=None)
    sender_actor_ref: ActorRef | None = Field(default=None)
    body: str
    body_format: Literal['plain', 'markdown', 'html']
    idempotency_key: str | None = Field(default=None)
    extensions: dict[str, Any] | None = Field(default=None)

    @field_validator('extensions')
    @classmethod
    def _validate_extensions_property_names(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        pattern = re.compile('^[a-z][a-z0-9-]*(\\.[a-z][a-z0-9-]*)*\\.v[0-9]+$')
        invalid = [key for key in value if not pattern.match(key)]
        if invalid:
            raise ValueError(f'invalid extension namespace(s): {invalid}')
        return value


class AvailabilityRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['Availability']
    schema_version: Literal['1.0.0']
    owner_ref: ObjectRef
    resource_ref: ObjectRef | None = Field(default=None)
    kind: Literal['available', 'unavailable']
    start_at: str
    end_at: str
    timezone: str = Field(min_length=1)
    capacity: int | None = Field(default=None, ge=0)
    recurrence_rule: RecurrenceRule | None = Field(default=None)
    status: Literal['active', 'archived']
    version: int = Field(ge=1)


class Calendar(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['Calendar']
    schema_version: Literal['1.0.0']
    name: str = Field(min_length=1)
    timezone: str = Field(min_length=1)
    status: Literal['active', 'archived']
    owner_ref: ObjectRef
    created_by: ActorRef
    created_at: str
    updated_at: str
    version: int = Field(ge=1)
    extensions: dict[str, Any] | None = Field(default=None)

    @field_validator('extensions')
    @classmethod
    def _validate_extensions_property_names(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        pattern = re.compile('^[a-z][a-z0-9-]*(\\.[a-z][a-z0-9-]*)*\\.v[0-9]+$')
        invalid = [key for key in value if not pattern.match(key)]
        if invalid:
            raise ValueError(f'invalid extension namespace(s): {invalid}')
        return value


class CalendarParticipant(BaseModel):
    model_config = ConfigDict(extra="forbid")
    participant_ref: ObjectRef
    role: Literal['organizer', 'required', 'optional', 'resource']
    status: Literal['invited', 'accepted', 'declined', 'tentative', 'no_response', 'canceled']
    responded_at: str | None = Field(default=None)


class Reservation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['Reservation']
    schema_version: Literal['1.0.0']
    calendar_ref: ObjectRef
    resource_ref: ObjectRef
    reserved_for_ref: ObjectRef
    status: Literal['held', 'confirmed', 'released', 'canceled', 'expired']
    start_at: str
    end_at: str
    timezone: str = Field(min_length=1)
    quantity: int = Field(ge=1)
    hold_expires_at: str | None = Field(default=None)
    created_at: str
    updated_at: str
    version: int = Field(ge=1)
    extensions: dict[str, Any] | None = Field(default=None)

    @field_validator('extensions')
    @classmethod
    def _validate_extensions_property_names(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        pattern = re.compile('^[a-z][a-z0-9-]*(\\.[a-z][a-z0-9-]*)*\\.v[0-9]+$')
        invalid = [key for key in value if not pattern.match(key)]
        if invalid:
            raise ValueError(f'invalid extension namespace(s): {invalid}')
        return value


class CreateRecordPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    database_id: str = Field(min_length=1)
    table_id: str = Field(min_length=1)
    values: list[FieldValue]
    extensions: dict[str, Any] | None = Field(default=None)

    @field_validator('extensions')
    @classmethod
    def _validate_extensions_property_names(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        pattern = re.compile('^[a-z][a-z0-9-]*(\\.[a-z][a-z0-9-]*)*\\.v[0-9]+$')
        invalid = [key for key in value if not pattern.match(key)]
        if invalid:
            raise ValueError(f'invalid extension namespace(s): {invalid}')
        return value


class Database(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['Database']
    schema_version: Literal['1.0.0']
    name: str = Field(min_length=1)
    description: str | None = Field(default=None)
    status: Literal['draft', 'active', 'locked', 'archived']
    owner_ref: ObjectRef
    authority_scope: dict[str, Any] | None = Field(default=None)
    created_by: ActorRef
    created_at: str
    updated_at: str
    version: int = Field(ge=1)
    extensions: dict[str, Any] | None = Field(default=None)

    @field_validator('extensions')
    @classmethod
    def _validate_extensions_property_names(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        pattern = re.compile('^[a-z][a-z0-9-]*(\\.[a-z][a-z0-9-]*)*\\.v[0-9]+$')
        invalid = [key for key in value if not pattern.match(key)]
        if invalid:
            raise ValueError(f'invalid extension namespace(s): {invalid}')
        return value


class FieldDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['FieldDefinition']
    schema_version: Literal['1.0.0']
    table_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    field_type: Literal['text', 'rich_text', 'number', 'boolean', 'date', 'datetime', 'select', 'multi_select', 'person_ref', 'organization_ref', 'relation', 'file_ref', 'url', 'email', 'phone', 'formula', 'rollup']
    required: bool
    unique: bool
    default_value: dict[str, Any] | None = Field(default=None)
    validation: dict[str, Any] | None = Field(default=None)
    options: list[str] | None = Field(default=None)
    relation_target: ObjectRef | None = Field(default=None)
    formula: dict[str, Any] | None = Field(default=None)
    position: int = Field(ge=0)
    status: Literal['active', 'archived']
    created_at: str
    updated_at: str
    version: int = Field(ge=1)


class DatabaseRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['Record']
    schema_version: Literal['1.0.0']
    database_id: str = Field(min_length=1)
    table_id: str = Field(min_length=1)
    record_version: int = Field(ge=1)
    values: list[FieldValue]
    status: Literal['active', 'archived', 'deleted']
    created_by: ActorRef
    created_at: str
    updated_at: str
    provenance: dict[str, Any] | None = Field(default=None)
    authority_scope: dict[str, Any] | None = Field(default=None)
    version: int = Field(ge=1)
    extensions: dict[str, Any] | None = Field(default=None)

    @field_validator('extensions')
    @classmethod
    def _validate_extensions_property_names(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        pattern = re.compile('^[a-z][a-z0-9-]*(\\.[a-z][a-z0-9-]*)*\\.v[0-9]+$')
        invalid = [key for key in value if not pattern.match(key)]
        if invalid:
            raise ValueError(f'invalid extension namespace(s): {invalid}')
        return value


class ViewDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['ViewDefinition']
    schema_version: Literal['1.0.0']
    database_id: str = Field(min_length=1)
    table_id: str | None = Field(default=None)
    name: str = Field(min_length=1)
    view_type: Literal['table', 'kanban', 'calendar', 'timeline', 'gallery', 'chart', 'form']
    filters: dict[str, Any] | None = Field(default=None)
    sorts: list[dict[str, Any]] | None = Field(default=None)
    grouping: dict[str, Any] | None = Field(default=None)
    visible_fields: list[str] | None = Field(default=None)
    layout: dict[str, Any] | None = Field(default=None)
    owner_ref: ObjectRef | None = Field(default=None)
    visibility: str | None = Field(default=None)
    created_at: str
    updated_at: str
    version: int = Field(ge=1)


class DocumentReviewRequestedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_ref: ObjectRef
    revision_id: str = Field(min_length=1)
    reviewer_ref: ActorRef


class Document(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['Document']
    schema_version: Literal['1.0.0']
    title: str = Field(min_length=1)
    status: Literal['draft', 'in_review', 'approved', 'published', 'archived']
    current_revision_id: str = Field(min_length=1)
    owner_ref: ObjectRef
    created_by: ActorRef
    created_at: str
    updated_at: str
    authority_scope: dict[str, Any] | None = Field(default=None)
    provenance: dict[str, Any] | None = Field(default=None)
    version: int = Field(ge=1)
    extensions: dict[str, Any] | None = Field(default=None)

    @field_validator('extensions')
    @classmethod
    def _validate_extensions_property_names(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        pattern = re.compile('^[a-z][a-z0-9-]*(\\.[a-z][a-z0-9-]*)*\\.v[0-9]+$')
        invalid = [key for key in value if not pattern.match(key)]
        if invalid:
            raise ValueError(f'invalid extension namespace(s): {invalid}')
        return value


class ReviewDecisionSubmittedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_ref: ObjectRef
    revision_id: str = Field(min_length=1)
    decision: Literal['approved', 'changes_requested', 'rejected', 'canceled']
    comments: str | None = Field(default=None)


class AuthorityContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    organizationId: str | None = Field(default=None, min_length=1)
    projectionId: str | None = Field(default=None, min_length=1)
    runtimeBinding: RuntimeBinding
    permissionSet: list[str] = Field(min_length=1)
    policyVersion: str = Field(min_length=1)
    approvalId: str | None = Field(default=None, min_length=1)


class CommandEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    commandId: str = Field(min_length=1)
    commandType: str = Field(pattern='^[A-Z][A-Za-z0-9]+\\.v[0-9]+$')
    contractVersion: str = Field(pattern='^1\\.[0-9]+\\.[0-9]+$')
    actor: ActorRef
    authorityContext: AuthorityContext
    target: ObjectRef | None
    payload: dict[str, Any]
    issuedAt: str
    idempotencyKey: str | None = Field(default=None, min_length=1)
    correlationId: str = Field(min_length=1)
    causationId: str | None = Field(default=None, min_length=1)
    expectedAggregateVersion: int | None = Field(default=None, ge=0)


class FoundationEvidenceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidenceId: str = Field(min_length=1)
    evidenceType: str | None = Field(default=None, min_length=1)
    sourceRuntime: RuntimeBinding
    objectRef: ObjectRef | None = Field(default=None)
    uri: str | None = Field(default=None, min_length=1)
    contentHash: str | None = Field(default=None, min_length=1)
    observedAt: str


class FileRegisteredPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    file: File


class FileRestoredPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    file: File


class FileTrashedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    file: File


class RestoreFilePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    file_ref: ObjectRef
    restore_to_status: Literal['ready', 'archived']
    reason: str = Field(min_length=1)
    evidence_refs: list[FoundationEvidenceRef] | None = Field(default=None)


class TrashFilePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    file_ref: ObjectRef
    reason: str = Field(min_length=1)
    evidence_refs: list[FoundationEvidenceRef] | None = Field(default=None)


class Invoice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['Invoice']
    schema_version: Literal['1.0.0']
    invoice_number: str = Field(min_length=1)
    status: Literal['draft', 'issued', 'paid', 'voided', 'overdue', 'written_off']
    bill_to_ref: ObjectRef
    currency: str = Field(pattern='^[A-Z]{3}$')
    total_amount: float = Field(ge=0)
    issued_at: str
    due_at: str
    transaction_ref: ObjectRef | None = Field(default=None)
    evidence_refs: list[FoundationEvidenceRef] | None = Field(default=None)
    version: int = Field(ge=1)
    extensions: dict[str, Any] | None = Field(default=None)

    @field_validator('extensions')
    @classmethod
    def _validate_extensions_property_names(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        pattern = re.compile('^[a-z][a-z0-9-]*(\\.[a-z][a-z0-9-]*)*\\.v[0-9]+$')
        invalid = [key for key in value if not pattern.match(key)]
        if invalid:
            raise ValueError(f'invalid extension namespace(s): {invalid}')
        return value


class IssueInvoicePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    invoice: Invoice
    evidence_refs: list[FoundationEvidenceRef] | None = Field(default=None)


class Statement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['Statement']
    schema_version: Literal['1.0.0']
    period_ref: ObjectRef
    statement_type: Literal['balance', 'cash_flow', 'income_expense', 'budget', 'forecast']
    currency: str = Field(pattern='^[A-Z]{3}$')
    generated_at: str
    evidence_refs: list[FoundationEvidenceRef]
    version: int = Field(ge=1)


class TransactionLine(BaseModel):
    model_config = ConfigDict(extra="forbid")
    line_id: str = Field(min_length=1)
    account_ref: ObjectRef
    amount: float
    currency: str = Field(pattern='^[A-Z]{3}$')
    line_type: Literal['debit', 'credit']
    classification: Literal['income', 'expense', 'asset', 'liability', 'equity', 'payout', 'allocation'] | None = Field(default=None)
    memo: str | None = Field(default=None)
    evidence_refs: list[FoundationEvidenceRef] | None = Field(default=None)


class Transaction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['Transaction']
    schema_version: Literal['1.0.0']
    transaction_date: str
    status: Literal['draft', 'posted', 'voided', 'reversed', 'adjusted']
    currency: str = Field(pattern='^[A-Z]{3}$')
    lines: list[TransactionLine] = Field(min_length=2)
    correction_of_ref: ObjectRef | None = Field(default=None)
    correction_type: Literal['reversal', 'adjustment', 'correcting_entry'] | None = Field(default=None)
    memo: str | None = Field(default=None)
    created_by: ActorRef
    created_at: str
    updated_at: str
    posted_at: str | None = Field(default=None)
    evidence_refs: list[FoundationEvidenceRef] | None = Field(default=None)
    version: int = Field(ge=1)
    extensions: dict[str, Any] | None = Field(default=None)

    @field_validator('extensions')
    @classmethod
    def _validate_extensions_property_names(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        pattern = re.compile('^[a-z][a-z0-9-]*(\\.[a-z][a-z0-9-]*)*\\.v[0-9]+$')
        invalid = [key for key in value if not pattern.match(key)]
        if invalid:
            raise ValueError(f'invalid extension namespace(s): {invalid}')
        return value


class FormSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['FormSubmission']
    schema_version: Literal['1.0.0']
    form_ref: ObjectRef
    form_version: int = Field(ge=1)
    submitter_ref: ObjectRef | None = Field(default=None)
    values: list[SubmissionValue]
    validation_status: Literal['accepted', 'accepted_with_warnings', 'rejected']
    validation_errors: list[str] | None = Field(default=None)
    destination_record_ref: ObjectRef | None = Field(default=None)
    submitted_at: str
    evidence_refs: list[FoundationEvidenceRef] | None = Field(default=None)
    version: int = Field(ge=1)
    extensions: dict[str, Any] | None = Field(default=None)

    @field_validator('extensions')
    @classmethod
    def _validate_extensions_property_names(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        pattern = re.compile('^[a-z][a-z0-9-]*(\\.[a-z][a-z0-9-]*)*\\.v[0-9]+$')
        invalid = [key for key in value if not pattern.match(key)]
        if invalid:
            raise ValueError(f'invalid extension namespace(s): {invalid}')
        return value


class FormSubmittedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    submission: FormSubmission


class SubmitFormPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    form_ref: ObjectRef
    form_version: int = Field(ge=1)
    submitter_ref: ObjectRef | None = Field(default=None)
    values: list[SubmissionValue]
    evidence_refs: list[FoundationEvidenceRef] | None = Field(default=None)
    extensions: dict[str, Any] | None = Field(default=None)

    @field_validator('extensions')
    @classmethod
    def _validate_extensions_property_names(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        pattern = re.compile('^[a-z][a-z0-9-]*(\\.[a-z][a-z0-9-]*)*\\.v[0-9]+$')
        invalid = [key for key in value if not pattern.match(key)]
        if invalid:
            raise ValueError(f'invalid extension namespace(s): {invalid}')
        return value


class Consent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['Consent']
    schema_version: Literal['1.0.0']
    subject_ref: ObjectRef
    scope: str = Field(min_length=1)
    channel: str | None = Field(default=None)
    purpose: str | None = Field(default=None)
    state: Literal['granted', 'denied', 'revoked', 'expired']
    basis: str | None = Field(default=None)
    captured_at: str
    expires_at: str | None = Field(default=None)
    revoked_at: str | None = Field(default=None)
    source: str = Field(min_length=1)
    evidence_refs: list[FoundationEvidenceRef] | None = Field(default=None)
    created_at: str
    updated_at: str
    version: int = Field(ge=1)
    extensions: dict[str, Any] | None = Field(default=None)

    @field_validator('extensions')
    @classmethod
    def _validate_extensions_property_names(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        pattern = re.compile('^[a-z][a-z0-9-]*(\\.[a-z][a-z0-9-]*)*\\.v[0-9]+$')
        invalid = [key for key in value if not pattern.match(key)]
        if invalid:
            raise ValueError(f'invalid extension namespace(s): {invalid}')
        return value


class Interaction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['Interaction']
    schema_version: Literal['1.0.0']
    relationship_id: str = Field(min_length=1)
    interaction_type: str = Field(min_length=1)
    occurred_at: str
    direction: Literal['inbound', 'outbound', 'internal', 'unknown'] | None = Field(default=None)
    channel: str | None = Field(default=None)
    summary: str | None = Field(default=None)
    source_object_refs: list[ObjectRef] | None = Field(default=None)
    actor_ref: ActorRef | None = Field(default=None)
    evidence_refs: list[FoundationEvidenceRef] | None = Field(default=None)
    created_at: str
    version: int = Field(ge=1)
    extensions: dict[str, Any] | None = Field(default=None)

    @field_validator('extensions')
    @classmethod
    def _validate_extensions_property_names(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        pattern = re.compile('^[a-z][a-z0-9-]*(\\.[a-z][a-z0-9-]*)*\\.v[0-9]+$')
        invalid = [key for key in value if not pattern.match(key)]
        if invalid:
            raise ValueError(f'invalid extension namespace(s): {invalid}')
        return value


class PersonCreatedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    person: Person


class RecordInteractionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    relationship_id: str = Field(min_length=1)
    interaction_type: str = Field(min_length=1)
    occurred_at: str
    direction: Literal['inbound', 'outbound', 'internal', 'unknown'] | None = Field(default=None)
    channel: str | None = Field(default=None)
    summary: str | None = Field(default=None)
    source_object_refs: list[ObjectRef] | None = Field(default=None)
    actor_ref: ActorRef | None = Field(default=None)
    evidence_refs: list[FoundationEvidenceRef] | None = Field(default=None)
    extensions: dict[str, Any] | None = Field(default=None)

    @field_validator('extensions')
    @classmethod
    def _validate_extensions_property_names(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        pattern = re.compile('^[a-z][a-z0-9-]*(\\.[a-z][a-z0-9-]*)*\\.v[0-9]+$')
        invalid = [key for key in value if not pattern.match(key)]
        if invalid:
            raise ValueError(f'invalid extension namespace(s): {invalid}')
        return value


class RelationshipCreatedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    relationship: Relationship


class DeliveryReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['DeliveryReceipt']
    schema_version: Literal['1.0.0']
    message_id: str = Field(min_length=1)
    delivery_attempt_id: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    state: Literal['queued', 'accepted', 'sent', 'delivered', 'read', 'failed', 'bounced', 'rejected']
    occurred_at: str
    provider_receipt_id: str | None = Field(default=None)
    failure_code: str | None = Field(default=None)
    failure_detail: str | None = Field(default=None)
    evidence_refs: list[FoundationEvidenceRef] | None = Field(default=None)
    version: int = Field(ge=1)


class MessageQueuedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: Message


class CreateReservationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    calendar_ref: ObjectRef
    resource_ref: ObjectRef
    reserved_for_ref: ObjectRef
    start_at: str
    end_at: str
    timezone: str = Field(min_length=1)
    quantity: int = Field(ge=1)
    hold_expires_at: str | None = Field(default=None)
    evidence_refs: list[FoundationEvidenceRef] | None = Field(default=None)
    extensions: dict[str, Any] | None = Field(default=None)

    @field_validator('extensions')
    @classmethod
    def _validate_extensions_property_names(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        pattern = re.compile('^[a-z][a-z0-9-]*(\\.[a-z][a-z0-9-]*)*\\.v[0-9]+$')
        invalid = [key for key in value if not pattern.match(key)]
        if invalid:
            raise ValueError(f'invalid extension namespace(s): {invalid}')
        return value


class CalendarEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['Event']
    schema_version: Literal['1.0.0']
    calendar_ref: ObjectRef
    title: str = Field(min_length=1)
    status: Literal['tentative', 'confirmed', 'canceled']
    start_at: str
    end_at: str
    timezone: str = Field(min_length=1)
    participants: list[CalendarParticipant]
    recurrence_rule: RecurrenceRule | None = Field(default=None)
    reservation_ref: ObjectRef | None = Field(default=None)
    created_at: str
    updated_at: str
    version: int = Field(ge=1)
    extensions: dict[str, Any] | None = Field(default=None)

    @field_validator('extensions')
    @classmethod
    def _validate_extensions_property_names(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        pattern = re.compile('^[a-z][a-z0-9-]*(\\.[a-z][a-z0-9-]*)*\\.v[0-9]+$')
        invalid = [key for key in value if not pattern.match(key)]
        if invalid:
            raise ValueError(f'invalid extension namespace(s): {invalid}')
        return value


class ReservationCreatedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reservation: Reservation


class CreateDatabasePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1)
    description: str | None = Field(default=None)
    owner_ref: ObjectRef
    initial_fields: list[FieldDefinition] | None = Field(default=None)
    extensions: dict[str, Any] | None = Field(default=None)

    @field_validator('extensions')
    @classmethod
    def _validate_extensions_property_names(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        pattern = re.compile('^[a-z][a-z0-9-]*(\\.[a-z][a-z0-9-]*)*\\.v[0-9]+$')
        invalid = [key for key in value if not pattern.match(key)]
        if invalid:
            raise ValueError(f'invalid extension namespace(s): {invalid}')
        return value


class DatabaseCreatedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    database: Database


class RecordCreatedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    record: DatabaseRecord


class DocumentReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['DocumentReviewRequest']
    schema_version: Literal['1.0.0']
    document_id: str = Field(min_length=1)
    revision_id: str = Field(min_length=1)
    reviewer_ref: ActorRef
    status: Literal['requested', 'canceled', 'decision_submitted']
    requested_at: str
    completed_at: str | None = Field(default=None)
    comments: str | None = Field(default=None)
    evidence_refs: list[FoundationEvidenceRef] | None = Field(default=None)
    version: int = Field(ge=1)


class DocumentRevision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['DocumentRevision']
    schema_version: Literal['1.0.0']
    document_id: str = Field(min_length=1)
    revision_number: int = Field(ge=1)
    content: dict[str, Any]
    content_format: Literal['markdown', 'rich_text', 'plain_text', 'structured_json']
    created_by: ActorRef
    created_at: str
    change_summary: str | None = Field(default=None)
    base_revision_id: str | None = Field(default=None)
    supersedes_revision_id: str | None = Field(default=None)
    evidence_refs: list[FoundationEvidenceRef] | None = Field(default=None)
    version: int = Field(ge=1)


class PublicationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['PublicationRecord']
    schema_version: Literal['1.0.0']
    document_id: str = Field(min_length=1)
    revision_id: str = Field(min_length=1)
    status: Literal['published', 'revoked', 'superseded']
    published_by: ActorRef
    published_at: str
    evidence_refs: list[FoundationEvidenceRef] | None = Field(default=None)
    version: int = Field(ge=1)


class RequestDocumentReviewPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_ref: ObjectRef
    revision_id: str = Field(min_length=1)
    reviewer_ref: ActorRef
    instructions: str | None = Field(default=None)
    evidence_refs: list[FoundationEvidenceRef] | None = Field(default=None)


class ReviewDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    objectType: Literal['ReviewDecision']
    schema_version: Literal['1.0.0']
    review_request_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    revision_id: str = Field(min_length=1)
    reviewer_ref: ActorRef
    decision: Literal['approved', 'changes_requested', 'rejected', 'canceled']
    comments: str | None = Field(default=None)
    decided_at: str
    evidence_refs: list[FoundationEvidenceRef] | None = Field(default=None)
    version: int = Field(ge=1)


class SubmitReviewDecisionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_ref: ObjectRef
    revision_id: str = Field(min_length=1)
    decision: Literal['approved', 'changes_requested', 'rejected', 'canceled']
    comments: str | None = Field(default=None)
    evidence_refs: list[FoundationEvidenceRef] | None = Field(default=None)


class EventEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    eventId: str = Field(min_length=1)
    eventType: str = Field(pattern='^[A-Z][A-Za-z0-9]+\\.v[0-9]+$')
    contractVersion: str = Field(pattern='^1\\.[0-9]+\\.[0-9]+$')
    aggregate: ObjectRef
    aggregateVersion: int = Field(ge=1)
    actor: ActorRef
    authorityContext: AuthorityContext
    occurredAt: str
    sourceRuntime: RuntimeBinding
    correlationId: str = Field(min_length=1)
    causationId: str = Field(min_length=1)
    evidenceRefs: list[FoundationEvidenceRef]
    payload: dict[str, Any]


class InvoiceIssuedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    invoice: Invoice


class PostTransactionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transaction: Transaction
    evidence_refs: list[FoundationEvidenceRef] | None = Field(default=None)
    extensions: dict[str, Any] | None = Field(default=None)

    @field_validator('extensions')
    @classmethod
    def _validate_extensions_property_names(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        pattern = re.compile('^[a-z][a-z0-9-]*(\\.[a-z][a-z0-9-]*)*\\.v[0-9]+$')
        invalid = [key for key in value if not pattern.match(key)]
        if invalid:
            raise ValueError(f'invalid extension namespace(s): {invalid}')
        return value


class TransactionPostedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transaction: Transaction


class InteractionRecordedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    interaction: Interaction


__all__ = ['RecurrenceRule', 'CalendarResource', 'FieldValue', 'Table', 'ActorRef', 'ObjectRef', 'RuntimeBinding', 'File', 'RegisterFilePayload', 'FinancialAccount', 'Allocation', 'FinancialPeriod', 'FormDestinationBinding', 'FormField', 'Form', 'SubmissionValue', 'ContactPoint', 'CreatePersonPayload', 'CreateRelationshipPayload', 'ExternalIdentity', 'Facet', 'FollowUp', 'Opportunity', 'Organization', 'Person', 'Pipeline', 'Relationship', 'Stage', 'Assignment', 'MessageAttachment', 'ChannelBinding', 'Conversation', 'InternalNote', 'Message', 'MessageParticipant', 'QueueMessagePayload', 'AvailabilityRule', 'Calendar', 'CalendarParticipant', 'Reservation', 'CreateRecordPayload', 'Database', 'FieldDefinition', 'DatabaseRecord', 'ViewDefinition', 'DocumentReviewRequestedPayload', 'Document', 'ReviewDecisionSubmittedPayload', 'AuthorityContext', 'CommandEnvelope', 'FoundationEvidenceRef', 'FileRegisteredPayload', 'FileRestoredPayload', 'FileTrashedPayload', 'RestoreFilePayload', 'TrashFilePayload', 'Invoice', 'IssueInvoicePayload', 'Statement', 'TransactionLine', 'Transaction', 'FormSubmission', 'FormSubmittedPayload', 'SubmitFormPayload', 'Consent', 'Interaction', 'PersonCreatedPayload', 'RecordInteractionPayload', 'RelationshipCreatedPayload', 'DeliveryReceipt', 'MessageQueuedPayload', 'CreateReservationPayload', 'CalendarEvent', 'ReservationCreatedPayload', 'CreateDatabasePayload', 'DatabaseCreatedPayload', 'RecordCreatedPayload', 'DocumentReviewRequest', 'DocumentRevision', 'PublicationRecord', 'RequestDocumentReviewPayload', 'ReviewDecision', 'SubmitReviewDecisionPayload', 'EventEnvelope', 'InvoiceIssuedPayload', 'PostTransactionPayload', 'TransactionPostedPayload', 'InteractionRecordedPayload']
