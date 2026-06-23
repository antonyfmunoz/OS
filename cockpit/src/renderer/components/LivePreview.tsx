import { useState, useRef, useEffect, useCallback } from 'react'
import { RefreshCw, ExternalLink, Maximize2, Minimize2, ChevronDown } from 'lucide-react'
import { ViewportSelector, VIEWPORT_PRESETS, type ViewportPreset } from './ViewportSelector'
import { fetchApi } from '../api/client'

interface ProjectionInfo {
  projection_id: string
  name: string
  preview_url: string
  health_url: string
}

interface LivePreviewProps {
  url?: string
  defaultUrl?: string
  expanded?: boolean
  onToggleExpand?: () => void
}

export function LivePreview({
  url: propUrl,
  defaultUrl = '',
  expanded = false,
  onToggleExpand,
}: LivePreviewProps) {
  const [projections, setProjections] = useState<ProjectionInfo[]>([])
  const [selectedProjection, setSelectedProjection] = useState<string>('')
  const [currentUrl, setCurrentUrl] = useState(propUrl || defaultUrl)
  const [inputUrl, setInputUrl] = useState(propUrl || defaultUrl)
  const [loading, setLoading] = useState(false)
  const [healthStatus, setHealthStatus] = useState<'unknown' | 'healthy' | 'unhealthy'>('unknown')
  const [viewport, setViewport] = useState<ViewportPreset>('desktop')
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const iframeRef = useRef<HTMLIFrameElement>(null)

  useEffect(() => {
    fetchApi<{ projections: any[] }>('/projections')
      .then((data) => {
        const projs: ProjectionInfo[] = (data.projections || [])
          .filter((p: any) => p.preview_url)
          .map((p: any) => ({
            projection_id: p.projection_id,
            name: p.name,
            preview_url: p.preview_url,
            health_url: p.health_url || '',
          }))
        setProjections(projs)
        if (projs.length > 0 && !propUrl && !defaultUrl) {
          setSelectedProjection(projs[0].projection_id)
          setCurrentUrl(projs[0].preview_url)
          setInputUrl(projs[0].preview_url)
        }
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (propUrl) {
      setCurrentUrl(propUrl)
      setInputUrl(propUrl)
    }
  }, [propUrl])

  const checkHealth = useCallback(async () => {
    const proj = projections.find((p) => p.projection_id === selectedProjection)
    if (!proj?.health_url) {
      setHealthStatus('unknown')
      return
    }
    try {
      const resp = await fetch(proj.health_url, { mode: 'no-cors', cache: 'no-store' })
      setHealthStatus(resp.type === 'opaque' || resp.ok ? 'healthy' : 'unhealthy')
    } catch {
      setHealthStatus('unhealthy')
    }
  }, [projections, selectedProjection])

  useEffect(() => {
    checkHealth()
    const interval = setInterval(checkHealth, 30000)
    return () => clearInterval(interval)
  }, [checkHealth])

  function handleProjectionChange(projId: string) {
    setSelectedProjection(projId)
    setDropdownOpen(false)
    const proj = projections.find((p) => p.projection_id === projId)
    if (proj) {
      setCurrentUrl(proj.preview_url)
      setInputUrl(proj.preview_url)
      setLoading(true)
    }
  }

  function handleNavigate(e: React.FormEvent) {
    e.preventDefault()
    let normalized = inputUrl.trim()
    if (normalized && !normalized.startsWith('http')) {
      normalized = `https://${normalized}`
    }
    setCurrentUrl(normalized)
    setLoading(true)
  }

  function handleRefresh() {
    if (iframeRef.current) {
      setLoading(true)
      iframeRef.current.src = currentUrl
    }
  }

  function handleOpenExternal() {
    if (currentUrl) {
      window.open(currentUrl, '_blank')
    }
  }

  const healthDot =
    healthStatus === 'healthy'
      ? '#22c55e'
      : healthStatus === 'unhealthy'
        ? '#ef4444'
        : '#6b7280'

  const vp = VIEWPORT_PRESETS[viewport]

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div
        className="flex items-center gap-2 px-2 py-1.5 flex-shrink-0"
        style={{ borderBottom: '1px solid var(--color-border)' }}
      >
        {/* Project selector */}
        {projections.length > 0 && (
          <div className="relative">
            <button
              onClick={() => setDropdownOpen(!dropdownOpen)}
              className="flex items-center gap-1 px-2 py-1 rounded text-xs"
              style={{
                color: 'var(--color-text-secondary)',
                border: '1px solid var(--color-border)',
              }}
            >
              <span
                className="inline-block w-2 h-2 rounded-full flex-shrink-0"
                style={{ background: healthDot }}
              />
              {projections.find((p) => p.projection_id === selectedProjection)?.name || 'Select'}
              <ChevronDown size={12} />
            </button>
            {dropdownOpen && (
              <div
                className="absolute top-full left-0 mt-1 rounded shadow-lg z-50 min-w-[160px]"
                style={{
                  background: 'var(--color-surface-raised)',
                  border: '1px solid var(--color-border)',
                }}
              >
                {projections.map((p) => (
                  <button
                    key={p.projection_id}
                    onClick={() => handleProjectionChange(p.projection_id)}
                    className="block w-full text-left px-3 py-1.5 text-xs hover:opacity-80"
                    style={{
                      color:
                        p.projection_id === selectedProjection
                          ? 'var(--color-accent)'
                          : 'var(--color-text-secondary)',
                    }}
                  >
                    {p.name}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* URL bar */}
        <form onSubmit={handleNavigate} className="flex-1 flex">
          <input
            value={inputUrl}
            onChange={(e) => setInputUrl(e.target.value)}
            className="flex-1 px-2 py-1 rounded text-xs bg-transparent outline-none"
            style={{
              color: 'var(--color-text-primary)',
              border: '1px solid var(--color-border)',
            }}
            placeholder="URL..."
          />
        </form>

        {/* Viewport selector */}
        <ViewportSelector value={viewport} onChange={setViewport} />

        {/* Action buttons */}
        <button
          onClick={handleRefresh}
          className="p-1 rounded hover:opacity-80"
          style={{ color: 'var(--color-text-tertiary)' }}
          title="Refresh"
        >
          <RefreshCw size={14} />
        </button>
        <button
          onClick={handleOpenExternal}
          className="p-1 rounded hover:opacity-80"
          style={{ color: 'var(--color-text-tertiary)' }}
          title="Open in browser"
        >
          <ExternalLink size={14} />
        </button>
        {onToggleExpand && (
          <button
            onClick={onToggleExpand}
            className="p-1 rounded hover:opacity-80"
            style={{ color: 'var(--color-text-tertiary)' }}
            title={expanded ? 'Collapse' : 'Expand'}
          >
            {expanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
          </button>
        )}
      </div>

      {/* Preview area with viewport framing */}
      <div className="flex-1 relative overflow-auto flex items-start justify-center">
        {loading && (
          <div
            className="absolute inset-0 flex items-center justify-center z-10"
            style={{ background: 'var(--color-surface-raised)' }}
          >
            <span className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>
              Loading preview...
            </span>
          </div>
        )}
        {!currentUrl ? (
          <div className="flex items-center justify-center h-full w-full">
            <span className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>
              Select a projection or enter a URL
            </span>
          </div>
        ) : (
          <div
            className="relative mx-auto my-2"
            style={{
              width: viewport === 'desktop' ? '100%' : `${vp.width}px`,
              maxWidth: '100%',
              height: viewport === 'desktop' ? '100%' : `${vp.height}px`,
              border: viewport !== 'desktop' ? '1px solid var(--color-border)' : 'none',
              borderRadius: viewport !== 'desktop' ? '8px' : '0',
              overflow: 'hidden',
            }}
          >
            <iframe
              ref={iframeRef}
              src={currentUrl}
              className="w-full h-full border-0"
              style={{ background: '#fff' }}
              onLoad={() => setLoading(false)}
              onError={() => setLoading(false)}
              sandbox="allow-scripts allow-forms allow-popups allow-same-origin"
            />
          </div>
        )}
      </div>
    </div>
  )
}
