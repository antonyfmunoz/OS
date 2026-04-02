-- ─────────────────────────────────────────────────────────────────────────────
-- Migration 0001: Portfolio architecture + agent hierarchy + workflow redesign
--
-- Changes:
--   1. CREATE portfolios (cross-company grouping, no RLS)
--   2. ALTER organizations ADD portfolio_id, autonomy_stage
--   3. ALTER org_members ADD access_level
--   4. Recreate agents (drop+recreate — 0 rows, safe): nullable org_id,
--      add portfolio_id / agent_type / department / parent_agent_id / is_active,
--      rename soul_json→soul / domain_rules_json→domain_rules / tools_json→tools,
--      change data_tier from enum to text
--   5. Recreate workflows (drop+recreate — 0 rows, safe): add description /
--      executor_type / trigger_type / is_active, rename steps_json→steps,
--      change autonomy_stage from enum to text
--   6. CREATE user_agent_sessions
-- ─────────────────────────────────────────────────────────────────────────────

--> statement-breakpoint
CREATE TABLE "portfolios" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"user_id" uuid,
	"name" text NOT NULL,
	"north_star" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
ALTER TABLE "portfolios" ADD CONSTRAINT "portfolios_user_id_users_id_fk"
  FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE set null ON UPDATE no action;
--> statement-breakpoint
CREATE INDEX "idx_portfolios_user_id" ON "portfolios" USING btree ("user_id");

--> statement-breakpoint
ALTER TABLE "organizations" ADD COLUMN "portfolio_id" uuid;
--> statement-breakpoint
ALTER TABLE "organizations" ADD COLUMN "autonomy_stage" text DEFAULT 'manual' NOT NULL;
--> statement-breakpoint
ALTER TABLE "organizations" ADD CONSTRAINT "organizations_portfolio_id_portfolios_id_fk"
  FOREIGN KEY ("portfolio_id") REFERENCES "public"."portfolios"("id") ON DELETE set null ON UPDATE no action;
--> statement-breakpoint
CREATE INDEX "idx_organizations_portfolio_id" ON "organizations" USING btree ("portfolio_id");

--> statement-breakpoint
ALTER TABLE "org_members" ADD COLUMN "access_level" text DEFAULT 'member' NOT NULL;

--> statement-breakpoint
-- Drop FK from interactions that references agents (must drop before agents)
ALTER TABLE "interactions" DROP CONSTRAINT IF EXISTS "interactions_agent_id_agents_id_fk";
--> statement-breakpoint
-- Drop agents (0 rows — safe). FK agents→organizations drops with table.
DROP TABLE "agents";
--> statement-breakpoint
-- Recreate agents with full hierarchy architecture
CREATE TABLE "agents" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"org_id" uuid,
	"portfolio_id" uuid,
	"name" text NOT NULL,
	"agent_type" text NOT NULL,
	"department" text,
	"parent_agent_id" uuid,
	"soul" jsonb DEFAULT '{}'::jsonb NOT NULL,
	"domain_rules" jsonb DEFAULT '{}'::jsonb NOT NULL,
	"tools" jsonb DEFAULT '[]'::jsonb NOT NULL,
	"data_tier" text DEFAULT 'internal' NOT NULL,
	"is_active" boolean DEFAULT true NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
ALTER TABLE "agents" ADD CONSTRAINT "agents_org_id_organizations_id_fk"
  FOREIGN KEY ("org_id") REFERENCES "public"."organizations"("id") ON DELETE cascade ON UPDATE no action;
--> statement-breakpoint
ALTER TABLE "agents" ADD CONSTRAINT "agents_portfolio_id_portfolios_id_fk"
  FOREIGN KEY ("portfolio_id") REFERENCES "public"."portfolios"("id") ON DELETE set null ON UPDATE no action;
--> statement-breakpoint
ALTER TABLE "agents" ADD CONSTRAINT "agents_parent_agent_id_agents_id_fk"
  FOREIGN KEY ("parent_agent_id") REFERENCES "public"."agents"("id") ON DELETE set null ON UPDATE no action;
--> statement-breakpoint
-- Restore FK from interactions → agents
ALTER TABLE "interactions" ADD CONSTRAINT "interactions_agent_id_agents_id_fk"
  FOREIGN KEY ("agent_id") REFERENCES "public"."agents"("id") ON DELETE set null ON UPDATE no action;
--> statement-breakpoint
CREATE INDEX "idx_agents_org_id" ON "agents" USING btree ("org_id");
--> statement-breakpoint
CREATE INDEX "idx_agents_portfolio_id" ON "agents" USING btree ("portfolio_id");
--> statement-breakpoint
CREATE INDEX "idx_agents_parent_id" ON "agents" USING btree ("parent_agent_id");

--> statement-breakpoint
-- Drop workflows (0 rows — safe)
DROP TABLE "workflows";
--> statement-breakpoint
-- Recreate workflows with full executor/trigger architecture
CREATE TABLE "workflows" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"org_id" uuid NOT NULL,
	"name" text NOT NULL,
	"description" text,
	"executor_type" text NOT NULL,
	"autonomy_stage" text DEFAULT 'manual' NOT NULL,
	"steps" jsonb DEFAULT '[]'::jsonb NOT NULL,
	"trigger_type" text DEFAULT 'manual' NOT NULL,
	"is_active" boolean DEFAULT true NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
ALTER TABLE "workflows" ADD CONSTRAINT "workflows_org_id_organizations_id_fk"
  FOREIGN KEY ("org_id") REFERENCES "public"."organizations"("id") ON DELETE cascade ON UPDATE no action;
--> statement-breakpoint
CREATE INDEX "idx_workflows_org_id" ON "workflows" USING btree ("org_id");

--> statement-breakpoint
CREATE TABLE "user_agent_sessions" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"user_id" uuid,
	"org_id" uuid,
	"active_agent_id" uuid,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
ALTER TABLE "user_agent_sessions" ADD CONSTRAINT "user_agent_sessions_user_id_users_id_fk"
  FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE cascade ON UPDATE no action;
--> statement-breakpoint
ALTER TABLE "user_agent_sessions" ADD CONSTRAINT "user_agent_sessions_org_id_organizations_id_fk"
  FOREIGN KEY ("org_id") REFERENCES "public"."organizations"("id") ON DELETE cascade ON UPDATE no action;
--> statement-breakpoint
ALTER TABLE "user_agent_sessions" ADD CONSTRAINT "user_agent_sessions_active_agent_id_agents_id_fk"
  FOREIGN KEY ("active_agent_id") REFERENCES "public"."agents"("id") ON DELETE set null ON UPDATE no action;
--> statement-breakpoint
CREATE INDEX "idx_user_agent_sessions_user_org" ON "user_agent_sessions" USING btree ("user_id", "org_id");
--> statement-breakpoint
CREATE INDEX "idx_user_agent_sessions_org_id" ON "user_agent_sessions" USING btree ("org_id");
