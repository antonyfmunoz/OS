import { useEffect, useState, type FormEvent } from 'react'
import { Video, Users, ListChecks, FileText, Plus, Check, CircleDot } from 'lucide-react'
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

export function MeetingRoomPanel({ channelId }: { channelId: string }) {
  const meetingStates = useRoomsStore((s) => s.meetingStates)
  const fetchMeeting = useRoomsStore((s) => s.fetchMeeting)
  const updateMeeting = useRoomsStore((s) => s.updateMeeting)
  const addMeetingActionItem = useRoomsStore((s) => s.addMeetingActionItem)
  const toggleMeetingActionItem = useRoomsStore((s) => s.toggleMeetingActionItem)

  const meeting = meetingStates[channelId]
  const [newAction, setNewAction] = useState('')
  const [newActionAssignee, setNewActionAssignee] = useState('')

  useEffect(() => {
    fetchMeeting(channelId)
  }, [channelId, fetchMeeting])

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

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      <div className="flex-1 p-4 space-y-4 max-w-3xl mx-auto w-full">
        <div className="flex items-center gap-3 mb-4">
          <div
            className="w-12 h-12 rounded-full flex items-center justify-center"
            style={{ background: 'var(--color-violet-dim)' }}
          >
            <Video size={22} style={{ color: 'var(--color-violet)' }} />
          </div>
          <div>
            <h3 className="text-sm font-mono font-semibold" style={{ color: 'var(--color-text-primary)' }}>
              Meeting Room
            </h3>
            <p className="text-[10px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
              Native video transport pending — metadata and meeting intelligence operational
            </p>
          </div>
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
      </div>
    </div>
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
