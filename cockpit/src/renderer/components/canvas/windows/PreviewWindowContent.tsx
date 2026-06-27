import { useState, useCallback } from 'react'

interface Props {
  url?: string
  paused: boolean
}

export function PreviewWindowContent({ url: initialUrl, paused }: Props) {
  const [url, setUrl] = useState(initialUrl ?? '')
  const [activeUrl, setActiveUrl] = useState(initialUrl ?? '')

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault()
    if (url.trim()) setActiveUrl(url.trim())
  }, [url])

  return (
    <div className="flex flex-col h-full">
      <form onSubmit={handleSubmit} className="flex gap-1 p-1 shrink-0" style={{ borderBottom: '1px solid var(--color-border)' }}>
        <input
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="URL..."
          className="flex-1 px-2 py-0.5 text-[11px] rounded"
          style={{ background: 'var(--color-canvas)', color: 'var(--color-text-primary)', border: '1px solid var(--color-border)', outline: 'none' }}
        />
      </form>
      <div className="flex-1">
        {activeUrl && !paused ? (
          <iframe
            src={activeUrl}
            className="w-full h-full border-none"
            sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
            title="Preview"
          />
        ) : (
          <div className="flex items-center justify-center h-full" style={{ color: 'var(--color-text-tertiary)' }}>
            <span className="text-[12px]">{paused ? 'Paused' : 'Enter a URL to preview'}</span>
          </div>
        )}
      </div>
    </div>
  )
}
