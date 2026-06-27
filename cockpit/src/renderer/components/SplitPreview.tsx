import { useState, useCallback } from 'react'
import { Plus, X, ExternalLink, ChevronLeft, ChevronRight } from 'lucide-react'
import { LivePreview } from './LivePreview'
import { fetchApi } from '../api/client'

const ALL_PROJECTIONS = ['umh', 'creatoros', 'eos', 'lyfeos']

function nextProjection(current: string[]): string {
  return ALL_PROJECTIONS.find((p) => !current.includes(p)) || ALL_PROJECTIONS[0]
}

interface SplitPreviewProps {
  browserMode?: boolean
  expanded?: boolean
  onToggleExpand?: () => void
}

export function SplitPreview({ browserMode = false, expanded, onToggleExpand }: SplitPreviewProps) {
  const [panes, setPanes] = useState<string[]>(browserMode ? ['browser-0'] : ['umh'])

  const addPane = useCallback(() => {
    setPanes((prev) => {
      if (prev.length >= 4) return prev
      if (browserMode) return [...prev, `browser-${prev.length}`]
      return [...prev, nextProjection(prev)]
    })
  }, [browserMode])

  const removePane = useCallback((index: number) => {
    setPanes((prev) => {
      if (prev.length <= 1) return prev
      return prev.filter((_, i) => i !== index)
    })
  }, [])

  function handlePopOutAll() {
    fetchApi<{ projections: any[] }>('/projections')
      .then((data) => {
        const urls = (data.projections || [])
          .filter((p: any) => p.preview_url && panes.includes(p.projection_id))
          .map((p: any) => p.preview_url)
        urls.forEach((url: string) => window.open(url, '_blank'))
      })
      .catch(() => {})
  }

  const count = panes.length
  const gridClass =
    count === 1
      ? 'grid-cols-1'
      : count === 2
        ? 'grid-cols-2'
        : 'grid-cols-2 grid-rows-2'

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div
        className="flex items-center gap-2 px-2 py-1 shrink-0"
        style={{ borderBottom: '1px solid var(--color-border)' }}
      >
        {onToggleExpand && (
          <button
            onClick={onToggleExpand}
            className="p-1 rounded hover:opacity-80"
            style={{ color: 'var(--color-text-tertiary)' }}
            title={expanded ? 'Collapse preview' : 'Expand preview'}
          >
            {expanded ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
          </button>
        )}
        <span className="text-[11px]" style={{ color: 'var(--color-text-tertiary)' }}>
          {browserMode ? 'Browser' : 'Preview'}
        </span>
        {count > 1 && (
          <span
            className="text-[10px] px-1 rounded"
            style={{ color: 'var(--color-text-tertiary)', background: 'var(--color-surface-raised)' }}
          >
            {count}
          </span>
        )}
        <div className="flex-1" />
        <button
          onClick={addPane}
          disabled={count >= 4}
          className="p-1 rounded hover:opacity-80 disabled:opacity-30"
          style={{ color: 'var(--color-text-tertiary)' }}
          title="Add preview pane"
        >
          <Plus size={14} />
        </button>
        {!browserMode && (
          <button
            onClick={handlePopOutAll}
            className="p-1 rounded hover:opacity-80"
            style={{ color: 'var(--color-text-tertiary)' }}
            title="Open all in browser"
          >
            <ExternalLink size={14} />
          </button>
        )}
      </div>
      <div className={`flex-1 grid ${gridClass} min-h-0`}>
        {panes.map((projId, i) => (
          <div
            key={`${projId}-${i}`}
            className="overflow-hidden relative"
            style={{
              borderRight: count > 1 && i % 2 === 0 ? '1px solid var(--color-border)' : undefined,
              borderBottom: count > 2 && i < 2 ? '1px solid var(--color-border)' : undefined,
              gridColumn: count === 3 && i === 2 ? '1 / -1' : undefined,
            }}
          >
            {count > 1 && (
              <button
                onClick={() => removePane(i)}
                className="absolute top-1.5 right-1.5 z-20 p-0.5 rounded hover:opacity-80"
                style={{ color: 'var(--color-text-tertiary)', background: 'var(--color-surface-raised)' }}
                title="Close pane"
              >
                <X size={10} />
              </button>
            )}
            <LivePreview defaultProjection={browserMode ? undefined : projId} browserMode={browserMode} />
          </div>
        ))}
      </div>
    </div>
  )
}
