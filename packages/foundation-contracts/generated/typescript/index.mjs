// Generated foundation contract Zod schemas. Do not hand-edit.
import { z } from 'zod';

export const RecurrenceRuleSchema = z.object({
  "frequency": z.enum(["daily", "weekly", "monthly", "yearly"]),
  "interval": z.number().int().min(1),
  "count": z.number().int().min(1).optional(),
  "until_at": z.string().datetime().optional(),
  "by_weekday": z.array(z.enum(["MO", "TU", "WE", "TH", "FR", "SA", "SU"])).optional(),
  "exceptions": z.array(z.string().datetime()).optional(),
}).strict();

export const CalendarResourceSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("Resource"),
  "schema_version": z.literal("1.0.0"),
  "name": z.string().min(1),
  "resource_type": z.enum(["person", "room", "equipment", "service", "pool"]),
  "capacity": z.number().int().min(1),
  "status": z.enum(["active", "unavailable", "archived"]),
  "created_at": z.string().datetime(),
  "updated_at": z.string().datetime(),
  "version": z.number().int().min(1),
  "extensions": z.record(z.string(), z.unknown()).refine((value) => Object.keys(value).every((key) => /^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)*\.v[0-9]+$/.test(key)), { message: 'invalid extension namespace' }).optional(),
}).strict();

export const FieldValueSchema = z.object({
  "field_id": z.string().min(1),
  "field_type": z.enum(["text", "rich_text", "number", "boolean", "date", "datetime", "select", "multi_select", "person_ref", "organization_ref", "relation", "file_ref", "url", "email", "phone", "formula", "rollup"]),
  "value": z.union([z.string(), z.number(), z.boolean(), z.array(z.string()), z.record(z.string(), z.unknown()), z.null()]),
}).strict();

export const TableSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("Table"),
  "schema_version": z.literal("1.0.0"),
  "database_id": z.string().min(1),
  "name": z.string().min(1),
  "status": z.enum(["active", "archived"]),
  "created_at": z.string().datetime(),
  "updated_at": z.string().datetime(),
  "version": z.number().int().min(1),
}).strict();

export const ActorRefSchema = z.object({
  "actorType": z.enum(["human", "agent", "service", "system"]),
  "actorId": z.string().min(1),
  "roleId": z.string().min(1).optional(),
  "delegatedBy": z.lazy(() => ActorRefSchema).optional(),
}).strict();

export const ObjectRefSchema = z.object({
  "objectType": z.string().min(1),
  "objectId": z.string().min(1),
  "version": z.number().int().min(0).optional(),
}).strict();

export const RuntimeBindingSchema = z.object({
  "runtimeId": z.string().min(1),
  "runtimeKind": z.enum(["umh-native", "projection-local", "connected-federated", "adapter"]),
  "projectionId": z.string().min(1).optional(),
  "serviceName": z.string().min(1).optional(),
  "contractVersion": z.string().regex(/^1\.[0-9]+\.[0-9]+$/),
}).strict();

export const FileSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("File"),
  "schema_version": z.literal("1.0.0"),
  "name": z.string().min(1),
  "kind": z.string().min(1),
  "mime_type": z.string().optional(),
  "size_bytes": z.number().int().min(0).optional(),
  "status": z.enum(["uploading", "processing", "ready", "quarantined", "archived", "trashed", "deleted"]),
  "storage_binding": z.record(z.string(), z.unknown()),
  "owner_ref": ObjectRefSchema,
  "created_by": ActorRefSchema,
  "created_at": z.string().datetime(),
  "updated_at": z.string().datetime(),
  "current_version_id": z.string().optional(),
  "visibility": z.string().optional(),
  "authority_scope": z.record(z.string(), z.unknown()).optional(),
  "provenance": z.record(z.string(), z.unknown()).optional(),
  "version": z.number().int().min(1),
  "extensions": z.record(z.string(), z.unknown()).refine((value) => Object.keys(value).every((key) => /^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)*\.v[0-9]+$/.test(key)), { message: 'invalid extension namespace' }).optional(),
}).strict();

export const RegisterFilePayloadSchema = z.object({
  "name": z.string().min(1),
  "kind": z.string().min(1),
  "mime_type": z.string().optional(),
  "size_bytes": z.number().int().min(0).optional(),
  "storage_binding": z.record(z.string(), z.unknown()),
  "owner_ref": ObjectRefSchema,
  "extensions": z.record(z.string(), z.unknown()).refine((value) => Object.keys(value).every((key) => /^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)*\.v[0-9]+$/.test(key)), { message: 'invalid extension namespace' }).optional(),
}).strict();

export const FinancialAccountSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("Account"),
  "schema_version": z.literal("1.0.0"),
  "name": z.string().min(1),
  "account_type": z.enum(["asset", "liability", "equity", "income", "expense"]),
  "currency": z.string().regex(/^[A-Z]{3}$/),
  "status": z.enum(["active", "closed", "archived"]),
  "owner_ref": ObjectRefSchema,
  "created_at": z.string().datetime(),
  "updated_at": z.string().datetime(),
  "version": z.number().int().min(1),
  "extensions": z.record(z.string(), z.unknown()).refine((value) => Object.keys(value).every((key) => /^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)*\.v[0-9]+$/.test(key)), { message: 'invalid extension namespace' }).optional(),
}).strict();

export const AllocationSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("Allocation"),
  "schema_version": z.literal("1.0.0"),
  "source_transaction_ref": ObjectRefSchema,
  "allocation_target_ref": ObjectRefSchema,
  "amount": z.number(),
  "currency": z.string().regex(/^[A-Z]{3}$/),
  "status": z.enum(["active", "reversed"]),
  "created_at": z.string().datetime(),
  "version": z.number().int().min(1),
}).strict();

export const FinancialPeriodSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("FinancialPeriod"),
  "schema_version": z.literal("1.0.0"),
  "name": z.string().min(1),
  "start_at": z.string().datetime(),
  "end_at": z.string().datetime(),
  "status": z.enum(["open", "closed", "locked"]),
  "version": z.number().int().min(1),
}).strict();

export const FormDestinationBindingSchema = z.object({
  "binding_type": z.enum(["database_table", "webhook", "none"]),
  "target_ref": ObjectRefSchema,
  "field_mappings": z.array(z.record(z.string(), z.unknown())),
}).strict();

export const FormFieldSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("FormField"),
  "schema_version": z.literal("1.0.0"),
  "form_id": z.string().min(1),
  "form_version": z.number().int().min(1),
  "label": z.string().min(1),
  "field_type": z.enum(["text", "long_text", "number", "boolean", "date", "datetime", "select", "multi_select", "email", "phone", "url", "file_ref", "consent_ack", "hidden"]),
  "required": z.boolean(),
  "validation_rules": z.record(z.string(), z.unknown()).optional(),
  "options": z.array(z.string()).optional(),
  "destination_field_id": z.string().optional(),
  "position": z.number().int().min(0),
  "status": z.enum(["active", "removed"]),
}).strict();

export const FormSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("Form"),
  "schema_version": z.literal("1.0.0"),
  "name": z.string().min(1),
  "description": z.string().optional(),
  "status": z.enum(["draft", "published", "closed", "archived"]),
  "current_version": z.number().int().min(1),
  "fields": z.array(FormFieldSchema),
  "destination_binding": FormDestinationBindingSchema.optional(),
  "privacy_policy_ref": ObjectRefSchema.optional(),
  "owner_ref": ObjectRefSchema,
  "created_by": ActorRefSchema,
  "created_at": z.string().datetime(),
  "updated_at": z.string().datetime(),
  "version": z.number().int().min(1),
  "extensions": z.record(z.string(), z.unknown()).refine((value) => Object.keys(value).every((key) => /^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)*\.v[0-9]+$/.test(key)), { message: 'invalid extension namespace' }).optional(),
}).strict();

export const SubmissionValueSchema = z.object({
  "field_id": z.string().min(1),
  "field_type": z.enum(["text", "long_text", "number", "boolean", "date", "datetime", "select", "multi_select", "email", "phone", "url", "file_ref", "consent_ack", "hidden"]),
  "value": z.union([z.string(), z.number(), z.boolean(), z.array(z.string()), z.record(z.string(), z.unknown()), z.null()]),
}).strict();

export const ContactPointSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("ContactPoint"),
  "schema_version": z.literal("1.0.0"),
  "owner_ref": ObjectRefSchema,
  "kind": z.enum(["email", "phone", "social", "messaging-address", "website"]),
  "value": z.string().min(1),
  "label": z.string().optional(),
  "is_primary": z.boolean().optional(),
  "verification_state": z.enum(["unverified", "pending", "verified", "failed"]),
  "consent_ref": ObjectRefSchema.optional(),
  "provenance": z.record(z.string(), z.unknown()),
  "created_at": z.string().datetime(),
  "updated_at": z.string().datetime(),
  "version": z.number().int().min(1),
  "extensions": z.record(z.string(), z.unknown()).refine((value) => Object.keys(value).every((key) => /^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)*\.v[0-9]+$/.test(key)), { message: 'invalid extension namespace' }).optional(),
}).strict();

export const CreatePersonPayloadSchema = z.object({
  "display_name": z.string().min(1),
  "given_name": z.string().optional(),
  "family_name": z.string().optional(),
  "preferred_name": z.string().optional(),
  "locale": z.string().optional(),
  "timezone": z.string().optional(),
  "extensions": z.record(z.string(), z.unknown()).refine((value) => Object.keys(value).every((key) => /^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)*\.v[0-9]+$/.test(key)), { message: 'invalid extension namespace' }).optional(),
}).strict();

export const CreateRelationshipPayloadSchema = z.object({
  "subject_ref": ObjectRefSchema,
  "object_ref": ObjectRefSchema,
  "relationship_class": z.string().min(1),
  "lifecycle_stage": z.string().optional(),
  "owner_actor_ref": ActorRefSchema.optional(),
  "source": z.string().min(1),
  "started_at": z.string().datetime().optional(),
  "extensions": z.record(z.string(), z.unknown()).refine((value) => Object.keys(value).every((key) => /^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)*\.v[0-9]+$/.test(key)), { message: 'invalid extension namespace' }).optional(),
}).strict();

export const ExternalIdentitySchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("ExternalIdentity"),
  "schema_version": z.literal("1.0.0"),
  "owner_ref": ObjectRefSchema,
  "provider": z.string().min(1),
  "provider_subject_id": z.string().min(1),
  "handle": z.string().optional(),
  "profile_url": z.string().optional(),
  "status": z.enum(["active", "unverified", "revoked", "archived"]),
  "verified_at": z.string().datetime().optional(),
  "created_at": z.string().datetime(),
  "updated_at": z.string().datetime(),
  "version": z.number().int().min(1),
  "extensions": z.record(z.string(), z.unknown()).refine((value) => Object.keys(value).every((key) => /^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)*\.v[0-9]+$/.test(key)), { message: 'invalid extension namespace' }).optional(),
}).strict();

export const FacetSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("Facet"),
  "schema_version": z.literal("1.0.0"),
  "relationship_id": z.string().min(1),
  "facet_key": z.enum(["customer", "prospect", "employee", "candidate", "vendor", "investor", "audience", "sponsor", "affiliate", "collaborator", "friend", "family", "mentor"]),
  "status": z.enum(["active", "inactive", "archived"]),
  "effective_from": z.string().datetime().optional(),
  "effective_to": z.string().datetime().optional(),
  "projection_namespace": z.string().optional(),
  "metadata": z.record(z.string(), z.unknown()).optional(),
  "created_at": z.string().datetime(),
  "updated_at": z.string().datetime(),
  "version": z.number().int().min(1),
  "extensions": z.record(z.string(), z.unknown()).refine((value) => Object.keys(value).every((key) => /^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)*\.v[0-9]+$/.test(key)), { message: 'invalid extension namespace' }).optional(),
}).strict();

export const FollowUpSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("FollowUp"),
  "schema_version": z.literal("1.0.0"),
  "relationship_id": z.string().min(1),
  "opportunity_id": z.string().optional(),
  "task_ref": ObjectRefSchema.optional(),
  "due_at": z.string().datetime(),
  "status": z.enum(["open", "completed", "canceled"]),
  "owner_actor_ref": ActorRefSchema,
  "reason": z.string().optional(),
  "created_at": z.string().datetime(),
  "updated_at": z.string().datetime(),
  "version": z.number().int().min(1),
}).strict();

export const OpportunitySchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("Opportunity"),
  "schema_version": z.literal("1.0.0"),
  "relationship_id": z.string().min(1),
  "pipeline_id": z.string().min(1),
  "stage_id": z.string().min(1),
  "name": z.string().min(1),
  "status": z.enum(["open", "won", "lost", "canceled"]),
  "amount": z.number().optional(),
  "currency": z.string().regex(/^[A-Z]{3}$/).optional(),
  "probability": z.number().min(0).max(1).optional(),
  "expected_close_at": z.string().datetime().optional(),
  "owner_actor_ref": ActorRefSchema.optional(),
  "source": z.string().min(1),
  "created_at": z.string().datetime(),
  "updated_at": z.string().datetime(),
  "version": z.number().int().min(1),
  "extensions": z.record(z.string(), z.unknown()).refine((value) => Object.keys(value).every((key) => /^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)*\.v[0-9]+$/.test(key)), { message: 'invalid extension namespace' }).optional(),
}).strict();

export const OrganizationSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("Organization"),
  "schema_version": z.literal("1.0.0"),
  "display_name": z.string().min(1),
  "status": z.enum(["active", "archived", "merged"]),
  "legal_name": z.string().optional(),
  "organization_kind": z.string().optional(),
  "website": z.string().optional(),
  "locale": z.string().optional(),
  "timezone": z.string().optional(),
  "created_at": z.string().datetime(),
  "updated_at": z.string().datetime(),
  "version": z.number().int().min(1),
  "extensions": z.record(z.string(), z.unknown()).refine((value) => Object.keys(value).every((key) => /^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)*\.v[0-9]+$/.test(key)), { message: 'invalid extension namespace' }).optional(),
}).strict();

export const PersonSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("Person"),
  "schema_version": z.literal("1.0.0"),
  "display_name": z.string().min(1),
  "status": z.enum(["active", "archived", "merged"]),
  "given_name": z.string().optional(),
  "family_name": z.string().optional(),
  "preferred_name": z.string().optional(),
  "locale": z.string().optional(),
  "timezone": z.string().optional(),
  "avatar_file_id": z.string().optional(),
  "created_at": z.string().datetime(),
  "updated_at": z.string().datetime(),
  "version": z.number().int().min(1),
  "extensions": z.record(z.string(), z.unknown()).refine((value) => Object.keys(value).every((key) => /^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)*\.v[0-9]+$/.test(key)), { message: 'invalid extension namespace' }).optional(),
}).strict();

export const PipelineSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("Pipeline"),
  "schema_version": z.literal("1.0.0"),
  "name": z.string().min(1),
  "status": z.enum(["active", "archived"]),
  "projection_namespace": z.string().optional(),
  "created_at": z.string().datetime(),
  "updated_at": z.string().datetime(),
  "version": z.number().int().min(1),
}).strict();

export const RelationshipSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("Relationship"),
  "schema_version": z.literal("1.0.0"),
  "subject_ref": ObjectRefSchema,
  "object_ref": ObjectRefSchema,
  "relationship_class": z.string().min(1),
  "lifecycle_stage": z.string().optional(),
  "status": z.enum(["active", "blocked", "archived"]),
  "owner_actor_ref": ActorRefSchema.optional(),
  "source": z.string().min(1),
  "started_at": z.string().datetime().optional(),
  "ended_at": z.string().datetime().optional(),
  "created_at": z.string().datetime(),
  "updated_at": z.string().datetime(),
  "version": z.number().int().min(1),
  "extensions": z.record(z.string(), z.unknown()).refine((value) => Object.keys(value).every((key) => /^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)*\.v[0-9]+$/.test(key)), { message: 'invalid extension namespace' }).optional(),
}).strict();

export const StageSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("Stage"),
  "schema_version": z.literal("1.0.0"),
  "pipeline_id": z.string().min(1),
  "name": z.string().min(1),
  "ordinal": z.number().int().min(0),
  "terminal_kind": z.enum(["none", "won", "lost"]),
  "entry_policy": z.record(z.string(), z.unknown()).optional(),
  "exit_policy": z.record(z.string(), z.unknown()).optional(),
  "created_at": z.string().datetime(),
  "updated_at": z.string().datetime(),
  "version": z.number().int().min(1),
}).strict();

export const AssignmentSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("Assignment"),
  "schema_version": z.literal("1.0.0"),
  "conversation_id": z.string().min(1),
  "actor_ref": ActorRefSchema,
  "queue": z.string().optional(),
  "status": z.enum(["active", "released"]),
  "assigned_at": z.string().datetime(),
  "released_at": z.string().datetime().optional(),
  "created_at": z.string().datetime(),
  "updated_at": z.string().datetime(),
  "version": z.number().int().min(1),
}).strict();

export const MessageAttachmentSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("Attachment"),
  "schema_version": z.literal("1.0.0"),
  "message_id": z.string().min(1),
  "file_ref": ObjectRefSchema.optional(),
  "external_media_id": z.string().optional(),
  "attachment_kind": z.string().min(1),
  "filename": z.string().optional(),
  "mime_type": z.string().optional(),
  "size_bytes": z.number().int().min(0).optional(),
  "duration_ms": z.number().int().min(0).optional(),
  "provider_metadata": z.record(z.string(), z.unknown()).optional(),
  "created_at": z.string().datetime(),
  "version": z.number().int().min(1),
}).strict();

export const ChannelBindingSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("ChannelBinding"),
  "schema_version": z.literal("1.0.0"),
  "provider": z.string().min(1),
  "connection_ref": ObjectRefSchema,
  "channel_kind": z.enum(["native", "email", "sms", "whatsapp", "instagram", "messenger", "x", "other"]),
  "external_thread_id": z.string().optional(),
  "status": z.enum(["pending", "active", "disabled", "revoked", "error"]),
  "capabilities": z.array(z.string().min(1)).min(1),
  "created_at": z.string().datetime(),
  "updated_at": z.string().datetime(),
  "version": z.number().int().min(1),
  "extensions": z.record(z.string(), z.unknown()).refine((value) => Object.keys(value).every((key) => /^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)*\.v[0-9]+$/.test(key)), { message: 'invalid extension namespace' }).optional(),
}).strict();

export const ConversationSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("Conversation"),
  "schema_version": z.literal("1.0.0"),
  "relationship_refs": z.array(ObjectRefSchema).optional(),
  "participant_refs": z.array(ObjectRefSchema).optional(),
  "status": z.enum(["open", "pending", "snoozed", "closed", "spam"]),
  "priority": z.enum(["low", "normal", "high", "urgent"]),
  "queue": z.string().optional(),
  "assigned_actor_ref": ActorRefSchema.optional(),
  "subject": z.string().optional(),
  "channel_binding_refs": z.array(ObjectRefSchema).optional(),
  "snoozed_until": z.string().datetime().optional(),
  "last_message_at": z.string().datetime().optional(),
  "ai_mode": z.enum(["observe", "suggest", "approval", "delegated"]),
  "created_at": z.string().datetime(),
  "updated_at": z.string().datetime(),
  "version": z.number().int().min(1),
  "extensions": z.record(z.string(), z.unknown()).refine((value) => Object.keys(value).every((key) => /^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)*\.v[0-9]+$/.test(key)), { message: 'invalid extension namespace' }).optional(),
}).strict();

export const InternalNoteSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("InternalNote"),
  "schema_version": z.literal("1.0.0"),
  "conversation_id": z.string().min(1),
  "body": z.string().min(1),
  "author_actor_ref": ActorRefSchema,
  "visibility": z.enum(["private", "team", "organization"]),
  "created_at": z.string().datetime(),
  "updated_at": z.string().datetime(),
  "version": z.number().int().min(1),
}).strict();

export const MessageSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("Message"),
  "schema_version": z.literal("1.0.0"),
  "conversation_id": z.string().min(1),
  "sender_participant_ref": ObjectRefSchema.optional(),
  "sender_actor_ref": ActorRefSchema.optional(),
  "direction": z.enum(["inbound", "outbound", "internal"]),
  "body": z.string(),
  "body_format": z.enum(["plain", "markdown", "html"]),
  "status": z.enum(["draft", "queued", "sent", "delivered", "read", "failed", "bounced", "rejected", "received"]),
  "reply_to_message_id": z.string().optional(),
  "provider_message_id": z.string().optional(),
  "idempotency_key": z.string().optional(),
  "sent_at": z.string().datetime().optional(),
  "received_at": z.string().datetime().optional(),
  "created_at": z.string().datetime(),
  "updated_at": z.string().datetime(),
  "version": z.number().int().min(1),
  "extensions": z.record(z.string(), z.unknown()).refine((value) => Object.keys(value).every((key) => /^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)*\.v[0-9]+$/.test(key)), { message: 'invalid extension namespace' }).optional(),
}).strict();

export const MessageParticipantSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("Participant"),
  "schema_version": z.literal("1.0.0"),
  "conversation_id": z.string().min(1),
  "entity_ref": ObjectRefSchema.optional(),
  "external_identity_ref": ObjectRefSchema.optional(),
  "role": z.enum(["sender", "recipient", "assignee", "observer", "system"]),
  "status": z.enum(["active", "left", "blocked", "provisional"]),
  "joined_at": z.string().datetime().optional(),
  "left_at": z.string().datetime().optional(),
  "created_at": z.string().datetime(),
  "updated_at": z.string().datetime(),
  "version": z.number().int().min(1),
  "extensions": z.record(z.string(), z.unknown()).refine((value) => Object.keys(value).every((key) => /^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)*\.v[0-9]+$/.test(key)), { message: 'invalid extension namespace' }).optional(),
}).strict();

export const QueueMessagePayloadSchema = z.object({
  "conversation_id": z.string().min(1),
  "sender_participant_ref": ObjectRefSchema.optional(),
  "sender_actor_ref": ActorRefSchema.optional(),
  "body": z.string(),
  "body_format": z.enum(["plain", "markdown", "html"]),
  "idempotency_key": z.string().optional(),
  "extensions": z.record(z.string(), z.unknown()).refine((value) => Object.keys(value).every((key) => /^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)*\.v[0-9]+$/.test(key)), { message: 'invalid extension namespace' }).optional(),
}).strict();

export const AvailabilityRuleSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("Availability"),
  "schema_version": z.literal("1.0.0"),
  "owner_ref": ObjectRefSchema,
  "resource_ref": ObjectRefSchema.optional(),
  "kind": z.enum(["available", "unavailable"]),
  "start_at": z.string().datetime(),
  "end_at": z.string().datetime(),
  "timezone": z.string().min(1),
  "capacity": z.number().int().min(0).optional(),
  "recurrence_rule": RecurrenceRuleSchema.optional(),
  "status": z.enum(["active", "archived"]),
  "version": z.number().int().min(1),
}).strict();

export const CalendarSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("Calendar"),
  "schema_version": z.literal("1.0.0"),
  "name": z.string().min(1),
  "timezone": z.string().min(1),
  "status": z.enum(["active", "archived"]),
  "owner_ref": ObjectRefSchema,
  "created_by": ActorRefSchema,
  "created_at": z.string().datetime(),
  "updated_at": z.string().datetime(),
  "version": z.number().int().min(1),
  "extensions": z.record(z.string(), z.unknown()).refine((value) => Object.keys(value).every((key) => /^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)*\.v[0-9]+$/.test(key)), { message: 'invalid extension namespace' }).optional(),
}).strict();

export const CalendarParticipantSchema = z.object({
  "participant_ref": ObjectRefSchema,
  "role": z.enum(["organizer", "required", "optional", "resource"]),
  "status": z.enum(["invited", "accepted", "declined", "tentative", "no_response", "canceled"]),
  "responded_at": z.string().datetime().optional(),
}).strict();

export const ReservationSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("Reservation"),
  "schema_version": z.literal("1.0.0"),
  "calendar_ref": ObjectRefSchema,
  "resource_ref": ObjectRefSchema,
  "reserved_for_ref": ObjectRefSchema,
  "status": z.enum(["held", "confirmed", "released", "canceled", "expired"]),
  "start_at": z.string().datetime(),
  "end_at": z.string().datetime(),
  "timezone": z.string().min(1),
  "quantity": z.number().int().min(1),
  "hold_expires_at": z.string().datetime().optional(),
  "created_at": z.string().datetime(),
  "updated_at": z.string().datetime(),
  "version": z.number().int().min(1),
  "extensions": z.record(z.string(), z.unknown()).refine((value) => Object.keys(value).every((key) => /^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)*\.v[0-9]+$/.test(key)), { message: 'invalid extension namespace' }).optional(),
}).strict();

export const CreateRecordPayloadSchema = z.object({
  "database_id": z.string().min(1),
  "table_id": z.string().min(1),
  "values": z.array(FieldValueSchema),
  "extensions": z.record(z.string(), z.unknown()).refine((value) => Object.keys(value).every((key) => /^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)*\.v[0-9]+$/.test(key)), { message: 'invalid extension namespace' }).optional(),
}).strict();

export const DatabaseSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("Database"),
  "schema_version": z.literal("1.0.0"),
  "name": z.string().min(1),
  "description": z.string().optional(),
  "status": z.enum(["draft", "active", "locked", "archived"]),
  "owner_ref": ObjectRefSchema,
  "authority_scope": z.record(z.string(), z.unknown()).optional(),
  "created_by": ActorRefSchema,
  "created_at": z.string().datetime(),
  "updated_at": z.string().datetime(),
  "version": z.number().int().min(1),
  "extensions": z.record(z.string(), z.unknown()).refine((value) => Object.keys(value).every((key) => /^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)*\.v[0-9]+$/.test(key)), { message: 'invalid extension namespace' }).optional(),
}).strict();

export const FieldDefinitionSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("FieldDefinition"),
  "schema_version": z.literal("1.0.0"),
  "table_id": z.string().min(1),
  "name": z.string().min(1),
  "field_type": z.enum(["text", "rich_text", "number", "boolean", "date", "datetime", "select", "multi_select", "person_ref", "organization_ref", "relation", "file_ref", "url", "email", "phone", "formula", "rollup"]),
  "required": z.boolean(),
  "unique": z.boolean(),
  "default_value": z.record(z.string(), z.unknown()).optional(),
  "validation": z.record(z.string(), z.unknown()).optional(),
  "options": z.array(z.string()).optional(),
  "relation_target": ObjectRefSchema.optional(),
  "formula": z.record(z.string(), z.unknown()).optional(),
  "position": z.number().int().min(0),
  "status": z.enum(["active", "archived"]),
  "created_at": z.string().datetime(),
  "updated_at": z.string().datetime(),
  "version": z.number().int().min(1),
}).strict();

export const DatabaseRecordSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("Record"),
  "schema_version": z.literal("1.0.0"),
  "database_id": z.string().min(1),
  "table_id": z.string().min(1),
  "record_version": z.number().int().min(1),
  "values": z.array(FieldValueSchema),
  "status": z.enum(["active", "archived", "deleted"]),
  "created_by": ActorRefSchema,
  "created_at": z.string().datetime(),
  "updated_at": z.string().datetime(),
  "provenance": z.record(z.string(), z.unknown()).optional(),
  "authority_scope": z.record(z.string(), z.unknown()).optional(),
  "version": z.number().int().min(1),
  "extensions": z.record(z.string(), z.unknown()).refine((value) => Object.keys(value).every((key) => /^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)*\.v[0-9]+$/.test(key)), { message: 'invalid extension namespace' }).optional(),
}).strict();

export const ViewDefinitionSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("ViewDefinition"),
  "schema_version": z.literal("1.0.0"),
  "database_id": z.string().min(1),
  "table_id": z.string().optional(),
  "name": z.string().min(1),
  "view_type": z.enum(["table", "kanban", "calendar", "timeline", "gallery", "chart", "form"]),
  "filters": z.record(z.string(), z.unknown()).optional(),
  "sorts": z.array(z.record(z.string(), z.unknown())).optional(),
  "grouping": z.record(z.string(), z.unknown()).optional(),
  "visible_fields": z.array(z.string()).optional(),
  "layout": z.record(z.string(), z.unknown()).optional(),
  "owner_ref": ObjectRefSchema.optional(),
  "visibility": z.string().optional(),
  "created_at": z.string().datetime(),
  "updated_at": z.string().datetime(),
  "version": z.number().int().min(1),
}).strict();

export const DocumentReviewRequestedPayloadSchema = z.object({
  "document_ref": ObjectRefSchema,
  "revision_id": z.string().min(1),
  "reviewer_ref": ActorRefSchema,
}).strict();

export const DocumentSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("Document"),
  "schema_version": z.literal("1.0.0"),
  "title": z.string().min(1),
  "status": z.enum(["draft", "in_review", "approved", "published", "archived"]),
  "current_revision_id": z.string().min(1),
  "owner_ref": ObjectRefSchema,
  "created_by": ActorRefSchema,
  "created_at": z.string().datetime(),
  "updated_at": z.string().datetime(),
  "authority_scope": z.record(z.string(), z.unknown()).optional(),
  "provenance": z.record(z.string(), z.unknown()).optional(),
  "version": z.number().int().min(1),
  "extensions": z.record(z.string(), z.unknown()).refine((value) => Object.keys(value).every((key) => /^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)*\.v[0-9]+$/.test(key)), { message: 'invalid extension namespace' }).optional(),
}).strict();

export const ReviewDecisionSubmittedPayloadSchema = z.object({
  "document_ref": ObjectRefSchema,
  "revision_id": z.string().min(1),
  "decision": z.enum(["approved", "changes_requested", "rejected", "canceled"]),
  "comments": z.string().optional(),
}).strict();

export const AuthorityContextSchema = z.object({
  "organizationId": z.string().min(1).optional(),
  "projectionId": z.string().min(1).optional(),
  "runtimeBinding": RuntimeBindingSchema,
  "permissionSet": z.array(z.string().min(1)).min(1),
  "policyVersion": z.string().min(1),
  "approvalId": z.string().min(1).optional(),
}).strict();

export const CommandEnvelopeSchema = z.object({
  "commandId": z.string().min(1),
  "commandType": z.string().regex(/^[A-Z][A-Za-z0-9]+\.v[0-9]+$/),
  "contractVersion": z.string().regex(/^1\.[0-9]+\.[0-9]+$/),
  "actor": ActorRefSchema,
  "authorityContext": AuthorityContextSchema,
  "target": z.union([ObjectRefSchema, z.null()]),
  "payload": z.record(z.string(), z.unknown()),
  "issuedAt": z.string().datetime(),
  "idempotencyKey": z.string().min(1).optional(),
  "correlationId": z.string().min(1),
  "causationId": z.string().min(1).optional(),
  "expectedAggregateVersion": z.number().int().min(0).optional(),
}).strict();

export const EvidenceRefSchema = z.object({
  "evidenceId": z.string().min(1),
  "evidenceType": z.string().min(1).optional(),
  "sourceRuntime": RuntimeBindingSchema,
  "objectRef": ObjectRefSchema.optional(),
  "uri": z.string().min(1).optional(),
  "contentHash": z.string().min(1).optional(),
  "observedAt": z.string().datetime(),
}).strict();

export const FileRegisteredPayloadSchema = z.object({
  "file": FileSchema,
}).strict();

export const FileRestoredPayloadSchema = z.object({
  "file": FileSchema,
}).strict();

export const FileTrashedPayloadSchema = z.object({
  "file": FileSchema,
}).strict();

export const RestoreFilePayloadSchema = z.object({
  "file_ref": ObjectRefSchema,
  "restore_to_status": z.enum(["ready", "archived"]),
  "reason": z.string().min(1),
  "evidence_refs": z.array(EvidenceRefSchema).optional(),
}).strict();

export const TrashFilePayloadSchema = z.object({
  "file_ref": ObjectRefSchema,
  "reason": z.string().min(1),
  "evidence_refs": z.array(EvidenceRefSchema).optional(),
}).strict();

export const InvoiceSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("Invoice"),
  "schema_version": z.literal("1.0.0"),
  "invoice_number": z.string().min(1),
  "status": z.enum(["draft", "issued", "paid", "voided", "overdue", "written_off"]),
  "bill_to_ref": ObjectRefSchema,
  "currency": z.string().regex(/^[A-Z]{3}$/),
  "total_amount": z.number().min(0),
  "issued_at": z.string().datetime(),
  "due_at": z.string().datetime(),
  "transaction_ref": ObjectRefSchema.optional(),
  "evidence_refs": z.array(EvidenceRefSchema).optional(),
  "version": z.number().int().min(1),
  "extensions": z.record(z.string(), z.unknown()).refine((value) => Object.keys(value).every((key) => /^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)*\.v[0-9]+$/.test(key)), { message: 'invalid extension namespace' }).optional(),
}).strict();

export const IssueInvoicePayloadSchema = z.object({
  "invoice": InvoiceSchema,
  "evidence_refs": z.array(EvidenceRefSchema).optional(),
}).strict();

export const StatementSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("Statement"),
  "schema_version": z.literal("1.0.0"),
  "period_ref": ObjectRefSchema,
  "statement_type": z.enum(["balance", "cash_flow", "income_expense", "budget", "forecast"]),
  "currency": z.string().regex(/^[A-Z]{3}$/),
  "generated_at": z.string().datetime(),
  "evidence_refs": z.array(EvidenceRefSchema),
  "version": z.number().int().min(1),
}).strict();

export const TransactionLineSchema = z.object({
  "line_id": z.string().min(1),
  "account_ref": ObjectRefSchema,
  "amount": z.number(),
  "currency": z.string().regex(/^[A-Z]{3}$/),
  "line_type": z.enum(["debit", "credit"]),
  "classification": z.enum(["income", "expense", "asset", "liability", "equity", "payout", "allocation"]).optional(),
  "memo": z.string().optional(),
  "evidence_refs": z.array(EvidenceRefSchema).optional(),
}).strict();

export const TransactionSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("Transaction"),
  "schema_version": z.literal("1.0.0"),
  "transaction_date": z.string().datetime(),
  "status": z.enum(["draft", "posted", "voided", "reversed", "adjusted"]),
  "currency": z.string().regex(/^[A-Z]{3}$/),
  "lines": z.array(TransactionLineSchema).min(2),
  "correction_of_ref": ObjectRefSchema.optional(),
  "correction_type": z.enum(["reversal", "adjustment", "correcting_entry"]).optional(),
  "memo": z.string().optional(),
  "created_by": ActorRefSchema,
  "created_at": z.string().datetime(),
  "updated_at": z.string().datetime(),
  "posted_at": z.string().datetime().optional(),
  "evidence_refs": z.array(EvidenceRefSchema).optional(),
  "version": z.number().int().min(1),
  "extensions": z.record(z.string(), z.unknown()).refine((value) => Object.keys(value).every((key) => /^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)*\.v[0-9]+$/.test(key)), { message: 'invalid extension namespace' }).optional(),
}).strict();

export const FormSubmissionSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("FormSubmission"),
  "schema_version": z.literal("1.0.0"),
  "form_ref": ObjectRefSchema,
  "form_version": z.number().int().min(1),
  "submitter_ref": ObjectRefSchema.optional(),
  "values": z.array(SubmissionValueSchema),
  "validation_status": z.enum(["accepted", "accepted_with_warnings", "rejected"]),
  "validation_errors": z.array(z.string()).optional(),
  "destination_record_ref": ObjectRefSchema.optional(),
  "submitted_at": z.string().datetime(),
  "evidence_refs": z.array(EvidenceRefSchema).optional(),
  "version": z.number().int().min(1),
  "extensions": z.record(z.string(), z.unknown()).refine((value) => Object.keys(value).every((key) => /^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)*\.v[0-9]+$/.test(key)), { message: 'invalid extension namespace' }).optional(),
}).strict();

export const FormSubmittedPayloadSchema = z.object({
  "submission": FormSubmissionSchema,
}).strict();

export const SubmitFormPayloadSchema = z.object({
  "form_ref": ObjectRefSchema,
  "form_version": z.number().int().min(1),
  "submitter_ref": ObjectRefSchema.optional(),
  "values": z.array(SubmissionValueSchema),
  "evidence_refs": z.array(EvidenceRefSchema).optional(),
  "extensions": z.record(z.string(), z.unknown()).refine((value) => Object.keys(value).every((key) => /^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)*\.v[0-9]+$/.test(key)), { message: 'invalid extension namespace' }).optional(),
}).strict();

export const ConsentSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("Consent"),
  "schema_version": z.literal("1.0.0"),
  "subject_ref": ObjectRefSchema,
  "scope": z.string().min(1),
  "channel": z.string().optional(),
  "purpose": z.string().optional(),
  "state": z.enum(["granted", "denied", "revoked", "expired"]),
  "basis": z.string().optional(),
  "captured_at": z.string().datetime(),
  "expires_at": z.string().datetime().optional(),
  "revoked_at": z.string().datetime().optional(),
  "source": z.string().min(1),
  "evidence_refs": z.array(EvidenceRefSchema).optional(),
  "created_at": z.string().datetime(),
  "updated_at": z.string().datetime(),
  "version": z.number().int().min(1),
  "extensions": z.record(z.string(), z.unknown()).refine((value) => Object.keys(value).every((key) => /^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)*\.v[0-9]+$/.test(key)), { message: 'invalid extension namespace' }).optional(),
}).strict();

export const InteractionSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("Interaction"),
  "schema_version": z.literal("1.0.0"),
  "relationship_id": z.string().min(1),
  "interaction_type": z.string().min(1),
  "occurred_at": z.string().datetime(),
  "direction": z.enum(["inbound", "outbound", "internal", "unknown"]).optional(),
  "channel": z.string().optional(),
  "summary": z.string().optional(),
  "source_object_refs": z.array(ObjectRefSchema).optional(),
  "actor_ref": ActorRefSchema.optional(),
  "evidence_refs": z.array(EvidenceRefSchema).optional(),
  "created_at": z.string().datetime(),
  "version": z.number().int().min(1),
  "extensions": z.record(z.string(), z.unknown()).refine((value) => Object.keys(value).every((key) => /^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)*\.v[0-9]+$/.test(key)), { message: 'invalid extension namespace' }).optional(),
}).strict();

export const PersonCreatedPayloadSchema = z.object({
  "person": PersonSchema,
}).strict();

export const RecordInteractionPayloadSchema = z.object({
  "relationship_id": z.string().min(1),
  "interaction_type": z.string().min(1),
  "occurred_at": z.string().datetime(),
  "direction": z.enum(["inbound", "outbound", "internal", "unknown"]).optional(),
  "channel": z.string().optional(),
  "summary": z.string().optional(),
  "source_object_refs": z.array(ObjectRefSchema).optional(),
  "actor_ref": ActorRefSchema.optional(),
  "evidence_refs": z.array(EvidenceRefSchema).optional(),
  "extensions": z.record(z.string(), z.unknown()).refine((value) => Object.keys(value).every((key) => /^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)*\.v[0-9]+$/.test(key)), { message: 'invalid extension namespace' }).optional(),
}).strict();

export const RelationshipCreatedPayloadSchema = z.object({
  "relationship": RelationshipSchema,
}).strict();

export const DeliveryReceiptSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("DeliveryReceipt"),
  "schema_version": z.literal("1.0.0"),
  "message_id": z.string().min(1),
  "delivery_attempt_id": z.string().min(1),
  "provider": z.string().min(1),
  "state": z.enum(["queued", "accepted", "sent", "delivered", "read", "failed", "bounced", "rejected"]),
  "occurred_at": z.string().datetime(),
  "provider_receipt_id": z.string().optional(),
  "failure_code": z.string().optional(),
  "failure_detail": z.string().optional(),
  "evidence_refs": z.array(EvidenceRefSchema).optional(),
  "version": z.number().int().min(1),
}).strict();

export const MessageQueuedPayloadSchema = z.object({
  "message": MessageSchema,
}).strict();

export const CreateReservationPayloadSchema = z.object({
  "calendar_ref": ObjectRefSchema,
  "resource_ref": ObjectRefSchema,
  "reserved_for_ref": ObjectRefSchema,
  "start_at": z.string().datetime(),
  "end_at": z.string().datetime(),
  "timezone": z.string().min(1),
  "quantity": z.number().int().min(1),
  "hold_expires_at": z.string().datetime().optional(),
  "evidence_refs": z.array(EvidenceRefSchema).optional(),
  "extensions": z.record(z.string(), z.unknown()).refine((value) => Object.keys(value).every((key) => /^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)*\.v[0-9]+$/.test(key)), { message: 'invalid extension namespace' }).optional(),
}).strict();

export const CalendarEventSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("Event"),
  "schema_version": z.literal("1.0.0"),
  "calendar_ref": ObjectRefSchema,
  "title": z.string().min(1),
  "status": z.enum(["tentative", "confirmed", "canceled"]),
  "start_at": z.string().datetime(),
  "end_at": z.string().datetime(),
  "timezone": z.string().min(1),
  "participants": z.array(CalendarParticipantSchema),
  "recurrence_rule": RecurrenceRuleSchema.optional(),
  "reservation_ref": ObjectRefSchema.optional(),
  "created_at": z.string().datetime(),
  "updated_at": z.string().datetime(),
  "version": z.number().int().min(1),
  "extensions": z.record(z.string(), z.unknown()).refine((value) => Object.keys(value).every((key) => /^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)*\.v[0-9]+$/.test(key)), { message: 'invalid extension namespace' }).optional(),
}).strict();

export const ReservationCreatedPayloadSchema = z.object({
  "reservation": ReservationSchema,
}).strict();

export const CreateDatabasePayloadSchema = z.object({
  "name": z.string().min(1),
  "description": z.string().optional(),
  "owner_ref": ObjectRefSchema,
  "initial_fields": z.array(FieldDefinitionSchema).optional(),
  "extensions": z.record(z.string(), z.unknown()).refine((value) => Object.keys(value).every((key) => /^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)*\.v[0-9]+$/.test(key)), { message: 'invalid extension namespace' }).optional(),
}).strict();

export const DatabaseCreatedPayloadSchema = z.object({
  "database": DatabaseSchema,
}).strict();

export const RecordCreatedPayloadSchema = z.object({
  "record": DatabaseRecordSchema,
}).strict();

export const DocumentReviewRequestSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("DocumentReviewRequest"),
  "schema_version": z.literal("1.0.0"),
  "document_id": z.string().min(1),
  "revision_id": z.string().min(1),
  "reviewer_ref": ActorRefSchema,
  "status": z.enum(["requested", "canceled", "decision_submitted"]),
  "requested_at": z.string().datetime(),
  "completed_at": z.string().datetime().optional(),
  "comments": z.string().optional(),
  "evidence_refs": z.array(EvidenceRefSchema).optional(),
  "version": z.number().int().min(1),
}).strict();

export const DocumentRevisionSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("DocumentRevision"),
  "schema_version": z.literal("1.0.0"),
  "document_id": z.string().min(1),
  "revision_number": z.number().int().min(1),
  "content": z.record(z.string(), z.unknown()),
  "content_format": z.enum(["markdown", "rich_text", "plain_text", "structured_json"]),
  "created_by": ActorRefSchema,
  "created_at": z.string().datetime(),
  "change_summary": z.string().optional(),
  "base_revision_id": z.string().optional(),
  "supersedes_revision_id": z.string().optional(),
  "evidence_refs": z.array(EvidenceRefSchema).optional(),
  "version": z.number().int().min(1),
}).strict();

export const PublicationRecordSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("PublicationRecord"),
  "schema_version": z.literal("1.0.0"),
  "document_id": z.string().min(1),
  "revision_id": z.string().min(1),
  "status": z.enum(["published", "revoked", "superseded"]),
  "published_by": ActorRefSchema,
  "published_at": z.string().datetime(),
  "evidence_refs": z.array(EvidenceRefSchema).optional(),
  "version": z.number().int().min(1),
}).strict();

export const RequestDocumentReviewPayloadSchema = z.object({
  "document_ref": ObjectRefSchema,
  "revision_id": z.string().min(1),
  "reviewer_ref": ActorRefSchema,
  "instructions": z.string().optional(),
  "evidence_refs": z.array(EvidenceRefSchema).optional(),
}).strict();

export const ReviewDecisionSchema = z.object({
  "id": z.string().min(1),
  "objectType": z.literal("ReviewDecision"),
  "schema_version": z.literal("1.0.0"),
  "review_request_id": z.string().min(1),
  "document_id": z.string().min(1),
  "revision_id": z.string().min(1),
  "reviewer_ref": ActorRefSchema,
  "decision": z.enum(["approved", "changes_requested", "rejected", "canceled"]),
  "comments": z.string().optional(),
  "decided_at": z.string().datetime(),
  "evidence_refs": z.array(EvidenceRefSchema).optional(),
  "version": z.number().int().min(1),
}).strict();

export const SubmitReviewDecisionPayloadSchema = z.object({
  "document_ref": ObjectRefSchema,
  "revision_id": z.string().min(1),
  "decision": z.enum(["approved", "changes_requested", "rejected", "canceled"]),
  "comments": z.string().optional(),
  "evidence_refs": z.array(EvidenceRefSchema).optional(),
}).strict();

export const EventEnvelopeSchema = z.object({
  "eventId": z.string().min(1),
  "eventType": z.string().regex(/^[A-Z][A-Za-z0-9]+\.v[0-9]+$/),
  "contractVersion": z.string().regex(/^1\.[0-9]+\.[0-9]+$/),
  "aggregate": ObjectRefSchema,
  "aggregateVersion": z.number().int().min(1),
  "actor": ActorRefSchema,
  "authorityContext": AuthorityContextSchema,
  "occurredAt": z.string().datetime(),
  "sourceRuntime": RuntimeBindingSchema,
  "correlationId": z.string().min(1),
  "causationId": z.string().min(1),
  "evidenceRefs": z.array(EvidenceRefSchema),
  "payload": z.record(z.string(), z.unknown()),
}).strict();

export const InvoiceIssuedPayloadSchema = z.object({
  "invoice": InvoiceSchema,
}).strict();

export const PostTransactionPayloadSchema = z.object({
  "transaction": TransactionSchema,
  "evidence_refs": z.array(EvidenceRefSchema).optional(),
  "extensions": z.record(z.string(), z.unknown()).refine((value) => Object.keys(value).every((key) => /^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)*\.v[0-9]+$/.test(key)), { message: 'invalid extension namespace' }).optional(),
}).strict();

export const TransactionPostedPayloadSchema = z.object({
  "transaction": TransactionSchema,
}).strict();

export const InteractionRecordedPayloadSchema = z.object({
  "interaction": InteractionSchema,
}).strict();

export const FoundationSchemas = { ActorRef: ActorRefSchema, Allocation: AllocationSchema, Assignment: AssignmentSchema, AuthorityContext: AuthorityContextSchema, AvailabilityRule: AvailabilityRuleSchema, Calendar: CalendarSchema, CalendarEvent: CalendarEventSchema, CalendarParticipant: CalendarParticipantSchema, CalendarResource: CalendarResourceSchema, ChannelBinding: ChannelBindingSchema, CommandEnvelope: CommandEnvelopeSchema, Consent: ConsentSchema, ContactPoint: ContactPointSchema, Conversation: ConversationSchema, CreateDatabasePayload: CreateDatabasePayloadSchema, CreatePersonPayload: CreatePersonPayloadSchema, CreateRecordPayload: CreateRecordPayloadSchema, CreateRelationshipPayload: CreateRelationshipPayloadSchema, CreateReservationPayload: CreateReservationPayloadSchema, Database: DatabaseSchema, DatabaseCreatedPayload: DatabaseCreatedPayloadSchema, DatabaseRecord: DatabaseRecordSchema, DeliveryReceipt: DeliveryReceiptSchema, Document: DocumentSchema, DocumentReviewRequest: DocumentReviewRequestSchema, DocumentReviewRequestedPayload: DocumentReviewRequestedPayloadSchema, DocumentRevision: DocumentRevisionSchema, EventEnvelope: EventEnvelopeSchema, EvidenceRef: EvidenceRefSchema, ExternalIdentity: ExternalIdentitySchema, Facet: FacetSchema, FieldDefinition: FieldDefinitionSchema, FieldValue: FieldValueSchema, File: FileSchema, FileRegisteredPayload: FileRegisteredPayloadSchema, FileRestoredPayload: FileRestoredPayloadSchema, FileTrashedPayload: FileTrashedPayloadSchema, FinancialAccount: FinancialAccountSchema, FinancialPeriod: FinancialPeriodSchema, FollowUp: FollowUpSchema, Form: FormSchema, FormDestinationBinding: FormDestinationBindingSchema, FormField: FormFieldSchema, FormSubmission: FormSubmissionSchema, FormSubmittedPayload: FormSubmittedPayloadSchema, Interaction: InteractionSchema, InteractionRecordedPayload: InteractionRecordedPayloadSchema, InternalNote: InternalNoteSchema, Invoice: InvoiceSchema, InvoiceIssuedPayload: InvoiceIssuedPayloadSchema, IssueInvoicePayload: IssueInvoicePayloadSchema, Message: MessageSchema, MessageAttachment: MessageAttachmentSchema, MessageParticipant: MessageParticipantSchema, MessageQueuedPayload: MessageQueuedPayloadSchema, ObjectRef: ObjectRefSchema, Opportunity: OpportunitySchema, Organization: OrganizationSchema, Person: PersonSchema, PersonCreatedPayload: PersonCreatedPayloadSchema, Pipeline: PipelineSchema, PostTransactionPayload: PostTransactionPayloadSchema, PublicationRecord: PublicationRecordSchema, QueueMessagePayload: QueueMessagePayloadSchema, RecordCreatedPayload: RecordCreatedPayloadSchema, RecordInteractionPayload: RecordInteractionPayloadSchema, RecurrenceRule: RecurrenceRuleSchema, RegisterFilePayload: RegisterFilePayloadSchema, Relationship: RelationshipSchema, RelationshipCreatedPayload: RelationshipCreatedPayloadSchema, RequestDocumentReviewPayload: RequestDocumentReviewPayloadSchema, Reservation: ReservationSchema, ReservationCreatedPayload: ReservationCreatedPayloadSchema, RestoreFilePayload: RestoreFilePayloadSchema, ReviewDecision: ReviewDecisionSchema, ReviewDecisionSubmittedPayload: ReviewDecisionSubmittedPayloadSchema, RuntimeBinding: RuntimeBindingSchema, Stage: StageSchema, Statement: StatementSchema, SubmissionValue: SubmissionValueSchema, SubmitFormPayload: SubmitFormPayloadSchema, SubmitReviewDecisionPayload: SubmitReviewDecisionPayloadSchema, Table: TableSchema, Transaction: TransactionSchema, TransactionLine: TransactionLineSchema, TransactionPostedPayload: TransactionPostedPayloadSchema, TrashFilePayload: TrashFilePayloadSchema, ViewDefinition: ViewDefinitionSchema };
