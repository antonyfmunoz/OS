import { useState } from 'react'
import { Sparkles } from 'lucide-react'
import { useCutStudioStore } from '../../stores/cutStudioStore'
import { fmtTime } from '../../utils/cutAlgorithms'
import type { HighlightCandidate } from '../../utils/cutAlgorithms'

function ScoreBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-[9px] font-mono uppercase w-10 shrink-0" style={{ color: 'var(--color-text-tertiary)' }}>
        {label}
      </span>
      <div className="flex-1 h-1" style={{ background: 'var(--color-border)' }}>
        <div className="h-full" style={{ width: `${Math.max(0, Math.min(99, value))}%`, background: 'var(--color-violet)' }} />
      </div>
      <span className="text-[9px] font-mono w-5 text-right shrink-0" style={{ color: 'var(--color-text-secondary)' }}>
        {value}
      </span>
    </div>
  )
}

/**
 * AI clip selection — one recording becomes several assets. Each candidate
 * renders on its own, independent of the main EDL cut.
 */
export function HighlightsPanel() {
  const highlights = useCutStudioStore((s) => s.highlights)
  const jobs = useCutStudioStore((s) => s.jobs)
  const runHighlights = useCutStudioStore((s) => s.runHighlights)
  const renderCut = useCutStudioStore((s) => s.renderCut)

  const [count, setCount] = useState(4)
  const [target, setTarget] = useState(45)

  const running = jobs.some((j) => j.kind === 'highlights' && (j.state === 'queued' || j.state === 'running'))

  const renderClip = (c: HighlightCandidate) => {
    void renderCut({
      aspect: '9:16',
      captions: true,
      caption_style: 2,
      clean_audio: false,
      clip: { start: c.start, end: c.end },
    })
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 p-2 shrink-0" style={{ borderBottom: '1px solid var(--color-border)' }}>
        <label className="text-[10px] font-mono uppercase" style={{ color: 'var(--color-text-tertiary)' }}>
          Count
        </label>
        <input
          type="number"
          min={1}
          max={12}
          value={count}
          onChange={(e) => setCount(Number(e.target.value))}
          onKeyDown={(e) => e.stopPropagation()}
          className="w-12 px-1 py-0.5 text-[10px] font-mono outline-none"
          style={{ background: 'var(--color-surface-raised)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }}
        />
        <label className="text-[10px] font-mono uppercase" style={{ color: 'var(--color-text-tertiary)' }}>
          Target s
        </label>
        <input
          type="number"
          min={10}
          max={180}
          value={target}
          onChange={(e) => setTarget(Number(e.target.value))}
          onKeyDown={(e) => e.stopPropagation()}
          className="w-14 px-1 py-0.5 text-[10px] font-mono outline-none"
          style={{ background: 'var(--color-surface-raised)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }}
        />
        <div className="flex-1" />
        <button
          type="button"
          onClick={() => void runHighlights(count, target)}
          disabled={running}
          className="flex items-center gap-1.5 px-2 py-1 text-[10px] font-mono uppercase"
          style={{ border: '1px solid var(--color-border)', color: running ? 'var(--color-text-tertiary)' : 'var(--color-violet)' }}
        >
          <Sparkles size={10} />
          {running ? 'Finding' : 'Find clips'}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {highlights.length === 0 && !running && (
          <p className="text-[11px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
            No candidates yet — find clips to rank the strongest moments.
          </p>
        )}
        {highlights.map((c, i) => (
          <div
            key={`${i}-${c.start}`}
            className="p-2"
            style={{ background: 'var(--color-surface-raised)', border: '1px solid var(--color-border)' }}
          >
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono" style={{ color: 'var(--color-violet)' }}>
                #{i + 1}
              </span>
              <span className="text-[10px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
                {fmtTime(c.start)}–{fmtTime(c.end)} · {Math.round(c.end - c.start)}s
              </span>
              <div className="flex-1" />
              <span className="text-[11px] font-mono" style={{ color: 'var(--color-text-primary)' }}>
                {c.score.overall}
              </span>
            </div>
            <p className="text-[11px] font-mono mt-1" style={{ color: 'var(--color-text-primary)' }}>
              {c.hook_line}
            </p>
            <p className="text-[10px] font-mono mt-0.5" style={{ color: 'var(--color-text-secondary)' }}>
              {c.reason}
            </p>
            <div className="mt-2 space-y-1">
              <ScoreBar label="Hook" value={c.score.hook} />
              <ScoreBar label="Flow" value={c.score.flow} />
              <ScoreBar label="Value" value={c.score.value} />
            </div>
            <button
              type="button"
              onClick={() => renderClip(c)}
              className="mt-2 w-full py-1 text-[10px] font-mono uppercase"
              style={{ border: '1px solid var(--color-violet)', color: 'var(--color-violet)' }}
            >
              Render this clip
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
