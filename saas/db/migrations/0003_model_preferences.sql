-- ─────────────────────────────────────────────────────────────────────────────
-- Migration 0003: Model preferences — per-org model routing config
--
-- Changes:
--   1. CREATE model_preferences — stores cost mode, local preference,
--      session/task overrides per org
--   2. ENABLE ROW LEVEL SECURITY with org_isolation policy
-- ─────────────────────────────────────────────────────────────────────────────

--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "model_preferences" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
  "org_id" uuid REFERENCES "public"."organizations"("id") ON DELETE CASCADE,
  "prefer_local" boolean DEFAULT false NOT NULL,
  "cost_mode" text DEFAULT 'auto' NOT NULL,
  "session_override" text DEFAULT NULL,
  "per_task_overrides" jsonb DEFAULT '{}' NOT NULL,
  "updated_at" timestamp with time zone DEFAULT now() NOT NULL,
  CONSTRAINT "model_preferences_org_id_unique" UNIQUE("org_id")
);
--> statement-breakpoint
ALTER TABLE "model_preferences" ENABLE ROW LEVEL SECURITY;
--> statement-breakpoint
CREATE POLICY "org_isolation" ON "model_preferences"
  USING (
    "org_id"::text = current_setting('app.current_org_id', true)
  );
