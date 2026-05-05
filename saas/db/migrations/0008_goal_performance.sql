-- Phase 9E: Outcome-Driven Reweighting
-- Add performance profile to goals + outcome tracking table

-- Performance profile on goals (JSONB for flexible evolution)
ALTER TABLE goals ADD COLUMN IF NOT EXISTS performance JSONB DEFAULT '{}';

-- Goal outcomes table — records every task result linked to a goal
CREATE TABLE IF NOT EXISTS goal_outcomes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID NOT NULL REFERENCES organizations(id),
    goal_id         TEXT NOT NULL REFERENCES goals(id),
    outcome_type    TEXT NOT NULL CHECK (outcome_type IN ('success', 'failure', 'partial')),
    task_type       TEXT DEFAULT '',
    execution_time  FLOAT DEFAULT 0.0,
    impact_delta    FLOAT DEFAULT 0.0,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_goal_outcomes_goal ON goal_outcomes(goal_id);
CREATE INDEX IF NOT EXISTS idx_goal_outcomes_org ON goal_outcomes(org_id);
CREATE INDEX IF NOT EXISTS idx_goal_outcomes_created ON goal_outcomes(created_at);
CREATE INDEX IF NOT EXISTS idx_goal_outcomes_goal_created ON goal_outcomes(goal_id, created_at);

ALTER TABLE goal_outcomes ENABLE ROW LEVEL SECURITY;

CREATE POLICY goal_outcomes_org_isolation ON goal_outcomes
    USING (org_id = current_setting('app.current_org_id')::uuid);
