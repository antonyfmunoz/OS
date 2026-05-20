-- Phase 3: UMH outcome writeback
-- Additive only — nullable columns + new table. No existing data affected.

ALTER TABLE "events" ADD COLUMN "umh_status" text;
ALTER TABLE "clients" ADD COLUMN "umh_status" text;
ALTER TABLE "ventures" ADD COLUMN "umh_status" text;

CREATE TABLE IF NOT EXISTS "umh_outcomes" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
  "org_id" uuid NOT NULL REFERENCES "organizations"("id") ON DELETE CASCADE,
  "trace_id" text NOT NULL,
  "source_table" text NOT NULL,
  "source_row_id" uuid,
  "outcome_type" text NOT NULL,
  "severity" integer NOT NULL,
  "payload" jsonb NOT NULL DEFAULT '{}'::jsonb,
  "created_at" timestamp with time zone NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS "idx_umh_outcomes_org_id" ON "umh_outcomes" ("org_id");
CREATE INDEX IF NOT EXISTS "idx_umh_outcomes_trace_id" ON "umh_outcomes" ("trace_id");
CREATE INDEX IF NOT EXISTS "idx_umh_outcomes_source" ON "umh_outcomes" ("source_table", "source_row_id");
CREATE INDEX IF NOT EXISTS "idx_umh_outcomes_org_created" ON "umh_outcomes" ("org_id", "created_at");
CREATE INDEX IF NOT EXISTS "idx_umh_outcomes_type" ON "umh_outcomes" ("outcome_type");
