import { useState } from 'react'
import { useCockpitStore } from '../stores/cockpitStore'
import { useAgentStore } from '../stores/agentStore'
import { useChatStore } from '../stores/chatStore'
import { VoiceWaveform } from './VoiceWaveform'
import { useVoiceStore } from '../stores/voiceStore'

const MODE_COLORS: Record<string, string> = {
  EXECUTE: 'var(--accent-green)',
  PLAN: 'var(--accent-amber)',
  REVIEW: 'var(--accent-purple)',
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
        background: 'var(--bg)',
        border: '1px solid var(--border)',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
      }}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span
            className="w-2 h-2 rounded-full"
            style={{ background: MODE_COLORS[mode] }}
          />
          <span className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
            {mode}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => activeAgents.length > 0 ? handleExecutionClick() : undefined}
            className="flex items-center gap-1 px-1.5 py-0.5 rounded text-xs"
            style={{
              color: activeAgents.length > 0 ? 'var(--accent-cyan)' : 'var(--text-tertiary)',
              background: activeAgents.length > 0 ? 'var(--glow-cyan)' : 'transparent',
            }}
            title="Agents active"
          >
            <span>⬡</span>
            <span>{activeAgents.length}</span>
          </button>

          <button
            onClick={() => {
              if (micState === 'idle') window.cockpit?.voice.start()
              else window.cockpit?.voice.stop()
            }}
            className="flex items-center justify-center w-6 h-6 rounded"
            style={{
              color: micState !== 'idle' ? 'var(--accent-cyan)' : 'var(--text-tertiary)',
              background: micState !== 'idle' ? 'var(--glow-cyan)' : 'transparent',
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
            color: 'var(--text-primary)',
            border: '1px solid var(--border)',
          }}
        />
        <button
          type="submit"
          disabled={sending || !dexInput.trim()}
          className="px-2 py-1 rounded text-xs"
          style={{
            color: 'var(--accent-cyan)',
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
          style={{ color: 'var(--text-tertiary)' }}
          title="Expand"
        >
          ↑
        </button>
        <button
          onClick={() => cycleWindowMode('shrink')}
          className="text-xs px-1.5 py-0.5 rounded"
          style={{ color: 'var(--text-tertiary)' }}
          title="Shrink"
        >
          ↓
        </button>
      </div>
    </div>
  )
}
