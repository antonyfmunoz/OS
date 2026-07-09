import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { RRIPMessage } from '../../types/rrip'

function safeUrl(url: string): string {
  return /^https?:\/\//i.test(url) ? url : ''
}

const markdownComponents = {
  a: ({ href, children, ...rest }: React.ComponentPropsWithoutRef<'a'>) => (
    <a href={href ?? ''} target="_blank" rel="noopener noreferrer nofollow" {...rest}>{children}</a>
  ),
  img: () => null,
}

interface ConversationBubbleProps {
  message: RRIPMessage
  aiName: string
}

function bubbleWidth(text: string): string {
  const len = text.length
  if (len <= 20) return 'max-w-[45%]'
  if (len <= 60) return 'max-w-[65%]'
  if (len <= 140) return 'max-w-[80%]'
  return 'max-w-full'
}

export function ConversationBubble({ message, aiName }: ConversationBubbleProps) {
  if (message.role === 'operator') {
    const w = bubbleWidth(message.content)
    return (
      <div className="flex justify-end">
        <div className={`px-2.5 py-1.5 rounded-2xl rounded-br-sm text-[11px] bg-cyan-glow text-text-primary w-fit min-w-0 ${w}`}>
          <p className="whitespace-pre-wrap break-words [overflow-wrap:anywhere]">{message.content}</p>
        </div>
      </div>
    )
  }

  const w = bubbleWidth(message.content)
  return (
    <div className="flex justify-start">
      <div className={`px-2.5 py-1.5 rounded-2xl rounded-bl-sm text-[11px] bg-surface-raised text-text-secondary w-fit min-w-0 ${w}`}>
        <div className="flex items-center gap-2 mb-0.5">
          <span className="font-mono text-[9px] text-text-tertiary">{aiName}</span>
          {message.intent && message.intent !== 'dex_response' && message.intent !== 'chat' && (
            <span className="text-[8px] font-mono px-1 rounded uppercase text-text-tertiary bg-surface">
              {message.intent}
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
        {message.routing && (
          <div className="text-[8px] font-mono text-text-tertiary mt-1 opacity-50">
            {message.routing.cognitive_mode && message.routing.cognitive_mode}
            {message.routing.runtime && ` · ${message.routing.runtime}`}
          </div>
        )}
      </div>
    </div>
  )
}
