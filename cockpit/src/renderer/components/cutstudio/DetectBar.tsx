import { useState } from 'react'
import { Scan } from 'lucide-react'
import { useCutStudioStore } from '../../stores/cutStudioStore'

/**
 * Filler-word and silence sweeps. Detection is computed server-side from the
 * word timestamps; nothing is cut until the operator applies it.
 */
export function DetectBar() {
  const detections = useCutStudioStore((s) => s.detections)
  const transcript = useCutStudioStore((s) => s.transcript)
  const runDetect = useCutStudioStore((s) => s.runDetect)
  const applyDetections = useCutStudioStore((s) => s.applyDetections)

  const [threshold, setThreshold] = useState(1.0)
  const [fillers, setFillers] = useState(true)
  const [silences, setSilences] = useState(true)

  const fillerCount = detections?.filler_words.length ?? 0
  const silenceCount = detections?.silence_gaps.length ?? 0

  return (
    <div className="flex flex-col h-full p-3 gap-3">
      <div className="flex items-center gap-2">
        <label className="text-[10px] font-mono uppercase" style={{ color: 'var(--color-text-tertiary)' }}>
          Silence &gt;
        </label>
        <input
          type="range"
          min={0.3}
          max={3}
          step={0.1}
          value={threshold}
          onChange={(e) => setThreshold(Number(e.target.value))}
          onKeyDown={(e) => e.stopPropagation()}
          className="flex-1 min-w-0"
        />
        <span className="text-[10px] font-mono w-8 text-right" style={{ color: 'var(--color-text-secondary)' }}>
          {threshold.toFixed(1)}s
        </span>
        <button
          type="button"
          onClick={() => void runDetect(threshold)}
          disabled={!transcript}
          className="flex items-center gap-1.5 px-2 py-1 text-[10px] font-mono uppercase shrink-0"
          style={{ border: '1px solid var(--color-border)', color: transcript ? 'var(--color-violet)' : 'var(--color-text-tertiary)' }}
        >
          <Scan size={10} />
          Detect
        </button>
      </div>

      {detections ? (
        <>
          <label className="flex items-center gap-2 text-[11px] font-mono cursor-pointer" style={{ color: 'var(--color-text-primary)' }}>
            <input type="checkbox" checked={fillers} onChange={(e) => setFillers(e.target.checked)} />
            {fillerCount} filler word{fillerCount === 1 ? '' : 's'}
          </label>
          <label className="flex items-center gap-2 text-[11px] font-mono cursor-pointer" style={{ color: 'var(--color-text-primary)' }}>
            <input type="checkbox" checked={silences} onChange={(e) => setSilences(e.target.checked)} />
            {silenceCount} silence gap{silenceCount === 1 ? '' : 's'}
          </label>
          <button
            type="button"
            onClick={() => applyDetections(fillers, silences)}
            disabled={(!fillers || fillerCount === 0) && (!silences || silenceCount === 0)}
            className="py-1.5 text-[10px] font-mono uppercase"
            style={{ border: '1px solid var(--color-violet)', color: 'var(--color-violet)' }}
          >
            Apply selected
          </button>
        </>
      ) : (
        <p className="text-[11px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
          {transcript
            ? 'Run a sweep to find filler words and dead air.'
            : 'Transcribe first — sweeps read the word timestamps.'}
        </p>
      )}
    </div>
  )
}
