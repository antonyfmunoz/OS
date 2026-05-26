import { useState } from 'react'
import { useCockpitStore } from '../stores/cockpitStore'
import { useAgentStore } from '../stores/agentStore'
import { useChatStore } from '../stores/chatStore'
import { VoiceWaveform } from './VoiceWaveform'
import { useVoiceStore } from '../stores/voiceStore'
import { startVoice, stopVoice } from '../api/voice-controller'

const MODE_COLORS: Record<string, string> = {
  EXECUTE: 'var(--color-ok)',
  PLAN: 'var(--color-warn)',
  REVIEW: 'var(--color-violet)',
}

export function FabLarge() {
  const mode = useCockpitStore((s) => s.mode)
  const cycleWindowMode = useCockpitStore((s) => s.cycleWindowMode)
  const setWindowMode = useCockpitStore((s) => s.setWindowMode)
  const setPanel = useCockpitStore((s) => s.setPanel)
  const agents = useAgentStore((s) => s.agents)
  const sendMessage = useChatStore((s) => s.sendMessage)
  const sending = useChatStore((s) => s.sending)
  const micState = useVoiceStore((s) => s.micState)
  const [dexInput, setDexInput] = useState('')

  const activeAgents = agents.filter((a) => a.status === 'active' || a.status === 'running')

  function handleDexSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (dexInput.trim() && !sending) {
      sendMessage(dexInput.trim())
      setDexInput('')
    }
  }

  function handleExecutionClick() {
    setWindowMode('maximized')
    setTimeout(() => setPanel('execution'), 50)
  }

  return (
    <div
      className="flex flex-col gap-2 p-3 rounded-lg select-none"
      style={{
        width: 280,
        background: 'var(--color-canvas)',
        border: '1px solid var(--color-border)',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
      }}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span
            className="w-2 h-2 rounded-full"
            style={{ background: MODE_COLORS[mode] }}
          />
          <span className="text-xs font-medium" style={{ color: 'var(--color-text-secondary)' }}>
            {mode}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => activeAgents.length > 0 ? handleExecutionClick() : undefined}
            className="flex items-center gap-1 px-1.5 py-0.5 rounded text-xs"
            style={{
              color: activeAgents.length > 0 ? 'var(--color-cyan)' : 'var(--color-text-tertiary)',
              background: activeAgents.length > 0 ? 'var(--color-cyan-glow)' : 'transparent',
            }}
            title="Agents active"
          >
            <span>⬡</span>
            <span>{activeAgents.length}</span>
          </button>

          <button
            onClick={() => {
              if (micState === 'idle') startVoice()
              else stopVoice()
            }}
            className="flex items-center justify-center w-6 h-6 rounded"
            style={{
              color: micState !== 'idle' ? 'var(--color-cyan)' : 'var(--color-text-tertiary)',
              background: micState !== 'idle' ? 'var(--color-cyan-glow)' : 'transparent',
            }}
            title="Voice"
          >
            {micState !== 'idle' ? <VoiceWaveform /> : <span className="text-xs">🎤</span>}
          </button>
        </div>
      </div>

      <form onSubmit={handleDexSubmit} className="flex gap-1.5">
        <input
          value={dexInput}
          onChange={(e) => setDexInput(e.target.value)}
          placeholder="Ask DEX..."
          className="flex-1 px-2 py-1 rounded text-xs bg-transparent outline-none"
          style={{
            color: 'var(--color-text-primary)',
            border: '1px solid var(--color-border)',
          }}
        />
        <button
          type="submit"
          disabled={sending || !dexInput.trim()}
          className="px-2 py-1 rounded text-xs"
          style={{
            color: 'var(--color-cyan)',
            opacity: sending || !dexInput.trim() ? 0.4 : 1,
          }}
        >
          ↵
        </button>
      </form>

      <div className="flex items-center justify-between">
        <button
          onClick={() => cycleWindowMode('expand')}
          className="text-xs px-1.5 py-0.5 rounded"
          style={{ color: 'var(--color-text-tertiary)' }}
          title="Expand"
        >
          ↑
        </button>
        <button
          onClick={() => cycleWindowMode('shrink')}
          className="text-xs px-1.5 py-0.5 rounded"
          style={{ color: 'var(--color-text-tertiary)' }}
          title="Shrink"
        >
          ↓
        </button>
      </div>
    </div>
  )
}
