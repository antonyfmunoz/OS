import { useState, useRef, useEffect } from 'react'

interface LivePreviewProps {
  url?: string
  defaultUrl?: string
}

export function LivePreview({ url, defaultUrl = 'http://localhost:5173' }: LivePreviewProps) {
  const [currentUrl, setCurrentUrl] = useState(url || defaultUrl)
  const [inputUrl, setInputUrl] = useState(url || defaultUrl)
  const [loading, setLoading] = useState(true)
  const iframeRef = useRef<HTMLIFrameElement>(null)

  useEffect(() => {
    if (url) {
      setCurrentUrl(url)
      setInputUrl(url)
    }
  }, [url])

  function handleNavigate(e: React.FormEvent) {
    e.preventDefault()
    let normalized = inputUrl.trim()
    if (normalized && !normalized.startsWith('http')) {
      normalized = `http://${normalized}`
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

  return (
    <div className="flex flex-col h-full">
      <div
        className="flex items-center gap-2 px-2 py-1.5 flex-shrink-0"
        style={{ borderBottom: '1px solid var(--border)' }}
      >
        <button
          onClick={handleRefresh}
          className="text-xs px-1.5 py-0.5 rounded"
          style={{ color: 'var(--text-secondary)' }}
          title="Refresh"
        >
          ↻
        </button>
        <form onSubmit={handleNavigate} className="flex-1 flex">
          <input
            value={inputUrl}
            onChange={(e) => setInputUrl(e.target.value)}
            className="flex-1 px-2 py-0.5 rounded text-xs bg-transparent outline-none"
            style={{
              color: 'var(--text-primary)',
              border: '1px solid var(--border)',
            }}
          />
        </form>
      </div>

      <div className="flex-1 relative">
        {loading && (
          <div
            className="absolute inset-0 flex items-center justify-center z-10"
            style={{ background: 'var(--surface-2)' }}
          >
            <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
              Loading...
            </span>
          </div>
        )}
        <iframe
          ref={iframeRef}
          src={currentUrl}
          className="w-full h-full border-0"
          style={{ background: '#fff' }}
          onLoad={() => setLoading(false)}
          onError={() => setLoading(false)}
          sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
        />
      </div>
    </div>
  )
}
