import { useCallback, useState } from 'react'
import { Send } from 'lucide-react'
import { useCutStudioStore } from '../../stores/cutStudioStore'
import { edlDiffSummary } from '../../utils/cutAlgorithms'

/**
 * Chat-to-edit. An instruction returns an EDL PROPOSAL, never a saved edit —
 * the operator sees what it would keep and decides. Discard leaves the current
 * cut untouched.
 */
export function ChatPanel() {
  const chat = useCutStudioStore((s) => s.chat)
  const chatSending = useCutStudioStore((s) => s.chatSending)
  const edl = useCutStudioStore((s) => s.edl)
  const pendingAiEdl = useCutStudioStore((s) => s.pendingAiEdl)
  const pendingAiNote = useCutStudioStore((s) => s.pendingAiNote)
  const aiEdit = useCutStudioStore((s) => s.aiEdit)
  const applyAiEdl = useCutStudioStore((s) => s.applyAiEdl)
  const discardAiEdl = useCutStudioStore((s) => s.discardAiEdl)

  const [input, setInput] = useState('')

  const submit = useCallback(() => {
    const text = input.trim()
    if (!text || chatSending) return
    setInput('')
    void aiEdit(text)
  }, [input, chatSending, aiEdit])

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {chat.length === 0 && (
          <p className="text-[11px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
            Describe the cut you want — "drop the intro rambling", "keep only the
            part about pricing".
          </p>
        )}
        {chat.map((m) => (
          <div key={m.id} className="text-[11px] font-mono leading-relaxed">
            <span
              className="uppercase mr-2 text-[9px]"
              style={{ color: m.role === 'operator' ? 'var(--color-cyan)' : 'var(--color-violet)' }}
            >
              {m.role === 'operator' ? 'you' : 'cut'}
            </span>
            <span style={{ color: 'var(--color-text-primary)' }}>{m.text}</span>
          </div>
        ))}
        {chatSending && (
          <p className="text-[10px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
            Thinking...
          </p>
        )}
      </div>

      {pendingAiEdl && (
        <div className="p-3 shrink-0" style={{ borderTop: '1px solid var(--color-violet)', background: 'var(--color-surface-overlay)' }}>
          <div className="text-[10px] font-mono uppercase mb-1" style={{ color: 'var(--color-violet)' }}>
            Proposed cut
          </div>
          <div className="text-[11px] font-mono" style={{ color: 'var(--color-text-primary)' }}>
            {edlDiffSummary(edl, pendingAiEdl)}
          </div>
          {pendingAiNote && (
            <div className="text-[10px] font-mono mt-1" style={{ color: 'var(--color-text-secondary)' }}>
              {pendingAiNote}
            </div>
          )}
          <div className="flex gap-2 mt-2">
            <button
              type="button"
              onClick={applyAiEdl}
              className="px-3 py-1 text-[10px] font-mono uppercase"
              style={{ border: '1px solid var(--color-violet)', color: 'var(--color-violet)' }}
            >
              Apply
            </button>
            <button
              type="button"
              onClick={discardAiEdl}
              className="px-3 py-1 text-[10px] font-mono uppercase"
              style={{ border: '1px solid var(--color-border)', color: 'var(--color-text-tertiary)' }}
            >
              Discard
            </button>
          </div>
        </div>
      )}

      <div className="flex items-center gap-2 p-2 shrink-0" style={{ borderTop: '1px solid var(--color-border)' }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              submit()
            }
            // Editing keys must not reach the panel's shortcut handler.
            e.stopPropagation()
          }}
          placeholder="Describe an edit..."
          className="flex-1 min-w-0 px-2 py-1 text-[11px] font-mono outline-none"
          style={{
            background: 'var(--color-surface-raised)',
            border: '1px solid var(--color-border)',
            color: 'var(--color-text-primary)',
          }}
        />
        <button
          type="button"
          onClick={submit}
          disabled={chatSending || !input.trim()}
          className="shrink-0 p-1"
          style={{ color: chatSending || !input.trim() ? 'var(--color-text-tertiary)' : 'var(--color-violet)' }}
          title="Send"
        >
          <Send size={12} />
        </button>
      </div>
    </div>
  )
}
