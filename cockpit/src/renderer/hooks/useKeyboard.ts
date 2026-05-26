import { useEffect } from 'react'
import { useCockpitStore, type Panel } from '../stores/cockpitStore'
import { useVoiceStore } from '../stores/voiceStore'
import { startVoice, stopVoice } from '../api/voice-controller'

const PANEL_KEYS: Record<string, Panel> = {
  '1': 'dashboard',
  '2': 'agents',
  '3': 'tasks',
  '4': 'approvals',
  '5': 'knowledge',
  '6': 'analytics',
  '7': 'editor',
  '8': 'settings',
  '9': 'activity',
  '0': 'execution',
  'p': 'portfolio',
  'c': 'company',
}

export function useKeyboard(): void {
  const setPanel = useCockpitStore((s) => s.setPanel)
  const toggleChat = useCockpitStore((s) => s.toggleChat)
  const cycleWindowMode = useCockpitStore((s) => s.cycleWindowMode)

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent): void {
      if (e.ctrlKey && e.shiftKey && e.key === 'M') {
        e.preventDefault()
        cycleWindowMode('shrink')
        return
      }

      if (e.ctrlKey && e.shiftKey && e.key === 'V') {
        e.preventDefault()
        const mic = useVoiceStore.getState().micState
        if (mic === 'idle') startVoice()
        else stopVoice()
        return
      }

      if (e.ctrlKey && !e.shiftKey && !e.altKey) {
        const panel = PANEL_KEYS[e.key]
        if (panel) {
          e.preventDefault()
          setPanel(panel)
          return
        }
        if (e.key === '/') {
          e.preventDefault()
          toggleChat()
          return
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [setPanel, toggleChat, cycleWindowMode])
}
