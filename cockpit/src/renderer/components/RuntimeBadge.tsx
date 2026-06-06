function normalizeRuntime(runtime: string): string {
  const value = runtime.toLowerCase().replace(/_/g, '-')
  if (value.includes('claude')) return 'claude-code'
  if (value.includes('codex')) return 'codex'
  if (value.includes('hermes')) return 'hermes'
  if (value.includes('browser') || value.includes('playwright')) return 'browser'
  if (value.includes('shell') || value.includes('tmux') || value.includes('ssh') || value === 'process') return 'shell'
  if (value.includes('local-model') || value.includes('ollama')) return 'local-model'
  return value
}

export const RUNTIME_COLORS: Record<string, { color: string; bg: string; label: string }> = {
  'claude-code': {
    color: 'var(--color-runtime-claude)',
    bg: 'var(--color-runtime-claude-bg)',
    label: 'CLAUDE',
  },
  codex: {
    color: 'var(--color-runtime-codex)',
    bg: 'var(--color-runtime-codex-bg)',
    label: 'CODEX',
  },
  hermes: {
    color: 'var(--color-runtime-hermes)',
    bg: 'var(--color-runtime-hermes-bg)',
    label: 'HERMES',
  },
  shell: {
    color: 'var(--color-runtime-shell)',
    bg: 'var(--color-runtime-shell-bg)',
    label: 'SHELL',
  },
  browser: {
    color: 'var(--color-runtime-browser)',
    bg: 'var(--color-runtime-browser-bg)',
    label: 'BROWSER',
  },
  'local-model': {
    color: 'var(--color-runtime-local-model)',
    bg: 'var(--color-runtime-local-model-bg)',
    label: 'LOCAL',
  },
}

interface RuntimeBadgeProps {
  runtime: string
}

export function RuntimeBadge({ runtime }: RuntimeBadgeProps) {
  const normalized = normalizeRuntime(runtime)
  const config = RUNTIME_COLORS[normalized] || {
    color: 'var(--color-text-tertiary)',
    bg: 'var(--color-surface-raised)',
    label: normalized.toUpperCase(),
  }

  return (
    <span
      className="wv-runtime-badge"
      style={{ color: config.color, background: config.bg }}
    >
      {config.label}
    </span>
  )
}
