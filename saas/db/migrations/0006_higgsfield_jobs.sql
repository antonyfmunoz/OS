-- Higgsfield Cloud API job tracking.
-- Every submit via eos_ai/higgsfield_client.generate() inserts a row here
-- BEFORE the SDK submits to platform.higgsfield.ai. The webhook handler at
-- services/higgsfield_webhook.py validates that the incoming request_id
-- exists in this table before acting on the payload (idempotency +
-- EOS-issued validation in one check).

CREATE TABLE IF NOT EXISTS higgsfield_jobs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  request_id      TEXT NOT NULL UNIQUE,
  venture         TEXT NOT NULL,
  model_id        TEXT NOT NULL,
  arguments       JSONB NOT NULL DEFAULT '{}'::jsonb,
  status          TEXT NOT NULL DEFAULT 'queued',
  -- queued | in_progress | Completed | Failed | NSFW | Cancelled
  output_url      TEXT,
  local_path      TEXT,
  error           TEXT,
  submitted_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at     TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS higgsfield_jobs_status_idx
  ON higgsfield_jobs (status);
CREATE INDEX IF NOT EXISTS higgsfield_jobs_venture_submitted_idx
  ON higgsfield_jobs (venture, submitted_at DESC);
CREATE INDEX IF NOT EXISTS higgsfield_jobs_model_id_idx
  ON higgsfield_jobs (model_id);
