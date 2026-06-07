import React from 'react'
import type { RRIPMessage, RRIPSuggestedAction } from '../../types/rrip'
import { ConversationBubble } from './ConversationBubble'
import { ReportCard } from './ReportCard'
import { CommandResultCard } from './CommandResultCard'
import { ApprovalCard } from './ApprovalCard'
import { ErrorCard } from './ErrorCard'

interface RRIPRendererProps {
  message: RRIPMessage
  aiName: string
  onAction?: (a: RRIPSuggestedAction) => void
  onApprove: (approvalId: string) => void
  onDeny: (approvalId: string) => void
}

export function RRIPRenderer({ message, aiName, onAction, onApprove, onDeny }: RRIPRendererProps) {
  switch (message.kind) {
    case 'conversation':
      return <ConversationBubble message={message} aiName={aiName} onAction={onAction} />
    case 'work_report':
    case 'audit_report':
      return <ReportCard message={message} />
    case 'command_result':
    case 'status':
    case 'delegation':
      return <CommandResultCard message={message} aiName={aiName} onAction={onAction} />
    case 'approval_request':
      return <ApprovalCard message={message} onApprove={onApprove} onDeny={onDeny} />
    case 'error':
      return <ErrorCard message={message} onAction={onAction} />
    default:
      return <ConversationBubble message={message} aiName={aiName} onAction={onAction} />
  }
}
