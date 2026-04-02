CREATE TYPE "public"."agent_data_tier" AS ENUM('standard', 'premium', 'isolated');--> statement-breakpoint
CREATE TYPE "public"."approval_status" AS ENUM('pending', 'approved', 'rejected', 'expired');--> statement-breakpoint
CREATE TYPE "public"."autonomy_stage" AS ENUM('supervised', 'semi_autonomous', 'autonomous');--> statement-breakpoint
CREATE TYPE "public"."member_role" AS ENUM('owner', 'admin', 'member');--> statement-breakpoint
CREATE TYPE "public"."org_plan" AS ENUM('free', 'starter', 'growth', 'enterprise');--> statement-breakpoint
CREATE TYPE "public"."outcome_type" AS ENUM('positive', 'negative', 'neutral', 'skipped');--> statement-breakpoint
CREATE TYPE "public"."venture_stage" AS ENUM('idea', 'pre_revenue', 'early', 'growth', 'scale');--> statement-breakpoint
CREATE TABLE "agents" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"org_id" uuid NOT NULL,
	"name" text NOT NULL,
	"soul_json" jsonb DEFAULT '{}'::jsonb NOT NULL,
	"domain_rules_json" jsonb DEFAULT '{}'::jsonb NOT NULL,
	"tools_json" jsonb DEFAULT '[]'::jsonb NOT NULL,
	"data_tier" "agent_data_tier" DEFAULT 'standard' NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "approvals" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"org_id" uuid NOT NULL,
	"request_json" jsonb DEFAULT '{}'::jsonb NOT NULL,
	"status" "approval_status" DEFAULT 'pending' NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"resolved_at" timestamp with time zone,
	"resolved_by" uuid
);
--> statement-breakpoint
CREATE TABLE "embeddings" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"interaction_id" uuid NOT NULL,
	"org_id" uuid NOT NULL,
	"embedding" vector(1536) NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "events" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"org_id" uuid NOT NULL,
	"event_type" text NOT NULL,
	"payload_json" jsonb DEFAULT '{}'::jsonb NOT NULL,
	"handled_by" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "human_profiles" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"org_id" uuid NOT NULL,
	"username" text NOT NULL,
	"venture_id" uuid,
	"profile_json" jsonb DEFAULT '{}'::jsonb NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "interactions" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"org_id" uuid NOT NULL,
	"user_id" uuid,
	"venture_id" uuid,
	"agent_id" uuid,
	"skill_id" uuid,
	"task_type" text NOT NULL,
	"model_used" text NOT NULL,
	"input_summary" text,
	"output_summary" text,
	"tokens_json" jsonb DEFAULT '{"prompt":0,"completion":0,"total":0,"cost_usd":0}'::jsonb NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "org_members" (
	"org_id" uuid NOT NULL,
	"user_id" uuid NOT NULL,
	"role" "member_role" DEFAULT 'member' NOT NULL,
	CONSTRAINT "org_members_org_id_user_id_pk" PRIMARY KEY("org_id","user_id")
);
--> statement-breakpoint
CREATE TABLE "organizations" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"name" text NOT NULL,
	"owner_id" uuid NOT NULL,
	"plan" "org_plan" DEFAULT 'free' NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "outcomes" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"interaction_id" uuid NOT NULL,
	"org_id" uuid NOT NULL,
	"outcome_type" "outcome_type" NOT NULL,
	"score" numeric(5, 2),
	"notes" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "skill_versions" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"skill_id" uuid NOT NULL,
	"org_id" uuid NOT NULL,
	"content" text NOT NULL,
	"version" integer NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"improvement_event_id" uuid
);
--> statement-breakpoint
CREATE TABLE "skills" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"org_id" uuid NOT NULL,
	"name" text NOT NULL,
	"content" text NOT NULL,
	"version" integer DEFAULT 1 NOT NULL,
	"fitness_function" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "users" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"email" text NOT NULL,
	"name" text NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "users_email_unique" UNIQUE("email")
);
--> statement-breakpoint
CREATE TABLE "ventures" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"org_id" uuid NOT NULL,
	"name" text NOT NULL,
	"stage" "venture_stage" DEFAULT 'idea' NOT NULL,
	"config_json" jsonb DEFAULT '{}'::jsonb NOT NULL,
	"monthly_revenue" numeric(12, 2) DEFAULT '0' NOT NULL,
	"monthly_target" numeric(12, 2) DEFAULT '0' NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "workflows" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"org_id" uuid NOT NULL,
	"name" text NOT NULL,
	"steps_json" jsonb DEFAULT '[]'::jsonb NOT NULL,
	"autonomy_stage" "autonomy_stage" DEFAULT 'supervised' NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
ALTER TABLE "agents" ADD CONSTRAINT "agents_org_id_organizations_id_fk" FOREIGN KEY ("org_id") REFERENCES "public"."organizations"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "approvals" ADD CONSTRAINT "approvals_org_id_organizations_id_fk" FOREIGN KEY ("org_id") REFERENCES "public"."organizations"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "approvals" ADD CONSTRAINT "approvals_resolved_by_users_id_fk" FOREIGN KEY ("resolved_by") REFERENCES "public"."users"("id") ON DELETE set null ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "embeddings" ADD CONSTRAINT "embeddings_interaction_id_interactions_id_fk" FOREIGN KEY ("interaction_id") REFERENCES "public"."interactions"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "embeddings" ADD CONSTRAINT "embeddings_org_id_organizations_id_fk" FOREIGN KEY ("org_id") REFERENCES "public"."organizations"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "events" ADD CONSTRAINT "events_org_id_organizations_id_fk" FOREIGN KEY ("org_id") REFERENCES "public"."organizations"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "human_profiles" ADD CONSTRAINT "human_profiles_org_id_organizations_id_fk" FOREIGN KEY ("org_id") REFERENCES "public"."organizations"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "human_profiles" ADD CONSTRAINT "human_profiles_venture_id_ventures_id_fk" FOREIGN KEY ("venture_id") REFERENCES "public"."ventures"("id") ON DELETE set null ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "interactions" ADD CONSTRAINT "interactions_org_id_organizations_id_fk" FOREIGN KEY ("org_id") REFERENCES "public"."organizations"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "interactions" ADD CONSTRAINT "interactions_user_id_users_id_fk" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE set null ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "interactions" ADD CONSTRAINT "interactions_venture_id_ventures_id_fk" FOREIGN KEY ("venture_id") REFERENCES "public"."ventures"("id") ON DELETE set null ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "interactions" ADD CONSTRAINT "interactions_agent_id_agents_id_fk" FOREIGN KEY ("agent_id") REFERENCES "public"."agents"("id") ON DELETE set null ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "interactions" ADD CONSTRAINT "interactions_skill_id_skills_id_fk" FOREIGN KEY ("skill_id") REFERENCES "public"."skills"("id") ON DELETE set null ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "org_members" ADD CONSTRAINT "org_members_org_id_organizations_id_fk" FOREIGN KEY ("org_id") REFERENCES "public"."organizations"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "org_members" ADD CONSTRAINT "org_members_user_id_users_id_fk" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "organizations" ADD CONSTRAINT "organizations_owner_id_users_id_fk" FOREIGN KEY ("owner_id") REFERENCES "public"."users"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "outcomes" ADD CONSTRAINT "outcomes_interaction_id_interactions_id_fk" FOREIGN KEY ("interaction_id") REFERENCES "public"."interactions"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "outcomes" ADD CONSTRAINT "outcomes_org_id_organizations_id_fk" FOREIGN KEY ("org_id") REFERENCES "public"."organizations"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "skill_versions" ADD CONSTRAINT "skill_versions_skill_id_skills_id_fk" FOREIGN KEY ("skill_id") REFERENCES "public"."skills"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "skill_versions" ADD CONSTRAINT "skill_versions_org_id_organizations_id_fk" FOREIGN KEY ("org_id") REFERENCES "public"."organizations"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "skill_versions" ADD CONSTRAINT "skill_versions_improvement_event_id_events_id_fk" FOREIGN KEY ("improvement_event_id") REFERENCES "public"."events"("id") ON DELETE set null ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "skills" ADD CONSTRAINT "skills_org_id_organizations_id_fk" FOREIGN KEY ("org_id") REFERENCES "public"."organizations"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "ventures" ADD CONSTRAINT "ventures_org_id_organizations_id_fk" FOREIGN KEY ("org_id") REFERENCES "public"."organizations"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "workflows" ADD CONSTRAINT "workflows_org_id_organizations_id_fk" FOREIGN KEY ("org_id") REFERENCES "public"."organizations"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
CREATE INDEX "idx_agents_org_id" ON "agents" USING btree ("org_id");--> statement-breakpoint
CREATE INDEX "idx_approvals_org_id" ON "approvals" USING btree ("org_id");--> statement-breakpoint
CREATE INDEX "idx_approvals_org_status" ON "approvals" USING btree ("org_id","status");--> statement-breakpoint
CREATE INDEX "idx_approvals_resolved" ON "approvals" USING btree ("resolved_by");--> statement-breakpoint
CREATE INDEX "idx_embeddings_interaction_id" ON "embeddings" USING btree ("interaction_id");--> statement-breakpoint
CREATE INDEX "idx_embeddings_org_id" ON "embeddings" USING btree ("org_id");--> statement-breakpoint
CREATE INDEX "idx_events_org_id" ON "events" USING btree ("org_id");--> statement-breakpoint
CREATE INDEX "idx_events_org_type" ON "events" USING btree ("org_id","event_type");--> statement-breakpoint
CREATE INDEX "idx_events_org_created" ON "events" USING btree ("org_id","created_at");--> statement-breakpoint
CREATE UNIQUE INDEX "idx_human_profiles_org_username" ON "human_profiles" USING btree ("org_id","username");--> statement-breakpoint
CREATE INDEX "idx_human_profiles_org_id" ON "human_profiles" USING btree ("org_id");--> statement-breakpoint
CREATE INDEX "idx_human_profiles_venture_id" ON "human_profiles" USING btree ("venture_id");--> statement-breakpoint
CREATE INDEX "idx_interactions_org_id" ON "interactions" USING btree ("org_id");--> statement-breakpoint
CREATE INDEX "idx_interactions_org_created" ON "interactions" USING btree ("org_id","created_at");--> statement-breakpoint
CREATE INDEX "idx_interactions_org_agent" ON "interactions" USING btree ("org_id","agent_id");--> statement-breakpoint
CREATE INDEX "idx_interactions_org_venture" ON "interactions" USING btree ("org_id","venture_id");--> statement-breakpoint
CREATE INDEX "idx_interactions_org_skill" ON "interactions" USING btree ("org_id","skill_id");--> statement-breakpoint
CREATE INDEX "idx_interactions_user_id" ON "interactions" USING btree ("user_id");--> statement-breakpoint
CREATE INDEX "idx_org_members_user_id" ON "org_members" USING btree ("user_id");--> statement-breakpoint
CREATE INDEX "idx_organizations_owner_id" ON "organizations" USING btree ("owner_id");--> statement-breakpoint
CREATE INDEX "idx_outcomes_interaction_id" ON "outcomes" USING btree ("interaction_id");--> statement-breakpoint
CREATE INDEX "idx_outcomes_org_id" ON "outcomes" USING btree ("org_id");--> statement-breakpoint
CREATE INDEX "idx_outcomes_org_type" ON "outcomes" USING btree ("org_id","outcome_type");--> statement-breakpoint
CREATE INDEX "idx_skill_versions_skill_id" ON "skill_versions" USING btree ("skill_id");--> statement-breakpoint
CREATE INDEX "idx_skill_versions_org_id" ON "skill_versions" USING btree ("org_id");--> statement-breakpoint
CREATE UNIQUE INDEX "idx_skill_versions_skill_v" ON "skill_versions" USING btree ("skill_id","version");--> statement-breakpoint
CREATE INDEX "idx_skills_org_id" ON "skills" USING btree ("org_id");--> statement-breakpoint
CREATE UNIQUE INDEX "idx_skills_org_name" ON "skills" USING btree ("org_id","name");--> statement-breakpoint
CREATE INDEX "idx_ventures_org_id" ON "ventures" USING btree ("org_id");--> statement-breakpoint
CREATE INDEX "idx_workflows_org_id" ON "workflows" USING btree ("org_id");