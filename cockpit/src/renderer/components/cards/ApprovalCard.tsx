import React from 'react'
import type { RRIPMessage } from '../../types/rrip'

const RISK_COLORS: Record<string, { text: string; bg: string }> = {
  LOW: { text: 'var(--color-ok)', bg: 'rgba(0,255,136,0.08)' },
  MEDIUM: { text: 'var(--color-warn)', bg: 'rgba(255,200,0,0.08)' },
  HIGH: { text: 'var(--color-danger)', bg: 'rgba(255,60,60,0.08)' },
  CRITICAL: { text: 'var(--color-danger)', bg: 'rgba(255,60,60,0.15)' },
}

interface ApprovalCardProps {
  message: RRIPMessage
  onApprove: (approvalId: string) => void
  onDeny: (approvalId: string) => void
}

export function ApprovalCard({ message, onApprove, onDeny }: ApprovalCardProps) {
  const data = message.approval_data
  if (!data) return null

  const riskStyle = RISK_COLORS[data.risk_level] || RISK_COLORS.MEDIUM

  return (
    <div
      className="px-2 py-2 rounded text-[11px] bg-surface-raised text-text-secondary mr-4"
      style={{ borderLeft: '2px solid var(--color-warn)' }}
    >
      <div className="flex items-center gap-2 mb-1">
        <span
          className="text-[8px] font-mono px-1 rounded uppercase"
          style={{ color: 'var(--color-warn)', background: 'rgba(255,200,0,0.08)' }}
        >
          approval required
        </span>
        <span
          className="text-[8px] font-mono px-1 rounded uppercase"
          style={{ color: riskStyle.text, background: riskStyle.bg }}
        >
          {data.risk_level}
        </span>
        <span className="text-[9px] text-text-tertiary ml-auto">
          {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>
      <p className="whitespace-pre-wrap mb-1">{data.description}</p>
      {data.agent && (
        <div className="text-[9px] text-text-tertiary font-mono mb-2">
          agent: {data.agent}
        </div>
      )}
      {data.status === 'pending' && (
        <div className="flex gap-2 mt-1.5 pt-1.5 border-t border-border/50">
          <button
            onClick={() => onApprove(data.approval_id)}
            className="text-[9px] font-mono px-2 py-0.5 rounded border transition-colors"
            style={{ borderColor: 'var(--color-ok)', color: 'var(--color-ok)' }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(0,255,136,0.1)' }}
            onMouseLeave={(e) => { e.currentTarget.style.background = '' }}
          >
            APPROVE
          </button>
          <button
            onClick={() => onDeny(data.approval_id)}
            className="text-[9px] font-mono px-2 py-0.5 rounded border transition-colors"
            style={{ borderColor: 'var(--color-danger)', color: 'var(--color-danger)' }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,60,60,0.1)' }}
            onMouseLeave={(e) => { e.currentTarget.style.background = '' }}
          >
            DENY
          </button>
        </div>
      )}
      {data.status !== 'pending' && (
        <div className="text-[9px] font-mono text-text-tertiary mt-1">
          {data.status === 'approved' ? 'Approved' : 'Denied'}
        </div>
      )}
    </div>
  )
}
