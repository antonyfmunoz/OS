import React, { useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Download } from 'lucide-react'
import type { RRIPMessage } from '../../types/rrip'
import { getApiKey, API_BASE } from '../../api/client'

function safeUrl(url: string): string {
  return /^https?:\/\//i.test(url) ? url : ''
}

const markdownComponents = {
  a: ({ href, children, ...rest }: React.ComponentPropsWithoutRef<'a'>) => (
    <a href={href ?? ''} target="_blank" rel="noopener noreferrer nofollow" {...rest}>{children}</a>
  ),
  img: () => null,
}

export function ReportCard({ message }: { message: RRIPMessage }) {
  const handleDownload = useCallback(async (e: React.MouseEvent) => {
    e.preventDefault()
    if (!message.attachment) return
    const url = `${API_BASE}/chat/attachment?path=${encodeURIComponent(message.attachment.path)}`
    const headers: Record<string, string> = {}
    const key = getApiKey()
    if (key) headers['X-API-Key'] = key
    const res = await fetch(url, { headers })
    if (!res.ok) return
    const blob = await res.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = message.attachment.filename
    a.click()
    URL.revokeObjectURL(a.href)
  }, [message.attachment])

  const provParts: string[] = []
  if (message.provenance) {
    if (message.provenance.node) provParts.push(message.provenance.node)
    if (message.provenance.harness) provParts.push(message.provenance.harness)
    if (message.provenance.session) provParts.push(`session ${message.provenance.session}`)
    if (message.provenance.phase) provParts.push(`Phase ${message.provenance.phase}`)
    if (message.provenance.pr) provParts.push(`PR #${message.provenance.pr}`)
    if (message.provenance.task) provParts.push(message.provenance.task)
  }

  return (
    <div
      className="px-2 py-2 rounded text-[11px] bg-surface-raised text-text-secondary mr-4"
      style={{ borderLeft: '2px solid var(--color-ok)' }}
    >
      <div className="flex items-center gap-2 mb-1">
        <span
          className="text-[8px] font-mono px-1 rounded uppercase"
          style={{ color: 'var(--color-ok)', background: 'rgba(0,255,136,0.08)' }}
        >
          system report
        </span>
        <span className="text-[9px] text-text-tertiary ml-auto">
          {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>
      {message.title && (
        <div
          className="font-mono text-[10px] tracking-wide uppercase mb-1 pb-1"
          style={{ color: 'var(--color-cyan)', borderBottom: '1px solid var(--color-border)' }}
        >
          {message.title}
        </div>
      )}
      {provParts.length > 0 && (
        <div
          className="flex flex-wrap gap-x-1 gap-y-1 mt-1 mb-2 py-1 px-2 rounded text-[9px] font-mono"
          style={{
            background: 'var(--color-surface)',
            borderLeft: '2px solid var(--color-cyan)',
            color: 'var(--color-text-tertiary)',
          }}
        >
          {provParts.map((p, i) => (
            <span key={i}>
              {i > 0 && <span style={{ opacity: 0.4 }}> · </span>}
              {p}
            </span>
          ))}
        </div>
      )}
      <div className="chat-markdown leading-relaxed" style={{ color: 'var(--color-violet)' }}>
        <ReactMarkdown remarkPlugins={[remarkGfm]} urlTransform={safeUrl} components={markdownComponents}>
          {message.content}
        </ReactMarkdown>
      </div>
      {message.attachment && (
        <button
          type="button"
          onClick={handleDownload}
          className="flex items-center gap-2 mt-2 py-1 px-2 rounded text-[10px] font-mono transition-colors cursor-pointer w-full text-left"
          style={{
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            color: 'var(--color-cyan)',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--color-cyan)' }}
          onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--color-border)' }}
        >
          <Download size={10} />
          <span className="truncate flex-1">{message.attachment.filename}</span>
          <span style={{ color: 'var(--color-text-tertiary)' }}>DOWNLOAD</span>
        </button>
      )}
    </div>
  )
}
