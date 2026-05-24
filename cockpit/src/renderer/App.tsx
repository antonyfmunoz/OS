import { useEffect } from 'react'
import { Shell } from './components/Shell'
import { useKeyboard } from './hooks/useKeyboard'
import { useWebSocket } from './hooks/useWebSocket'
import { useChatStore } from './stores/chatStore'

export function App() {
  useKeyboard()
  useWebSocket()

  const loadHistory = useChatStore((s) => s.loadHistory)

  useEffect(() => {
    loadHistory()
  }, [loadHistory])

  return <Shell />
}
