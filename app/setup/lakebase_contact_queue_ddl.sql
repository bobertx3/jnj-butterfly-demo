-- Run this in batch_release_db (e.g. via Databricks SQL or psql) to create tables for the Prioritized Contact Queue UI.
-- Requires CREATE on public (or run as an admin).

-- Contact queue: one row per contact for the left panel and detail view.
CREATE TABLE IF NOT EXISTS public.contact_queue (
  id SERIAL PRIMARY KEY,
  contact_id VARCHAR(32) NOT NULL UNIQUE,
  name VARCHAR(128) NOT NULL,
  role_specialty VARCHAR(64),
  institution VARCHAR(128),
  priority_score NUMERIC(5,2) NOT NULL DEFAULT 0,
  intent_score INT NOT NULL DEFAULT 0,
  risk_level VARCHAR(16) NOT NULL DEFAULT 'Medium',
  preferred_channel VARCHAR(32) DEFAULT 'Email',
  last_touch_days INT NOT NULL DEFAULT 0,
  last_interaction_channel VARCHAR(32),
  last_interaction_date DATE,
  last_interaction_summary TEXT,
  last_products_discussed TEXT,
  next_follow_up_objective TEXT,
  trx_volume_3m INT DEFAULT 0,
  nrx_volume_3m INT DEFAULT 0,
  site_visits INT DEFAULT 0,
  webinar_signups INT DEFAULT 0,
  rx_growth_3m_pct NUMERIC(6,2),
  territory_id VARCHAR(32),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Backward-compatible migration for already-created environments.
ALTER TABLE IF EXISTS public.contact_queue ADD COLUMN IF NOT EXISTS last_interaction_channel VARCHAR(32);
ALTER TABLE IF EXISTS public.contact_queue ADD COLUMN IF NOT EXISTS last_interaction_date DATE;
ALTER TABLE IF EXISTS public.contact_queue ADD COLUMN IF NOT EXISTS last_interaction_summary TEXT;
ALTER TABLE IF EXISTS public.contact_queue ADD COLUMN IF NOT EXISTS last_products_discussed TEXT;
ALTER TABLE IF EXISTS public.contact_queue ADD COLUMN IF NOT EXISTS next_follow_up_objective TEXT;

-- AI-generated next best action and email draft per contact (written when user clicks Generate NBA / Generate Email Draft).
CREATE TABLE IF NOT EXISTS public.nba_recommendation (
  id SERIAL PRIMARY KEY,
  contact_id VARCHAR(32) NOT NULL UNIQUE,
  recommendation_text TEXT,
  email_draft_subject VARCHAR(256),
  email_draft_body TEXT,
  generated_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
