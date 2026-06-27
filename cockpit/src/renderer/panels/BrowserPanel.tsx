import { useState, useCallback } from 'react'
import { RefreshCw, Maximize2, Minimize2 } from 'lucide-react'

const NEKO_PWD = import.meta.env.VITE_NEKO_PASSWORD || 'neko'

function nekoUrl(): string {
  return `/neko/?embed=1&usr=operator&pwd=${encodeURIComponent(NEKO_PWD)}&volume=0`
}

export function BrowserPanel() {
  const [key, setKey] = useState(0)
  const [fullscreen, setFullscreen] = useState(false)

  const handleRefresh = useCallback(() => {
    setKey((k) => k + 1)
  }, [])

  return (
    <div className="flex flex-col h-full">
      <div
        className="flex items-center gap-2 px-2 py-1 shrink-0"
        style={{ borderBottom: '1px solid var(--color-border)' }}
      >
        <span className="text-[11px]" style={{ color: 'var(--color-text-tertiary)' }}>
          Browser
        </span>
        <div className="flex-1" />
        <button
          onClick={handleRefresh}
          className="p-1 rounded hover:opacity-80"
          style={{ color: 'var(--color-text-tertiary)' }}
          title="Reconnect"
        >
          <RefreshCw size={14} />
        </button>
        <button
          onClick={() => setFullscreen((f) => !f)}
          className="p-1 rounded hover:opacity-80"
          style={{ color: 'var(--color-text-tertiary)' }}
          title={fullscreen ? 'Exit fullscreen' : 'Fullscreen'}
        >
          {fullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
        </button>
      </div>
      <div className={`flex-1 relative ${fullscreen ? 'fixed inset-0 z-50 bg-black' : ''}`}>
        <iframe
          key={key}
          src={nekoUrl()}
          className="w-full h-full border-0"
          allow="autoplay; clipboard-read; clipboard-write"
        />
      </div>
    </div>
  )
}
