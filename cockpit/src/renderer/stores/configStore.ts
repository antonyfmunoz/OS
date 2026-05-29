import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface UmhConfig {
  ai_name: string
  timezone: string
  locale: string
  theme: string
  founder_name: string
  org_name: string
  [key: string]: unknown
}

interface ConfigState {
  config: UmhConfig
  loaded: boolean
  aiName: string

  loadConfig: () => Promise<void>
  setConfigValue: (key: string, value: unknown) => Promise<void>
  applyRemoteUpdate: (key: string, value: unknown) => void
}

const FALLBACK_AI_NAME = import.meta.env.VITE_AI_NAME || 'Assistant'

const DEFAULT_CONFIG: UmhConfig = {
  ai_name: FALLBACK_AI_NAME,
  timezone: 'UTC',
  locale: 'en',
  theme: 'dark',
  founder_name: '',
  org_name: '',
}

export const useConfigStore = create<ConfigState>((set, get) => ({
  config: { ...DEFAULT_CONFIG },
  loaded: false,
  aiName: FALLBACK_AI_NAME,

  loadConfig: async () => {
    try {
      const data = await fetchApi<UmhConfig>('/config')
      const aiName = (data.ai_name as string) || FALLBACK_AI_NAME
      set({
        config: { ...DEFAULT_CONFIG, ...data },
        loaded: true,
        aiName,
      })
    } catch {
      set({ loaded: true })
    }
  },

  setConfigValue: async (key: string, value: unknown) => {
    try {
      await fetchApi('/config', {
        method: 'PATCH',
        body: JSON.stringify({ key, value, layer: 'system' }),
      })
      const prev = get().config
      const updated = { ...prev, [key]: value }
      set({
        config: updated,
        aiName: key === 'ai_name' ? (value as string) || FALLBACK_AI_NAME : get().aiName,
      })
    } catch (err) {
      console.error('[configStore] setConfigValue failed:', err)
    }
  },

  applyRemoteUpdate: (key: string, value: unknown) => {
    const prev = get().config
    set({
      config: { ...prev, [key]: value },
      aiName: key === 'ai_name' ? (value as string) || FALLBACK_AI_NAME : get().aiName,
    })
  },
}))
