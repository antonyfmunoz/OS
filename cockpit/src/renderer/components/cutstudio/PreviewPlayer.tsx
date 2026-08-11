import { useCallback, useEffect, useRef, useState } from 'react'
import { Pause, Play } from 'lucide-react'
import { useCutStudioStore } from '../../stores/cutStudioStore'
import {
  edlDuration,
  fmtTime,
  isKept,
  nextRangeAfter,
  outputToSource,
  rangeAt,
  sourceToOutput,
} from '../../utils/cutAlgorithms'

const EDGE = 0.03

/**
 * A2 — the cut plays without rendering. A requestAnimationFrame loop watches
 * the source playhead and jumps to the next kept range as it reaches the end of
 * the current one. rAF, not `timeupdate`: timeupdate fires ~4Hz, which lands the
 * jump up to 250ms late and shows a visible overshoot of the removed material.
 */
export function PreviewPlayer() {
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const rafRef = useRef<number | null>(null)
  const mediaUrl = useCutStudioStore((s) => s.mediaUrl)
  const edl = useCutStudioStore((s) => s.edl)
  const playhead = useCutStudioStore((s) => s.playhead)
  const setPlayhead = useCutStudioStore((s) => s.setPlayhead)
  const [playing, setPlaying] = useState(false)

  const outputTotal = edlDuration(edl)
  const outputNow = sourceToOutput(edl, playhead)

  // The store playhead is the seek authority: any external seek (transcript
  // click, timeline click, keyboard) moves the element to match. Guarded so the
  // rAF loop's own updates don't fight the element.
  useEffect(() => {
    const v = videoRef.current
    if (!v) return
    if (Math.abs(v.currentTime - playhead) > 0.25) v.currentTime = playhead
  }, [playhead])

  const tick = useCallback(() => {
    const v = videoRef.current
    if (!v) return
    const t = v.currentTime
    const currentRange = rangeAt(edl, t)

    if (!currentRange) {
      // Playhead sits in removed material — jump forward to the next kept clip.
      const next = nextRangeAfter(edl, t)
      if (next) {
        v.currentTime = next.start
      } else {
        v.pause()
      }
    } else if (t >= currentRange.end - EDGE) {
      const next = nextRangeAfter(edl, currentRange.end)
      if (next) {
        v.currentTime = next.start
      } else {
        v.pause()
      }
    }

    setPlayhead(v.currentTime)
    rafRef.current = requestAnimationFrame(tick)
  }, [edl, setPlayhead])

  useEffect(() => {
    if (!playing) {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current)
      rafRef.current = null
      return
    }
    rafRef.current = requestAnimationFrame(tick)
    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current)
      rafRef.current = null
    }
  }, [playing, tick])

  const toggle = useCallback(() => {
    const v = videoRef.current
    if (!v) return
    if (v.paused) {
      // Starting inside removed material would play material the cut drops.
      if (!isKept(edl, v.currentTime)) {
        const next = nextRangeAfter(edl, v.currentTime)
        if (next) v.currentTime = next.start
      }
      void v.play().catch(() => { /* autoplay/gesture guard */ })
    } else {
      v.pause()
    }
  }, [edl])

  const seekBar = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (!outputTotal) return
      const rect = e.currentTarget.getBoundingClientRect()
      const ratio = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width))
      setPlayhead(outputToSource(edl, ratio * outputTotal))
    },
    [edl, outputTotal, setPlayhead],
  )

  const pct = outputTotal > 0 ? (outputNow / outputTotal) * 100 : 0

  return (
    <div className="flex flex-col" style={{ borderBottom: '1px solid var(--color-border)' }}>
      <div className="flex items-center justify-center" style={{ background: 'var(--color-canvas)' }}>
        {mediaUrl ? (
          <video
            ref={videoRef}
            src={mediaUrl}
            preload="metadata"
            playsInline
            className="max-h-[38vh] w-auto"
            onPlay={() => setPlaying(true)}
            onPause={() => setPlaying(false)}
            onEnded={() => setPlaying(false)}
          />
        ) : (
          <div className="h-[38vh] flex items-center justify-center">
            <span className="text-[11px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
              Loading media...
            </span>
          </div>
        )}
      </div>

      <div className="flex items-center gap-2 px-3 py-2">
        <button
          type="button"
          onClick={toggle}
          className="shrink-0 cursor-pointer"
          style={{ color: 'var(--color-violet)' }}
          title={playing ? 'Pause (space)' : 'Play (space)'}
        >
          {playing ? <Pause size={13} /> : <Play size={13} />}
        </button>
        <div className="flex-1 min-w-0">
          <div
            onClick={seekBar}
            className="h-1 rounded-full cursor-pointer relative"
            style={{ background: 'var(--color-border)' }}
          >
            <div
              className="h-full rounded-full absolute left-0 top-0"
              style={{ width: `${pct}%`, background: 'var(--color-violet)' }}
            />
          </div>
        </div>
        <span className="shrink-0 text-[10px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
          {fmtTime(outputNow)} / {fmtTime(outputTotal)}
        </span>
      </div>
    </div>
  )
}
