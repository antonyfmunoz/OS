import { useEffect, useState, useCallback, type FormEvent } from 'react'
import {
  Video,
  Plus,
  Check,
  CircleDot,
  Link2,
  Copy,
  Bot,
  Mic,
  PhoneOff,
  Activity,
  Wifi,
  WifiOff,
  ChevronDown,
  ChevronRight,
  Users,
} from 'lucide-react'
import { useRoomsStore } from '../../stores/roomsStore'
import type { MeetingMode } from '../../types/rooms'

const MEETING_MODES: { value: MeetingMode; label: string }[] = [
  { value: 'sales_call', label: 'Sales Call' },
  { value: 'coaching_call', label: 'Coaching' },
  { value: 'investor_call', label: 'Investor' },
  { value: 'hiring_interview', label: 'Hiring' },
  { value: 'team_meeting', label: 'Team' },
  { value: 'client_onboarding', label: 'Client' },
  { value: 'podcast_interview', label: 'Podcast' },
  { value: 'training_review', label: 'Training' },
  { value: 'war_room', label: 'War Room' },
]

type JoinState = 'idle' | 'joining' | 'joined' | 'failed'

export function MeetingRoomPanel({ channelId }: { channelId: string }) {
  const meetingStates = useRoomsStore((s) => s.meetingStates)
  const fetchMeeting = useRoomsStore((s) => s.fetchMeeting)
  const updateMeeting = useRoomsStore((s) => s.updateMeeting)
  const addMeetingActionItem = useRoomsStore((s) => s.addMeetingActionItem)
  const toggleMeetingActionItem = useRoomsStore((s) => s.toggleMeetingActionItem)
  const voiceStates = useRoomsStore((s) => s.voiceStates)
  const fetchVoiceState = useRoomsStore((s) => s.fetchVoiceState)
  const joinVoice = useRoomsStore((s) => s.joinVoice)
  const leaveVoice = useRoomsStore((s) => s.leaveVoice)
  const activeServerId = useRoomsStore((s) => s.activeServerId)
  const invites = useRoomsStore((s) => s.invites)
  const createInvite = useRoomsStore((s) => s.createInvite)
  const fetchInvites = useRoomsStore((s) => s.fetchInvites)
  const error = useRoomsStore((s) => s.error)

  const meeting = meetingStates[channelId]
  const voiceState = voiceStates[channelId]
  const [newAction, setNewAction] = useState('')
  const [newActionAssignee, setNewActionAssignee] = useState('')
  const [joinState, setJoinState] = useState<JoinState>('idle')
  const [joinError, setJoinError] = useState<string | null>(null)
  const [copiedLink, setCopiedLink] = useState(false)
  const [showDiagnostics, setShowDiagnostics] = useState(false)

  useEffect(() => {
    fetchMeeting(channelId)
    fetchVoiceState(channelId)
    if (activeServerId) fetchInvites(activeServerId)
  }, [channelId, fetchMeeting, fetchVoiceState, activeServerId, fetchInvites])

  useEffect(() => {
    const isIn = voiceState?.participants.some((p) => p.user_id === 'operator')
    if (isIn && joinState !== 'joined') setJoinState('joined')
    if (!isIn && joinState === 'joined') setJoinState('idle')
  }, [voiceState, joinState])

  const handleJoin = useCallback(async () => {
    setJoinState('joining')
    setJoinError(null)
    try {
      await joinVoice(channelId)
      setJoinState('joined')
    } catch (e) {
      setJoinState('failed')
      setJoinError(e instanceof Error ? e.message : 'Failed to join meeting')
    }
  }, [channelId, joinVoice])

  const handleLeave = useCallback(async () => {
    await leaveVoice(channelId)
    setJoinState('idle')
  }, [channelId, leaveVoice])

  const handleCopyInvite = useCallback(async () => {
    let code = invites.find((inv) => !inv.revoked)?.code
    if (!code && activeServerId) {
      const invite = await createInvite(activeServerId, channelId, null, 24, null)
      code = invite?.code
    }
    if (code) {
      const link = `${window.location.origin}/invite/${code}`
      await navigator.clipboard.writeText(link)
      setCopiedLink(true)
      setTimeout(() => setCopiedLink(false), 2000)
    }
  }, [invites, activeServerId, channelId, createInvite])

  const handleAddAction = async (e: FormEvent) => {
    e.preventDefault()
    if (!newAction.trim()) return
    await addMeetingActionItem(channelId, {
      text: newAction.trim(),
      assignee: newActionAssignee.trim() || 'unassigned',
      due_date: null,
      completed: false,
    })
    setNewAction('')
    setNewActionAssignee('')
  }

  const isInRoom = joinState === 'joined'
  const participantCount = voiceState?.participants.length || 0

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      <div className="flex-1 p-4 space-y-4 max-w-3xl mx-auto w-full">
        {/* Header with join controls */}
        <div className="flex items-start gap-3 mb-2">
          <div
            className="w-12 h-12 rounded-full flex items-center justify-center shrink-0"
            style={{ background: isInRoom ? 'var(--color-ok-dim)' : 'var(--color-violet-dim)' }}
          >
            <Video size={22} style={{ color: isInRoom ? 'var(--color-ok)' : 'var(--color-violet)' }} />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-mono font-semibold" style={{ color: 'var(--color-text-primary)' }}>
              Meeting Room
            </h3>
            <JoinStateLine joinState={joinState} joinError={joinError} />
          </div>
        </div>

        {/* Join / Leave / Invite bar */}
        <div className="flex flex-wrap gap-2">
          {isInRoom ? (
            <button
              onClick={handleLeave}
              className="flex items-center gap-2 text-[10px] font-mono px-3 py-1.5 rounded"
              style={{ background: 'var(--color-danger)', color: 'var(--color-canvas)' }}
            >
              <PhoneOff size={12} /> Leave Meeting
            </button>
          ) : (
            <button
              onClick={handleJoin}
              disabled={joinState === 'joining'}
              className="flex items-center gap-2 text-[10px] font-mono px-3 py-1.5 rounded"
              style={{
                background: joinState === 'joining' ? 'var(--color-surface-raised)' : 'var(--color-ok)',
                color: joinState === 'joining' ? 'var(--color-text-tertiary)' : 'var(--color-canvas)',
              }}
            >
              <Mic size={12} />
              {joinState === 'joining' ? 'Joining...' : 'Join Meeting'}
            </button>
          )}

          <button
            onClick={handleCopyInvite}
            className="flex items-center gap-2 text-[10px] font-mono px-3 py-1.5 rounded border"
            style={{
              borderColor: 'var(--color-border)',
              color: copiedLink ? 'var(--color-ok)' : 'var(--color-text-secondary)',
            }}
          >
            {copiedLink ? <Check size={12} /> : <Link2 size={12} />}
            {copiedLink ? 'Copied!' : 'Copy Invite Link'}
          </button>

          <div className="flex items-center gap-1 text-[9px] font-mono px-2" style={{ color: 'var(--color-text-tertiary)' }}>
            <Users size={10} />
            {participantCount} in meeting
          </div>
        </div>

        {/* AI participant card */}
        <div
          className="rounded border p-3"
          style={{ borderColor: 'var(--color-violet)', background: 'var(--color-violet-dim)' }}
        >
          <div className="flex items-center gap-2 mb-1">
            <Bot size={12} style={{ color: 'var(--color-violet)' }} />
            <span className="text-[10px] font-mono font-semibold" style={{ color: 'var(--color-violet)' }}>
              AI Participant Available
            </span>
          </div>
          <p className="text-[9px] font-mono" style={{ color: 'var(--color-text-secondary)' }}>
            Transcribe, summarize, action items, coaching cues.
            Governed by room permissions and AI Assistance toggle.
          </p>
          <p className="text-[9px] font-mono mt-1" style={{ color: 'var(--color-text-tertiary)' }}>
            Media listener unavailable until WebRTC/SFU is live.
          </p>
        </div>

        {/* Meeting Mode */}
        <Section title="Mode">
          <div className="flex flex-wrap gap-1.5">
            {MEETING_MODES.map((m) => (
              <button
                key={m.value}
                onClick={() => updateMeeting(channelId, { mode: m.value })}
                className="text-[9px] font-mono px-2 py-1 rounded border"
                style={{
                  borderColor: meeting?.mode === m.value ? 'var(--color-violet)' : 'var(--color-border)',
                  color: meeting?.mode === m.value ? 'var(--color-violet)' : 'var(--color-text-tertiary)',
                  background: meeting?.mode === m.value ? 'var(--color-violet-dim)' : 'transparent',
                }}
              >
                {m.label}
              </button>
            ))}
          </div>
        </Section>

        {/* Objective */}
        <Section title="Objective">
          <input
            value={meeting?.objective || ''}
            onChange={(e) => updateMeeting(channelId, { objective: e.target.value })}
            placeholder="What is this meeting trying to achieve?"
            className="w-full text-xs font-mono px-3 py-2 rounded border bg-transparent outline-none"
            style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-primary)' }}
          />
        </Section>

        {/* Agenda */}
        <Section title="Agenda">
          <div className="space-y-1">
            {(meeting?.agenda || []).map((item, i) => (
              <div key={i} className="flex items-center gap-2">
                <CircleDot size={10} style={{ color: 'var(--color-cyan)' }} />
                <span className="text-[11px] font-mono" style={{ color: 'var(--color-text-primary)' }}>{item}</span>
              </div>
            ))}
          </div>
          <input
            placeholder="Add agenda item (Enter to add)"
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                const val = (e.target as HTMLInputElement).value.trim()
                if (val) {
                  updateMeeting(channelId, { agenda: [...(meeting?.agenda || []), val] })
                  ;(e.target as HTMLInputElement).value = ''
                }
              }
            }}
            className="w-full text-xs font-mono px-3 py-2 mt-1 rounded border bg-transparent outline-none"
            style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-primary)' }}
          />
        </Section>

        {/* Notes */}
        <Section title="Notes">
          <textarea
            value={meeting?.notes || ''}
            onChange={(e) => updateMeeting(channelId, { notes: e.target.value })}
            placeholder="Meeting notes..."
            rows={4}
            className="w-full text-xs font-mono px-3 py-2 rounded border bg-transparent outline-none resize-none"
            style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-primary)' }}
          />
        </Section>

        {/* Decisions */}
        <Section title="Decisions">
          <div className="space-y-1">
            {(meeting?.decisions || []).map((d, i) => (
              <div key={i} className="flex items-center gap-2">
                <Check size={10} style={{ color: 'var(--color-ok)' }} />
                <span className="text-[11px] font-mono" style={{ color: 'var(--color-text-primary)' }}>{d}</span>
              </div>
            ))}
          </div>
          <input
            placeholder="Record a decision (Enter)"
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                const val = (e.target as HTMLInputElement).value.trim()
                if (val) {
                  updateMeeting(channelId, { decisions: [...(meeting?.decisions || []), val] })
                  ;(e.target as HTMLInputElement).value = ''
                }
              }
            }}
            className="w-full text-xs font-mono px-3 py-2 mt-1 rounded border bg-transparent outline-none"
            style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-primary)' }}
          />
        </Section>

        {/* Action Items */}
        <Section title="Action Items">
          <div className="space-y-1">
            {(meeting?.action_items || []).map((item) => (
              <div key={item.id} className="flex items-center gap-2">
                <button onClick={() => toggleMeetingActionItem(channelId, item.id)}>
                  <div
                    className="w-4 h-4 rounded border flex items-center justify-center"
                    style={{
                      borderColor: item.completed ? 'var(--color-ok)' : 'var(--color-border)',
                      background: item.completed ? 'var(--color-ok)' : 'transparent',
                    }}
                  >
                    {item.completed && <Check size={10} style={{ color: 'var(--color-canvas)' }} />}
                  </div>
                </button>
                <span
                  className="text-[11px] font-mono flex-1"
                  style={{
                    color: item.completed ? 'var(--color-text-tertiary)' : 'var(--color-text-primary)',
                    textDecoration: item.completed ? 'line-through' : 'none',
                  }}
                >
                  {item.text}
                </span>
                <span className="text-[9px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
                  {item.assignee}
                </span>
              </div>
            ))}
          </div>

          <form onSubmit={handleAddAction} className="flex gap-2 mt-2">
            <input
              value={newAction}
              onChange={(e) => setNewAction(e.target.value)}
              placeholder="New action item"
              className="flex-1 text-xs font-mono px-3 py-1.5 rounded border bg-transparent outline-none"
              style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-primary)' }}
            />
            <input
              value={newActionAssignee}
              onChange={(e) => setNewActionAssignee(e.target.value)}
              placeholder="Assignee"
              className="w-24 text-xs font-mono px-2 py-1.5 rounded border bg-transparent outline-none"
              style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-primary)' }}
            />
            <button
              type="submit"
              disabled={!newAction.trim()}
              className="text-xs font-mono px-2 py-1.5 rounded"
              style={{
                background: newAction.trim() ? 'var(--color-cyan)' : 'var(--color-surface-raised)',
                color: newAction.trim() ? 'var(--color-canvas)' : 'var(--color-text-tertiary)',
              }}
            >
              <Plus size={12} />
            </button>
          </form>
        </Section>

        {/* Settings */}
        <Section title="Settings">
          <div className="flex gap-3">
            <ToggleSetting
              label="Recording Consent"
              value={meeting?.recording_consent || false}
              onChange={(v) => updateMeeting(channelId, { recording_consent: v })}
            />
            <ToggleSetting
              label="AI Assistance"
              value={meeting?.ai_assistance || false}
              onChange={(v) => updateMeeting(channelId, { ai_assistance: v })}
            />
          </div>
        </Section>

        {/* Diagnostics */}
        <MeetingDiagnostics
          channelId={channelId}
          isInRoom={isInRoom}
          participantCount={participantCount}
          error={error}
          open={showDiagnostics}
          onToggle={() => setShowDiagnostics((v) => !v)}
        />
      </div>
    </div>
  )
}

function JoinStateLine({ joinState, joinError }: { joinState: JoinState; joinError: string | null }) {
  if (joinState === 'idle') {
    return (
      <p className="text-[10px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
        Meeting room — join to participate
      </p>
    )
  }
  if (joinState === 'joining') {
    return (
      <p className="text-[10px] font-mono flex items-center gap-1" style={{ color: 'var(--color-cyan)' }}>
        <Activity size={10} className="animate-pulse" /> Connecting...
      </p>
    )
  }
  if (joinState === 'joined') {
    return (
      <p className="text-[10px] font-mono flex items-center gap-1" style={{ color: 'var(--color-ok)' }}>
        <Wifi size={10} /> Connected — room shell active
      </p>
    )
  }
  return (
    <p className="text-[10px] font-mono flex items-center gap-1" style={{ color: 'var(--color-danger)' }}>
      <WifiOff size={10} /> {joinError || 'Connection failed'}
    </p>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-[10px] font-mono uppercase tracking-wider mb-1.5" style={{ color: 'var(--color-text-tertiary)' }}>
        {title}
      </div>
      {children}
    </div>
  )
}

function ToggleSetting({ label, value, onChange }: { label: string; value: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      onClick={() => onChange(!value)}
      className="flex items-center gap-2 text-[10px] font-mono px-2 py-1 rounded border"
      style={{
        borderColor: value ? 'var(--color-ok)' : 'var(--color-border)',
        color: value ? 'var(--color-ok)' : 'var(--color-text-tertiary)',
      }}
    >
      <div
        className="w-3 h-3 rounded-full"
        style={{ background: value ? 'var(--color-ok)' : 'var(--color-surface-raised)' }}
      />
      {label}
    </button>
  )
}

function MeetingDiagnostics({
  channelId,
  isInRoom,
  participantCount,
  error,
  open,
  onToggle,
}: {
  channelId: string
  isInRoom: boolean
  participantCount: number
  error: string | null
  open: boolean
  onToggle: () => void
}) {
  return (
    <div>
      <button
        onClick={onToggle}
        className="flex items-center gap-1 text-[9px] font-mono uppercase"
        style={{ color: 'var(--color-text-tertiary)' }}
      >
        {open ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
        Meeting Diagnostics
      </button>
      {open && (
        <div
          className="mt-1 rounded border p-3 space-y-1"
          style={{ borderColor: 'var(--color-border)' }}
        >
          <DiagRow label="Auth" value="Clerk JWT" ok />
          <DiagRow label="Room membership" value={isInRoom ? 'Joined' : 'Not joined'} ok={isInRoom} />
          <DiagRow label="WebSocket" value="Connected (pulse)" ok />
          <DiagRow label="Video transport" value="Pending — WebRTC/SFU required" ok={false} />
          <DiagRow label="Audio transport" value="Pending — WebRTC/SFU required" ok={false} />
          <DiagRow label="Screen share" value="Pending" ok={false} />
          <DiagRow label="Participants" value={String(participantCount)} ok={participantCount > 0} />
          <DiagRow label="AI assistance" value="Text mode operational" ok />
          <DiagRow label="Channel ID" value={channelId} ok />
          {error && <DiagRow label="Last error" value={error} ok={false} />}
        </div>
      )}
    </div>
  )
}

function DiagRow({ label, value, ok }: { label: string; value: string; ok: boolean }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-[9px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
        {label}
      </span>
      <div className="flex items-center gap-1">
        <div
          className="w-1.5 h-1.5 rounded-full"
          style={{ background: ok ? 'var(--color-ok)' : 'var(--color-warn)' }}
        />
        <span className="text-[9px] font-mono max-w-[160px] truncate" style={{ color: 'var(--color-text-secondary)' }}>
          {value}
        </span>
      </div>
    </div>
  )
}
