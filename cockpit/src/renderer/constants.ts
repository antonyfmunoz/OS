import { useConfigStore } from './stores/configStore'

export const FALLBACK_AI_NAME = import.meta.env.VITE_AI_NAME || 'Assistant'

export function getAiName(): string {
  return useConfigStore.getState().aiName || FALLBACK_AI_NAME
}
