import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useCutStudioStore } from '../../stores/cutStudioStore'
import {
  MIN_CLIP,
  allWords,
  edlDuration,
  fmtTime,
  outputToSource,
  replaceClip,
  snapToWord,
  sourceToOutput,
} from '../../utils/cutAlgorithms'

const EDGE_HIT = 8

interface DragState {
  index: number
  edge: 'start' | 'end'
}

/**
 * Source-time timeline: the full media as a muted track with kept clips drawn
 * over it, plus the playhead. Clicking seeks; dragging a clip edge trims it,
 * snapping to word boundaries so a trim lands on speech, not mid-syllable.
 */
export function Timeline() {
  const edl = useCutStudioStore((s) => s.edl)
  const project = useCutStudioStore((s) => s.project)
  const transcript = useCutStudioStore((s) => s.transcript)
  const playhead = useCutStudioStore((s) => s.playhead)
  const setPlayhead = useCutStudioStore((s) => s.setPlayhead)
  const setClips = useCutStudioStore((s) => s.setClips)

  const trackRef = useRef<HTMLDivElement | null>(null)
  const [drag, setDrag] = useState<DragState | null>(null)

  const words = useMemo(() => allWords(transcript), [transcript])
  // Source duration is project metadata (ffprobe at upload), not part of the
  // EDL body; the transcript is the fallback before the project list loads.
  const total = project?.duration || transcript?.duration || 0

  const timeAt = useCallback(
    (clientX: number): number => {
      const el = trackRef.current
      if (!el || !total) return 0
      const rect = el.getBoundingClientRect()
      const ratio = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width))
      return ratio * total
    },
    [total],
  )

  // Edge drags track on the window: the pointer routinely leaves the 24px-tall
  // track while trimming, and a track-scoped listener would drop the gesture.
  useEffect(() => {
    if (!drag) return
    const onMove = (e: MouseEvent) => {
      const current = useCutStudioStore.getState().edl
      if (!current) return
      const clip = current.clips[drag.index]
      if (!clip) return
      const raw = timeAt(e.clientX)
      const snapped = snapToWord(words, raw)
      const next =
        drag.edge === 'start'
          ? { start: Math.min(snapped, clip.end - MIN_CLIP), end: clip.end }
          : { start: clip.start, end: Math.max(snapped, clip.start + MIN_CLIP) }
      setClips(replaceClip(current, drag.index, next))
    }
    const onUp = () => setDrag(null)
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
  }, [drag, words, timeAt, setClips])

  const onTrackClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (drag) return
      const outputTotal = edlDuration(edl)
      if (!outputTotal) return
      // Clicking the source track seeks through the OUTPUT mapping, so a click
      // inside removed material lands on the nearest kept frame instead of a
      // position the cut never plays.
      setPlayhead(outputToSource(edl, sourceToOutput(edl, timeAt(e.clientX))))
    },
    [drag, edl, timeAt, setPlayhead],
  )

  if (!edl || !total) return null

  const pctOf = (t: number) => (t / total) * 100

  return (
    <div className="px-3 py-2 shrink-0" style={{ borderBottom: '1px solid var(--color-border)' }}>
      <div className="flex items-center justify-between mb-1">
        <span className="text-[10px] font-mono uppercase" style={{ color: 'var(--color-text-tertiary)' }}>
          Timeline
        </span>
        <span className="text-[10px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
          {edl.clips.length} clip{edl.clips.length === 1 ? '' : 's'} · {fmtTime(edlDuration(edl))} of {fmtTime(total)}
        </span>
      </div>

      <div
        ref={trackRef}
        onClick={onTrackClick}
        className="relative h-6 cursor-pointer"
        style={{ background: 'var(--color-surface-raised)', border: '1px solid var(--color-border)' }}
      >
        {edl.clips.map((c, i) => (
          <div
            key={`${i}-${c.start}`}
            className="absolute top-0 bottom-0"
            style={{
              left: `${pctOf(c.start)}%`,
              width: `${pctOf(c.end - c.start)}%`,
              background: 'var(--color-violet-dim)',
              borderLeft: '1px solid var(--color-violet)',
              borderRight: '1px solid var(--color-violet)',
            }}
          >
            <div
              onMouseDown={(e) => {
                e.stopPropagation()
                setDrag({ index: i, edge: 'start' })
              }}
              className="absolute left-0 top-0 bottom-0"
              style={{ width: EDGE_HIT, marginLeft: -EDGE_HIT / 2, cursor: 'col-resize' }}
              title="Trim clip start"
            />
            <div
              onMouseDown={(e) => {
                e.stopPropagation()
                setDrag({ index: i, edge: 'end' })
              }}
              className="absolute right-0 top-0 bottom-0"
              style={{ width: EDGE_HIT, marginRight: -EDGE_HIT / 2, cursor: 'col-resize' }}
              title="Trim clip end"
            />
          </div>
        ))}

        <div
          className="absolute top-0 bottom-0 pointer-events-none"
          style={{ left: `${pctOf(playhead)}%`, width: 1, background: 'var(--color-cyan)' }}
        />
      </div>
    </div>
  )
}
