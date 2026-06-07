import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { RRIPMessage, RRIPSuggestedAction } from '../../types/rrip'

function safeUrl(url: string): string {
  return /^https?:\/\//i.test(url) ? url : ''
}

const markdownComponents = {
  a: ({ href, children, ...rest }: React.ComponentPropsWithoutRef<'a'>) => (
    <a href={href ?? ''} target="_blank" rel="noopener noreferrer nofollow" {...rest}>{children}</a>
  ),
  img: () => null,
}

interface CommandResultCardProps {
  message: RRIPMessage
  aiName: string
  onAction?: (a: RRIPSuggestedAction) => void
}

function bubbleWidth(text: string): string {
  const len = text.length
  if (len <= 20) return 'max-w-[45%]'
  if (len <= 60) return 'max-w-[65%]'
  if (len <= 140) return 'max-w-[80%]'
  return 'max-w-full'
}

export function CommandResultCard({ message, aiName, onAction }: CommandResultCardProps) {
  const w = bubbleWidth(message.content)
  return (
    <div className="flex justify-start">
      <div
        className={`px-2.5 py-1.5 rounded-2xl rounded-bl-sm text-[11px] bg-surface-raised text-text-secondary w-fit ${w}`}
        style={{ borderLeft: '2px solid var(--color-cyan)' }}
      >
        <div className="flex items-center gap-2 mb-0.5">
          <span className="font-mono text-[9px] text-text-tertiary">{aiName}</span>
          {message.intent && (
            <span
              className="text-[8px] font-mono px-1 rounded uppercase"
              style={{ color: 'var(--color-cyan)', background: 'rgba(0,200,255,0.08)' }}
            >
              {message.intent.replace(/_/g, ' ')}
            </span>
          )}
          <span className="text-[9px] text-text-tertiary ml-auto">
            {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>
        <div className="chat-markdown leading-relaxed" style={{ color: 'var(--color-violet)' }}>
          <ReactMarkdown remarkPlugins={[remarkGfm]} urlTransform={safeUrl} components={markdownComponents}>
            {message.content}
          </ReactMarkdown>
        </div>
        {message.suggested_actions && message.suggested_actions.length > 0 && onAction && (
          <div className="flex flex-wrap gap-1 mt-1.5 pt-1.5 border-t border-border/50">
            {message.suggested_actions.map((action, i) => (
              <button
                key={i}
                onClick={() => onAction(action)}
                className="text-[9px] font-mono px-1.5 py-0.5 rounded border border-cyan/30 text-cyan hover:bg-cyan-glow transition-colors"
              >
                {action.label}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
