// lib/env.ts
// Single source of truth for all env vars used in lib/
// All lib/ files import from here — never process.env directly

export function getAnthropicApiKey(): string {
  const key =
    process.env.AI_INTEGRATIONS_ANTHROPIC_API_KEY ||
    process.env.ANTHROPIC_API_KEY;
  if (!key) throw new Error('Missing Anthropic API key. Set ANTHROPIC_API_KEY in .env');
  return key;
}

export function getAnthropicBaseUrl(): string {
  return (
    process.env.AI_INTEGRATIONS_ANTHROPIC_BASE_URL ||
    'https://api.anthropic.com'
  );
}

export function getDatabaseUrl(): string {
  const url = process.env.DATABASE_URL;
  if (!url) throw new Error('Missing DATABASE_URL in .env');
  return url;
}

export function getGeminiApiKey(): string | undefined {
  return process.env.GEMINI_API_KEY;
}
