import { useCallback, useMemo, useRef, useState } from 'react'
import { FileText } from 'lucide-react'
import { useCutStudioStore } from '../../stores/cutStudioStore'
import { isKept } from '../../utils/cutAlgorithms'
import type { Segment, Word } from '../../utils/cutAlgorithms'

/**
 * The transcript IS the editor. Words render as spans styled by whether the EDL
 * keeps them; clicking seeks, dragging selects a run, and the selection is
 * struck (or restored) from there. Filler and silence candidates are marked
 * inline so a sweep is one click away from where the operator is already
 * reading.
 */
export function TranscriptPanel() {
  const transcript = useCutStudioStore((s) => s.transcript)
  const edl = useCutStudioStore((s) => s.edl)
  const playhead = useCutStudioStore((s) => s.playhead)
  const selection = useCutStudioStore((s) => s.selection)
  const detections = useCutStudioStore((s) => s.detections)
  const setSelection = useCutStudioStore((s) => s.setSelection)
  const toggleStrike = useCutStudioStore((s) => s.toggleStrike)
  const setPlayhead = useCutStudioStore((s) => s.setPlayhead)
  const transcribe = useCutStudioStore((s) => s.transcribe)

  const [dragAnchor, setDragAnchor] = useState<Word | null>(null)
  const dragging = useRef(false)

  /** Filler word start times, for the pre-highlight marks. */
  const fillerStarts = useMemo(() => {
    const set = new Set<number>()
    for (const f of detections?.filler_words ?? []) set.add(Math.round(f.start * 1000))
    return set
  }, [detections])

  const selectedKeys = useMemo(() => {
    const set = new Set<number>()
    for (const w of selection?.words ?? []) set.add(Math.round(w.start * 1000))
    return set
  }, [selection])

  const flat = useMemo(() => (transcript ? transcript.segments.flatMap((s) => s.words) : []), [transcript])

  const selectRun = useCallback(
    (from: Word, to: Word) => {
      const lo = Math.min(from.start, to.start)
      const hi = Math.max(from.end, to.end)
      const words = flat.filter((w) => w.start >= lo - 1e-6 && w.end <= hi + 1e-6)
      if (words.length === 0) return
      // A run is "struck" only when every word in it is already cut — a mixed
      // run strikes, so dragging over a partly-cut passage removes the rest.
      const struck = words.every((w) => !isKept(edl, (w.start + w.end) / 2))
      setSelection({ words, struck })
    },
    [flat, edl, setSelection],
  )

  const onWordDown = useCallback(
    (w: Word) => {
      dragging.current = true
      setDragAnchor(w)
      selectRun(w, w)
    },
    [selectRun],
  )

  const onWordEnter = useCallback(
    (w: Word) => {
      if (!dragging.current || !dragAnchor) return
      selectRun(dragAnchor, w)
    },
    [dragAnchor, selectRun],
  )

  const onWordUp = useCallback(
    (w: Word) => {
      const wasDrag = dragging.current && dragAnchor && dragAnchor.start !== w.start
      dragging.current = false
      setDragAnchor(null)
      if (wasDrag) return // leave the run selected; S/R or the button acts on it

      // A plain click on a struck word restores it; on a kept word it seeks.
      const struck = !isKept(edl, (w.start + w.end) / 2)
      if (struck) {
        toggleStrike([w], true)
      } else {
        setPlayhead(w.start)
        setSelection(null)
      }
    },
    [dragAnchor, edl, toggleStrike, setPlayhead, setSelection],
  )

  if (!transcript) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 p-4">
        <FileText size={18} style={{ color: 'var(--color-text-tertiary)' }} />
        <p className="text-[11px] font-mono text-center" style={{ color: 'var(--color-text-secondary)' }}>
          No transcript yet — transcribe to start cutting by text.
        </p>
        <button
          type="button"
          onClick={() => void transcribe()}
          className="px-3 py-1.5 text-[10px] font-mono uppercase transition-colors"
          style={{
            background: 'var(--color-surface-raised)',
            border: '1px solid var(--color-border)',
            color: 'var(--color-violet)',
          }}
        >
          Transcribe
        </button>
      </div>
    )
  }

  return (
    <div
      className="h-full overflow-y-auto p-4 select-none"
      onMouseLeave={() => { dragging.current = false }}
    >
      {selection && selection.words.length > 0 && (
        <div
          className="sticky top-0 z-10 flex items-center gap-3 px-2 py-1.5 mb-3"
          style={{ background: 'var(--color-surface-overlay)', border: '1px solid var(--color-violet)' }}
        >
          <span className="text-[10px] font-mono" style={{ color: 'var(--color-text-secondary)' }}>
            {selection.words.length} word{selection.words.length === 1 ? '' : 's'} selected
          </span>
          <div className="flex-1" />
          <button
            type="button"
            onClick={() => toggleStrike(selection.words, selection.struck)}
            className="text-[10px] font-mono uppercase"
            style={{ color: 'var(--color-violet)' }}
          >
            {selection.struck ? 'Restore (R)' : 'Strike (S)'}
          </button>
          <button
            type="button"
            onClick={() => setSelection(null)}
            className="text-[10px] font-mono uppercase"
            style={{ color: 'var(--color-text-tertiary)' }}
          >
            Clear
          </button>
        </div>
      )}

      {transcript.segments.map((seg: Segment) => (
        <p key={seg.id} className="mb-3 leading-relaxed text-[12px]">
          {seg.words.map((w, i) => {
            const kept = isKept(edl, (w.start + w.end) / 2)
            const current = playhead >= w.start && playhead < w.end
            const selected = selectedKeys.has(Math.round(w.start * 1000))
            const filler = fillerStarts.has(Math.round(w.start * 1000))
            return (
              <span
                key={`${seg.id}-${i}`}
                onMouseDown={() => onWordDown(w)}
                onMouseEnter={() => onWordEnter(w)}
                onMouseUp={() => onWordUp(w)}
                className="cursor-pointer px-[1px]"
                style={{
                  color: kept ? 'var(--color-text-primary)' : 'var(--color-text-tertiary)',
                  textDecoration: kept ? 'none' : 'line-through',
                  background: current
                    ? 'var(--color-violet-dim)'
                    : selected
                      ? 'rgba(168, 85, 247, 0.18)'
                      : filler && kept
                        ? 'rgba(255, 184, 0, 0.14)'
                        : 'transparent',
                }}
                title={filler ? 'filler candidate' : undefined}
              >
                {w.word}{' '}
              </span>
            )
          })}
        </p>
      ))}
    </div>
  )
}
