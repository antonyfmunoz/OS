import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface Provider {
  id: string
  name: string
  type: 'ai' | 'tool' | 'service' | 'adapter'
  status: 'operational' | 'configured' | 'not_configured' | 'error' | 'unknown'
  capabilities: string[]
  risk_level: string
  api_path: string
  setup_blocker: string
  last_smoke_test: string
}

interface ProviderRegistryState {
  providers: Provider[]
  loading: boolean

  fetchProviders: () => Promise<void>
  smokeTest: (id: string) => Promise<{ success: boolean; detail: string }>
}

const KNOWN_PROVIDERS: Provider[] = [
  { id: 'claude-code', name: 'Claude Code', type: 'ai', status: 'unknown', capabilities: ['code-gen', 'analysis', 'refactor', 'test'], risk_level: 'low', api_path: 'cc_sdk', setup_blocker: '', last_smoke_test: '' },
  { id: 'codex', name: 'Codex', type: 'ai', status: 'unknown', capabilities: ['code-gen', 'parallel-exec'], risk_level: 'medium', api_path: 'codex', setup_blocker: '', last_smoke_test: '' },
  { id: 'gemini', name: 'Gemini', type: 'ai', status: 'unknown', capabilities: ['generation', 'analysis'], risk_level: 'low', api_path: 'gemini', setup_blocker: '', last_smoke_test: '' },
  { id: 'groq', name: 'Groq', type: 'ai', status: 'unknown', capabilities: ['fast-inference'], risk_level: 'low', api_path: 'groq', setup_blocker: '', last_smoke_test: '' },
  { id: 'ollama', name: 'Ollama', type: 'ai', status: 'unknown', capabilities: ['local-inference'], risk_level: 'low', api_path: 'ollama', setup_blocker: '', last_smoke_test: '' },
  { id: 'shell', name: 'Shell', type: 'tool', status: 'operational', capabilities: ['command-exec', 'file-ops', 'git'], risk_level: 'high', api_path: 'shell', setup_blocker: '', last_smoke_test: '' },
  { id: 'github', name: 'GitHub', type: 'service', status: 'unknown', capabilities: ['pr', 'issues', 'actions'], risk_level: 'medium', api_path: 'github', setup_blocker: '', last_smoke_test: '' },
  { id: 'docs', name: 'Documentation', type: 'adapter', status: 'operational', capabilities: ['wiki', 'skills', 'knowledge'], risk_level: 'low', api_path: 'docs', setup_blocker: '', last_smoke_test: '' },
]

export const useProviderRegistryStore = create<ProviderRegistryState>((set) => ({
  providers: KNOWN_PROVIDERS,
  loading: false,

  fetchProviders: async () => {
    set({ loading: true })
    try {
      const models = await fetchApi<Record<string, unknown>>('/models').catch(() => null)
      const infra = await fetchApi<Record<string, unknown>>('/infra').catch(() => null)

      set((s) => ({
        loading: false,
        providers: s.providers.map((p) => {
          if (p.id === 'claude-code' && models) {
            return { ...p, status: 'operational' as const, last_smoke_test: new Date().toISOString() }
          }
          if (p.id === 'gemini' && models) {
            const hasGemini = JSON.stringify(models).toLowerCase().includes('gemini')
            return { ...p, status: hasGemini ? 'configured' as const : 'not_configured' as const }
          }
          if (p.id === 'ollama' && infra) {
            const hasOllama = JSON.stringify(infra).toLowerCase().includes('ollama')
            return { ...p, status: hasOllama ? 'configured' as const : 'not_configured' as const }
          }
          return p
        }),
      }))
    } catch {
      set({ loading: false })
    }
  },

  smokeTest: async (id: string) => {
    try {
      const result = await fetchApi<{ success: boolean; detail: string }>(`/models/smoke-test/${id}`, {
        method: 'POST',
        body: JSON.stringify({}),
      }).catch(() => ({ success: false, detail: 'smoke test endpoint not available' }))

      set((s) => ({
        providers: s.providers.map((p) =>
          p.id === id ? { ...p, status: result.success ? 'operational' as const : 'error' as const, last_smoke_test: new Date().toISOString() } : p
        ),
      }))

      return result
    } catch {
      return { success: false, detail: 'smoke test failed' }
    }
  },
}))
