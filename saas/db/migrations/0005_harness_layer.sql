CREATE TABLE IF NOT EXISTS cross_product_permissions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  source_product TEXT NOT NULL,
  target_product TEXT NOT NULL,
  data_category TEXT NOT NULL,
  permitted BOOLEAN DEFAULT false,
  granted_at TIMESTAMPTZ,
  revoked_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, source_product, target_product, data_category)
);

CREATE TABLE IF NOT EXISTS user_intelligence_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) UNIQUE,
  communication_style JSONB DEFAULT '{}',
  peak_performance_windows JSONB DEFAULT '[]',
  decision_patterns JSONB DEFAULT '{}',
  content_strengths JSONB DEFAULT '{}',
  learning_style JSONB DEFAULT '{}',
  stress_indicators JSONB DEFAULT '{}',
  north_star TEXT,
  cross_product_insights JSONB DEFAULT '{}',
  last_updated TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS product_connections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  product TEXT NOT NULL,
  connection_config JSONB DEFAULT '{}',
  status TEXT DEFAULT 'disconnected',
  connected_at TIMESTAMPTZ,
  last_sync TIMESTAMPTZ
);

ALTER TABLE cross_product_permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_intelligence_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_connections ENABLE ROW LEVEL SECURITY;
