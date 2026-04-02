-- ─────────────────────────────────────────────────────────────────────────────
-- Migration 0002: Python AI layer columns
--
-- Changes:
--   1. ALTER interactions ADD agent_label  — Python string agent name
--   2. ALTER interactions ADD lead_username — social handle for outreach context
--   3. ALTER outcomes ADD outcome_label    — Python outcome type (reply/no_reply/
--      booked/closed/ignored) stored alongside Neon's enum for RLHF analytics
--   4. Indexes on new columns
-- ─────────────────────────────────────────────────────────────────────────────

--> statement-breakpoint
ALTER TABLE "interactions" ADD COLUMN IF NOT EXISTS "agent_label" text;
--> statement-breakpoint
ALTER TABLE "interactions" ADD COLUMN IF NOT EXISTS "lead_username" text;
--> statement-breakpoint
ALTER TABLE "outcomes" ADD COLUMN IF NOT EXISTS "outcome_label" text;
--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "idx_interactions_lead_username" ON "interactions" USING btree ("lead_username");
--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "idx_interactions_agent_label" ON "interactions" USING btree ("agent_label");
--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "idx_outcomes_label" ON "outcomes" USING btree ("outcome_label");
