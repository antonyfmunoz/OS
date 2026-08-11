import { useCallback, useEffect, useRef, useState } from 'react'
import { ArrowLeft } from 'lucide-react'
import { useCutStudioStore } from '../../stores/cutStudioStore'
import { ProjectList } from './ProjectList'
import { TranscriptPanel } from './TranscriptPanel'
import { PreviewPlayer } from './PreviewPlayer'
import { Timeline } from './Timeline'
import { ChatPanel } from './ChatPanel'
import { HighlightsPanel } from './HighlightsPanel'
import { DetectBar } from './DetectBar'
import { RenderBar } from './RenderBar'

type Tab = 'chat' | 'highlights' | 'detect'

const TABS: Array<{ id: Tab; label: string }> = [
  { id: 'chat', label: 'Chat' },
  { id: 'highlights', label: 'Highlights' },
  { id: 'detect', label: 'Detect' },
]

/**
 * CutStudio — transcript-based video editing as a cockpit instrument.
 *
 * The panel is self-contained: it adds a surface inside the existing cockpit
 * layout and changes nothing about the shell around it.
 */
export function CutStudioPanel() {
  const project = useCutStudioStore((s) => s.project)
  const edl = useCutStudioStore((s) => s.edl)
  const dirty = useCutStudioStore((s) => s.dirty)
  const saving = useCutStudioStore((s) => s.saving)
  const error = useCutStudioStore((s) => s.error)
  const notice = useCutStudioStore((s) => s.notice)
  const selection = useCutStudioStore((s) => s.selection)
  const playhead = useCutStudioStore((s) => s.playhead)
  const closeProject = useCutStudioStore((s) => s.closeProject)
  const clearNotice = useCutStudioStore((s) => s.clearNotice)
  const toggleStrike = useCutStudioStore((s) => s.toggleStrike)
  const setPlayhead = useCutStudioStore((s) => s.setPlayhead)
  const saveEdl = useCutStudioStore((s) => s.saveEdl)
  const undo = useCutStudioStore((s) => s.undo)
  const redo = useCutStudioStore((s) => s.redo)
  const stopJobPolling = useCutStudioStore((s) => s.stopJobPolling)

  const rootRef = useRef<HTMLDivElement | null>(null)
  const [tab, setTab] = useState<Tab>('chat')

  useEffect(() => () => stopJobPolling(), [stopJobPolling])

  /**
   * Shortcuts are bound to the panel root, not window: a window listener would
   * clobber space/S/R across every other cockpit surface. The root is
   * focusable and autofocused so the keys work as soon as the panel opens.
   */
  const onKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      const target = e.target as HTMLElement
      const tag = target.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || target.isContentEditable) return

      const mod = e.metaKey || e.ctrlKey
      if (mod && e.key.toLowerCase() === 'z') {
        e.preventDefault()
        if (e.shiftKey) redo()
        else undo()
        return
      }
      if (mod && e.key.toLowerCase() === 's') {
        e.preventDefault()
        void saveEdl()
        return
      }
      if (mod) return

      switch (e.key) {
        case ' ': {
          e.preventDefault()
          const video = rootRef.current?.querySelector('video')
          if (video) {
            if (video.paused) void video.play().catch(() => { /* gesture guard */ })
            else video.pause()
          }
          break
        }
        case 's':
        case 'S':
          if (selection && selection.words.length > 0) {
            e.preventDefault()
            toggleStrike(selection.words, false)
          }
          break
        case 'r':
        case 'R':
          if (selection && selection.words.length > 0) {
            e.preventDefault()
            toggleStrike(selection.words, true)
          }
          break
        case 'ArrowLeft':
          e.preventDefault()
          setPlayhead(Math.max(0, playhead - 5))
          break
        case 'ArrowRight':
          e.preventDefault()
          setPlayhead(Math.min(project?.duration || playhead + 5, playhead + 5))
          break
        default:
          break
      }
    },
    [selection, playhead, project, toggleStrike, setPlayhead, saveEdl, undo, redo],
  )

  if (!project) {
    return (
      <div className="h-full" style={{ background: 'var(--color-surface)' }}>
        <ProjectList />
      </div>
    )
  }

  return (
    <div
      ref={rootRef}
      tabIndex={-1}
      onKeyDown={onKeyDown}
      autoFocus
      className="flex flex-col h-full outline-none"
      style={{ background: 'var(--color-surface)' }}
    >
      <div className="flex items-center gap-2 px-3 h-9 shrink-0" style={{ borderBottom: '1px solid var(--color-border)' }}>
        <button
          type="button"
          onClick={closeProject}
          className="flex items-center gap-1.5 text-[10px] font-mono uppercase"
          style={{ color: 'var(--color-text-tertiary)' }}
        >
          <ArrowLeft size={11} />
          Projects
        </button>
        <span className="text-[11px] font-mono truncate" style={{ color: 'var(--color-text-primary)' }}>
          {project.name}
        </span>
        <div className="flex-1" />
        <span className="text-[10px] font-mono" style={{ color: dirty ? 'var(--color-warn)' : 'var(--color-text-tertiary)' }}>
          {saving ? 'saving' : dirty ? 'unsaved' : 'saved'}
        </span>
      </div>

      {(error || notice) && (
        <button
          type="button"
          onClick={clearNotice}
          className="px-3 py-1 text-left text-[10px] font-mono shrink-0"
          style={{
            background: 'var(--color-surface-overlay)',
            borderBottom: '1px solid var(--color-border)',
            color: error ? 'var(--color-danger)' : 'var(--color-text-secondary)',
          }}
        >
          {error || notice}
        </button>
      )}

      <div className="flex flex-1 min-h-0">
        <div className="w-[42%] min-w-[280px] overflow-hidden" style={{ borderRight: '1px solid var(--color-border)' }}>
          <TranscriptPanel />
        </div>

        <div className="flex-1 flex flex-col min-w-0">
          <PreviewPlayer />
          <Timeline />

          <div className="flex shrink-0" style={{ borderBottom: '1px solid var(--color-border)' }}>
            {TABS.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setTab(t.id)}
                className="px-3 py-1.5 text-[10px] font-mono uppercase transition-colors"
                style={{
                  color: tab === t.id ? 'var(--color-violet)' : 'var(--color-text-tertiary)',
                  borderBottom: tab === t.id ? '1px solid var(--color-violet)' : '1px solid transparent',
                }}
              >
                {t.label}
              </button>
            ))}
          </div>

          <div className="flex-1 min-h-0 overflow-hidden">
            {tab === 'chat' && <ChatPanel />}
            {tab === 'highlights' && <HighlightsPanel />}
            {tab === 'detect' && <DetectBar />}
          </div>

          <RenderBar />
        </div>
      </div>
    </div>
  )
}
