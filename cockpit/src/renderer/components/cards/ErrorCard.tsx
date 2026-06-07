import React from 'react'
import type { RRIPMessage, RRIPSuggestedAction } from '../../types/rrip'

interface ErrorCardProps {
  message: RRIPMessage
  onAction?: (a: RRIPSuggestedAction) => void
}

export function ErrorCard({ message, onAction }: ErrorCardProps) {
  return (
    <div
      className="px-2 py-2 rounded text-[11px] text-text-secondary mr-4"
      style={{
        borderLeft: '2px solid var(--color-danger)',
        background: 'rgba(255,60,60,0.05)',
      }}
    >
      <div className="flex items-center gap-2 mb-1">
        <span
          className="text-[8px] font-mono px-1 rounded uppercase"
          style={{ color: 'var(--color-danger)', background: 'rgba(255,60,60,0.1)' }}
        >
          error
        </span>
        <span className="text-[9px] text-text-tertiary ml-auto">
          {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>
      <p className="whitespace-pre-wrap font-mono text-[10px]" style={{ color: 'var(--color-danger)' }}>
        {message.content}
      </p>
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
  )
}
