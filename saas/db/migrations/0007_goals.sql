-- Phase 9D: Goal Selection + System Focus Layer
-- Goals table with scoring, states, and focus budget support

CREATE TABLE IF NOT EXISTS goals (
    id              TEXT PRIMARY KEY,
    org_id          UUID NOT NULL REFERENCES organizations(id),
    title           TEXT NOT NULL,
    description     TEXT DEFAULT '',
    state           TEXT NOT NULL DEFAULT 'deferred'
                    CHECK (state IN ('active', 'deferred', 'blocked', 'completed', 'dropped')),
    priority        INTEGER DEFAULT 5 CHECK (priority BETWEEN 1 AND 10),
    expected_impact FLOAT DEFAULT 0.5 CHECK (expected_impact BETWEEN 0.0 AND 1.0),
    estimated_cost  FLOAT DEFAULT 0.5 CHECK (estimated_cost BETWEEN 0.0 AND 1.0),
    confidence      FLOAT DEFAULT 0.5 CHECK (confidence BETWEEN 0.0 AND 1.0),
    dependency_unlock INTEGER DEFAULT 0,
    venture_id      UUID REFERENCES ventures(id),
    blocked_by      JSONB DEFAULT '[]',
    score           FLOAT DEFAULT 0.0,
    rank            INTEGER DEFAULT 0,
    score_explanation JSONB DEFAULT '[]',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_goals_org_id ON goals(org_id);
CREATE INDEX IF NOT EXISTS idx_goals_state ON goals(state);
CREATE INDEX IF NOT EXISTS idx_goals_org_state ON goals(org_id, state);
CREATE INDEX IF NOT EXISTS idx_goals_venture ON goals(venture_id);

ALTER TABLE goals ENABLE ROW LEVEL SECURITY;

CREATE POLICY goals_org_isolation ON goals
    USING (org_id = current_setting('app.current_org_id')::uuid);
