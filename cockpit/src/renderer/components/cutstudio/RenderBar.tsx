import { useCallback, useState } from 'react'
import { Download, Film } from 'lucide-react'
import { CUT_API, useCutStudioStore } from '../../stores/cutStudioStore'
import type { RenderOptions } from '../../stores/cutStudioStore'
import { authHeader } from '../../api/client'

type Aspect = RenderOptions['aspect']

const ASPECTS: Aspect[] = ['source', '9:16', '1:1', '16:9']
const CAPTION_STYLES: Array<{ value: 1 | 2 | 3; label: string }> = [
  { value: 1, label: 'Clean lower-third' },
  { value: 2, label: 'Bold center' },
  { value: 3, label: 'Minimal' },
]

/** Render controls, job state, and the finished-artifact download links. */
export function RenderBar() {
  const project = useCutStudioStore((s) => s.project)
  const projects = useCutStudioStore((s) => s.projects)
  const dirty = useCutStudioStore((s) => s.dirty)
  const saving = useCutStudioStore((s) => s.saving)
  const jobs = useCutStudioStore((s) => s.jobs)
  const renderCut = useCutStudioStore((s) => s.renderCut)
  const mediaTokenUrl = useCutStudioStore((s) => s.mediaTokenUrl)

  const [aspect, setAspect] = useState<Aspect>('9:16')
  const [captions, setCaptions] = useState(true)
  const [captionStyle, setCaptionStyle] = useState<1 | 2 | 3>(1)
  const [cleanAudio, setCleanAudio] = useState(false)

  const renderJobs = jobs.filter((j) => j.kind === 'render')
  const active = renderJobs.filter((j) => j.state === 'queued' || j.state === 'running')

  // The single-project fetch carries no `renders` key — only the list response
  // does, and the store refreshes it whenever a render finishes.
  const renders = projects.find((p) => p.id === project?.id)?.renders ?? []

  const download = useCallback(
    async (name: string) => {
      const url = await mediaTokenUrl(name)
      if (url) window.open(url, '_blank', 'noopener')
    },
    [mediaTokenUrl],
  )

  /**
   * The CMX3600 export is a bearer-authed text endpoint, so it can't be a plain
   * <a href> — fetch it with the Clerk header and hand the browser a blob.
   */
  const downloadEdl = useCallback(async () => {
    if (!project) return
    try {
      const res = await fetch(`${CUT_API}/export/${project.id}.edl`, { headers: await authHeader() })
      if (!res.ok) return
      const text = await res.text()
      const blob = new Blob([text], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${project.name || project.id}.edl`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      /* download is best-effort — the panel error banner covers API failures */
    }
  }, [project])

  return (
    <div className="p-3 shrink-0" style={{ borderTop: '1px solid var(--color-border)' }}>
      <div className="flex flex-wrap items-center gap-2">
        <select
          value={aspect}
          onChange={(e) => setAspect(e.target.value as Aspect)}
          onKeyDown={(e) => e.stopPropagation()}
          className="px-1.5 py-1 text-[10px] font-mono outline-none"
          style={{ background: 'var(--color-surface-raised)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }}
        >
          {ASPECTS.map((a) => (
            <option key={a} value={a}>{a}</option>
          ))}
        </select>

        <label className="flex items-center gap-1.5 text-[10px] font-mono cursor-pointer" style={{ color: 'var(--color-text-secondary)' }}>
          <input type="checkbox" checked={captions} onChange={(e) => setCaptions(e.target.checked)} />
          Captions
        </label>

        <select
          value={captionStyle}
          onChange={(e) => setCaptionStyle(Number(e.target.value) as 1 | 2 | 3)}
          onKeyDown={(e) => e.stopPropagation()}
          disabled={!captions}
          className="px-1.5 py-1 text-[10px] font-mono outline-none"
          style={{ background: 'var(--color-surface-raised)', border: '1px solid var(--color-border)', color: captions ? 'var(--color-text-primary)' : 'var(--color-text-tertiary)' }}
        >
          {CAPTION_STYLES.map((s) => (
            <option key={s.value} value={s.value}>{s.label}</option>
          ))}
        </select>

        <label className="flex items-center gap-1.5 text-[10px] font-mono cursor-pointer" style={{ color: 'var(--color-text-secondary)' }}>
          <input type="checkbox" checked={cleanAudio} onChange={(e) => setCleanAudio(e.target.checked)} />
          Clean audio
        </label>

        <div className="flex-1" />

        <button
          type="button"
          onClick={() => void downloadEdl()}
          className="flex items-center gap-1.5 px-2 py-1 text-[10px] font-mono uppercase"
          style={{ border: '1px solid var(--color-border)', color: 'var(--color-text-secondary)' }}
          title="Export CMX3600 EDL for Premiere/Resolve"
        >
          <Download size={10} />
          .edl
        </button>

        <button
          type="button"
          onClick={() => void renderCut({ aspect, captions, caption_style: captionStyle, clean_audio: cleanAudio })}
          disabled={saving}
          className="flex items-center gap-1.5 px-3 py-1 text-[10px] font-mono uppercase"
          style={{ border: '1px solid var(--color-violet)', color: 'var(--color-violet)' }}
        >
          <Film size={10} />
          {dirty ? 'Save & render' : 'Render'}
        </button>
      </div>

      {active.length > 0 && (
        <div className="mt-2 space-y-1">
          {active.map((j) => (
            <div key={j.id} className="flex items-center gap-2 text-[10px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
              <span>{j.state}</span>
              <div className="flex-1 h-0.5" style={{ background: 'var(--color-border)' }}>
                <div className="h-full" style={{ width: `${Math.round(j.progress * 100)}%`, background: 'var(--color-violet)' }} />
              </div>
              <span>{j.detail || `${Math.round(j.progress * 100)}%`}</span>
            </div>
          ))}
        </div>
      )}

      {renderJobs.some((j) => j.state === 'error') && (
        <div className="mt-2 text-[10px] font-mono" style={{ color: 'var(--color-danger)' }}>
          {renderJobs.filter((j) => j.state === 'error').map((j) => j.detail).join(' · ')}
        </div>
      )}

      {renders.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-2">
          {renders.map((name) => (
            <button
              key={name}
              type="button"
              onClick={() => void download(name)}
              className="flex items-center gap-1.5 px-2 py-1 text-[10px] font-mono"
              style={{ border: '1px solid var(--color-border)', color: 'var(--color-cyan)' }}
            >
              <Download size={10} />
              {name}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
