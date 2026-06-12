import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import {
  Video,
  VideoOff,
  Mic,
  MicOff,
  PhoneOff,
  Monitor,
  MonitorOff,
  MessageSquare,
  Send,
  Plus,
  Check,
  CircleDot,
  Link2,
  Copy,
  Bot,
  Activity,
  Wifi,
  WifiOff,
  ChevronDown,
  ChevronRight,
  Users,
  X,
  Maximize2,
  Minimize2,
  AppWindow,
  Globe,
  Camera,
  ScreenShare,
  AlertTriangle,
  VolumeX,
  Volume2,
  Shield,
  Eye,
  FileText,
  ListTodo,
  CheckCircle2,
  ClipboardList,
  StickyNote,
} from 'lucide-react'
import { useRoomsStore } from '../../stores/roomsStore'
import { useConferenceRoom, detectScreenShareSupport } from '../../hooks/useConferenceRoom'
import type {
  ConferenceParticipant,
  ConferenceDiagnostics,
  ConferenceRoomState,
  MediaStreamSource,
  AIGovernancePermissions,
  ProductionTestItem,
} from '../../hooks/useConferenceRoom'
import type { RoomMessage, MeetingMode } from '../../types/rooms'

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

const SOURCE_TYPE_ICONS: Record<string, typeof Monitor> = {
  camera: Camera,
  screen: Monitor,
  window: AppWindow,
  tab: Globe,
  application: AppWindow,
}

const SOURCE_TYPE_LABELS: Record<string, string> = {
  camera: 'Camera',
  screen: 'Screen',
  window: 'Window',
  tab: 'Browser Tab',
  application: 'Application',
}

function isIOS(): boolean {
  if (typeof navigator === 'undefined') return false
  return /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
}

type MeetingSidePanel = 'chat' | 'agenda' | 'notes' | 'actions' | null

export function MeetingRoomPanel({ channelId, onOpenChat }: { channelId: string; onOpenChat?: () => void }) {
  const channels = useRoomsStore((s) => s.channels)
  const channel = channels.find((c) => c.id === channelId)
  const meetingStates = useRoomsStore((s) => s.meetingStates)
  const fetchMeeting = useRoomsStore((s) => s.fetchMeeting)
  const updateMeeting = useRoomsStore((s) => s.updateMeeting)
  const addMeetingActionItem = useRoomsStore((s) => s.addMeetingActionItem)
  const toggleMeetingActionItem = useRoomsStore((s) => s.toggleMeetingActionItem)
  const activeServerId = useRoomsStore((s) => s.activeServerId)
  const invites = useRoomsStore((s) => s.invites)
  const createInvite = useRoomsStore((s) => s.createInvite)
  const fetchInvites = useRoomsStore((s) => s.fetchInvites)

  const conf = useConferenceRoom(channelId)
  const meeting = meetingStates[channelId]
  const [sidePanel, setSidePanel] = useState<MeetingSidePanel>(null)
  const [focusedStream, setFocusedStream] = useState<string | null>(null)
  const [copiedLink, setCopiedLink] = useState(false)

  const isConnected = conf.state === 'connected'

  useEffect(() => {
    fetchMeeting(channelId)
    if (activeServerId) fetchInvites(activeServerId)
  }, [channelId, fetchMeeting, activeServerId, fetchInvites])

  const endMeeting = useRoomsStore((s) => s.endMeeting)

  const handleCopyInvite = async () => {
    let code = invites.find((inv) => !inv.revoked)?.code
    if (!code && activeServerId) {
      const invite = await createInvite(activeServerId, {
        channel_id: channelId,
        room_type: 'meeting',
        expires_hours: 24,
      })
      code = invite?.code
    }
    if (code) {
      const link = `${window.location.origin}/join/${code}`
      await navigator.clipboard.writeText(link)
      setCopiedLink(true)
      setTimeout(() => setCopiedLink(false), 2000)
    }
  }

  const handleEndMeeting = useCallback(() => {
    endMeeting(channelId)
    conf.leave()
  }, [channelId, endMeeting, conf])

  const allStreams: Array<MediaStreamSource & { participantName: string }> = []
  conf.streams.forEach((sources, identity) => {
    const participant = conf.participants.find(p => p.identity === identity)
    const name = participant?.name || identity
    for (const source of sources) {
      allStreams.push({ ...source, participantName: name })
    }
  })

  const togglePanel = (panel: MeetingSidePanel) => {
    setSidePanel(prev => prev === panel ? null : panel)
  }

  return (
    <div className="flex flex-col h-full overflow-hidden"
      style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
    >
      <div className="flex flex-1 min-h-0">
        {/* Main content area */}
        <div className={`flex-1 flex flex-col min-h-0 ${sidePanel ? 'sm:border-r' : ''}`}
          style={{ borderColor: 'var(--color-border)' }}
        >
          <div className="flex-1 overflow-y-auto overscroll-contain">
            <div className="flex flex-col items-center justify-start p-3 sm:p-4 max-w-4xl mx-auto w-full">
              {/* Header */}
              <MeetingHeader
                name={channel?.name || 'Meeting Room'}
                state={conf.state}
                participantCount={conf.participants.length}
                copiedLink={copiedLink}
                onCopyInvite={handleCopyInvite}
              />

              <ConnectionBanner state={conf.state} error={conf.error} reconnectAttempts={conf.diagnostics.reconnectAttempts} />

              {/* Meeting Mode selector - pre-join only */}
              {!isConnected && (
                <MeetingModeSelector
                  channelId={channelId}
                  currentMode={meeting?.mode}
                  onUpdateMeeting={updateMeeting}
                />
              )}

              {/* Objective - pre-join only */}
              {!isConnected && (
                <div className="w-full mb-3">
                  <input
                    value={meeting?.objective || ''}
                    onChange={(e) => updateMeeting(channelId, { objective: e.target.value })}
                    placeholder="Meeting objective..."
                    className="w-full text-xs font-mono px-3 py-2 rounded border bg-transparent outline-none"
                    style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-primary)' }}
                  />
                </div>
              )}

              {/* Video/Screen grid */}
              {isConnected && allStreams.length > 0 && (
                <StreamGrid
                  streams={allStreams}
                  focusedStream={focusedStream}
                  onFocus={setFocusedStream}
                  getVideoElement={conf.getVideoElement}
                  onStopStream={conf.stopStream}
                  localIdentity={conf.participants.find(p => p.identity === conf.diagnostics.participantIdentity)?.identity}
                />
              )}

              {/* Participant strip */}
              {isConnected && conf.participants.length > 0 && (
                <ParticipantStrip participants={conf.participants} />
              )}

              {/* In-meeting objective display */}
              {isConnected && meeting?.objective && (
                <div className="w-full rounded px-3 py-2 mb-3 border"
                  style={{ borderColor: 'var(--color-border)', background: 'var(--color-surface)' }}
                >
                  <span className="text-[9px] font-mono uppercase tracking-wider" style={{ color: 'var(--color-text-tertiary)' }}>
                    Objective
                  </span>
                  <p className="text-[11px] font-mono" style={{ color: 'var(--color-text-primary)' }}>
                    {meeting.objective}
                  </p>
                </div>
              )}

              {/* Disconnected reconnect */}
              {conf.state === 'disconnected' && (
                <div className="w-full rounded px-3 py-2 mb-3 text-center"
                  style={{ background: 'var(--color-warn-dim)' }}
                >
                  <p className="text-[10px] font-mono mb-1" style={{ color: 'var(--color-warn)' }}>
                    Connection lost
                  </p>
                  <button onClick={conf.join}
                    className="text-[10px] font-mono px-3 py-1 rounded"
                    style={{ background: 'var(--color-ok)', color: 'var(--color-canvas)' }}
                  >
                    Reconnect
                  </button>
                </div>
              )}

              <AIGovernanceBadge
                governance={conf.aiGovernance}
                onUpdate={conf.setAIGovernance}
              />

              <ProductionTestChecklist items={conf.productionChecklist} />

              <DiagnosticsPanel diagnostics={conf.diagnostics} state={conf.state} />
            </div>
          </div>

          {/* Control bar */}
          <MeetingControlBar
            state={conf.state}
            isMuted={conf.isMuted}
            isDeafened={conf.isDeafened}
            isVideoOn={conf.isVideoOn}
            preJoinMicEnabled={conf.preJoinMicEnabled}
            preJoinVideoEnabled={conf.preJoinVideoEnabled}
            localStreamCount={conf.localStreams.filter(s => s.sourceType !== 'camera').length}
            canAddStream={conf.canAddStream}
            sidePanel={sidePanel}
            error={conf.error}
            onJoin={conf.join}
            onLeave={conf.leave}
            onEndMeeting={handleEndMeeting}
            onToggleMute={conf.toggleMute}
            onToggleDeafen={conf.toggleDeafen}
            onTogglePreJoinMic={conf.togglePreJoinMic}
            onTogglePreJoinVideo={conf.togglePreJoinVideo}
            onToggleVideo={conf.toggleVideo}
            onAddScreenShare={conf.addScreenShare}
            onStopAllStreams={conf.stopAllStreams}
            onTogglePanel={togglePanel}
          />
        </div>

        {/* Side panel */}
        {sidePanel && (
          <>
            {/* Mobile: bottom sheet drawer — keeps meeting context visible */}
            <div className="sm:hidden fixed inset-x-0 bottom-0 z-40 flex flex-col"
              style={{
                background: 'var(--color-canvas)',
                borderTop: '1px solid var(--color-border)',
                height: '60vh',
                maxHeight: '60vh',
                borderRadius: '12px 12px 0 0',
                boxShadow: '0 -4px 20px rgba(0,0,0,0.3)',
              }}
            >
              <div className="flex items-center justify-between px-3 h-9 shrink-0">
                <div className="w-8 h-1 rounded-full mx-auto" style={{ background: 'var(--color-border)' }} />
              </div>
              <div className="flex items-center justify-between px-3 pb-1 shrink-0">
                <span className="text-[11px] font-mono font-semibold capitalize" style={{ color: 'var(--color-text-primary)' }}>
                  {sidePanel === 'actions' ? 'Action Items' : sidePanel}
                </span>
                <button onClick={() => setSidePanel(null)}
                  className="p-1.5 rounded min-w-[36px] min-h-[36px] flex items-center justify-center"
                  style={{ color: 'var(--color-text-tertiary)' }}
                >
                  <X size={16} />
                </button>
              </div>
              <SidePanelContent
                panel={sidePanel}
                channelId={channelId}
                meeting={meeting}
                updateMeeting={updateMeeting}
                addActionItem={addMeetingActionItem}
                toggleActionItem={toggleMeetingActionItem}
              />
            </div>
            {/* Mobile backdrop */}
            <div className="sm:hidden fixed inset-0 z-30" style={{ background: 'rgba(0,0,0,0.3)' }}
              onClick={() => setSidePanel(null)}
            />

            {/* Desktop: side panel */}
            <div className="hidden sm:flex w-80 flex-col min-h-0" style={{ maxWidth: '50%' }}>
              <div className="flex items-center justify-between px-3 h-8 border-b shrink-0"
                style={{ borderColor: 'var(--color-border)' }}
              >
                <span className="text-[10px] font-mono font-semibold capitalize" style={{ color: 'var(--color-text-secondary)' }}>
                  {sidePanel === 'actions' ? 'Action Items' : sidePanel}
                </span>
                <button onClick={() => setSidePanel(null)} className="p-0.5 rounded">
                  <X size={10} style={{ color: 'var(--color-text-tertiary)' }} />
                </button>
              </div>
              <SidePanelContent
                panel={sidePanel}
                channelId={channelId}
                meeting={meeting}
                updateMeeting={updateMeeting}
                addActionItem={addMeetingActionItem}
                toggleActionItem={toggleMeetingActionItem}
              />
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function SidePanelContent({
  panel,
  channelId,
  meeting,
  updateMeeting,
  addActionItem,
  toggleActionItem,
}: {
  panel: MeetingSidePanel
  channelId: string
  meeting: ReturnType<typeof useRoomsStore.getState>['meetingStates'][string]
  updateMeeting: ReturnType<typeof useRoomsStore.getState>['updateMeeting']
  addActionItem: ReturnType<typeof useRoomsStore.getState>['addMeetingActionItem']
  toggleActionItem: ReturnType<typeof useRoomsStore.getState>['toggleMeetingActionItem']
}) {
  switch (panel) {
    case 'chat':
      return <MeetingChat channelId={channelId} />
    case 'agenda':
      return <AgendaPanel channelId={channelId} meeting={meeting} updateMeeting={updateMeeting} />
    case 'notes':
      return <NotesPanel channelId={channelId} meeting={meeting} updateMeeting={updateMeeting} />
    case 'actions':
      return <ActionsPanel channelId={channelId} meeting={meeting} addActionItem={addActionItem} toggleActionItem={toggleActionItem} />
    default:
      return null
  }
}

function MeetingHeader({
  name,
  state,
  participantCount,
  copiedLink,
  onCopyInvite,
}: {
  name: string
  state: ConferenceRoomState
  participantCount: number
  copiedLink: boolean
  onCopyInvite: () => void
}) {
  const isConnected = state === 'connected'

  return (
    <div className="flex items-center gap-3 w-full mb-3">
      <div className="w-10 h-10 rounded-full flex items-center justify-center shrink-0"
        style={{ background: isConnected ? 'var(--color-ok-dim)' : 'var(--color-violet-dim)' }}
      >
        <Video size={18} style={{
          color: isConnected ? 'var(--color-ok)' : 'var(--color-violet)',
        }} />
      </div>
      <div className="flex-1 min-w-0">
        <h3 className="text-sm font-mono font-semibold" style={{ color: 'var(--color-text-primary)' }}>
          {name}
        </h3>
        <p className="text-[9px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
          {isConnected ? `${participantCount} in meeting` : 'Meeting room — join to participate'}
        </p>
      </div>
      <button
        onClick={onCopyInvite}
        className="flex items-center gap-1.5 text-[9px] font-mono px-2 py-1 rounded border shrink-0"
        style={{
          borderColor: 'var(--color-border)',
          color: copiedLink ? 'var(--color-ok)' : 'var(--color-text-secondary)',
        }}
      >
        {copiedLink ? <Check size={10} /> : <Link2 size={10} />}
        {copiedLink ? 'Copied!' : 'Invite'}
      </button>
    </div>
  )
}

function MeetingModeSelector({
  channelId,
  currentMode,
  onUpdateMeeting,
}: {
  channelId: string
  currentMode: MeetingMode | undefined
  onUpdateMeeting: (channelId: string, updates: { mode: MeetingMode }) => void
}) {
  return (
    <div className="w-full mb-3">
      <div className="text-[9px] font-mono uppercase tracking-wider mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
        Meeting Type
      </div>
      <div className="flex flex-wrap gap-1.5">
        {MEETING_MODES.map((m) => (
          <button
            key={m.value}
            onClick={() => onUpdateMeeting(channelId, { mode: m.value })}
            className="text-[9px] font-mono px-2 py-1 rounded border"
            style={{
              borderColor: currentMode === m.value ? 'var(--color-violet)' : 'var(--color-border)',
              color: currentMode === m.value ? 'var(--color-violet)' : 'var(--color-text-tertiary)',
              background: currentMode === m.value ? 'var(--color-violet-dim)' : 'transparent',
            }}
          >
            {m.label}
          </button>
        ))}
      </div>
    </div>
  )
}

function MeetingControlBar({
  state,
  isMuted,
  isDeafened,
  isVideoOn,
  preJoinMicEnabled,
  preJoinVideoEnabled,
  localStreamCount,
  canAddStream,
  sidePanel,
  error,
  onJoin,
  onLeave,
  onEndMeeting,
  onToggleMute,
  onToggleDeafen,
  onTogglePreJoinMic,
  onTogglePreJoinVideo,
  onToggleVideo,
  onAddScreenShare,
  onStopAllStreams,
  onTogglePanel,
}: {
  state: ConferenceRoomState
  isMuted: boolean
  isDeafened: boolean
  isVideoOn: boolean
  preJoinMicEnabled: boolean
  preJoinVideoEnabled: boolean
  localStreamCount: number
  canAddStream: boolean
  sidePanel: MeetingSidePanel
  error: string | null
  onJoin: () => void
  onLeave: () => void
  onEndMeeting: () => void
  onToggleMute: () => void
  onToggleDeafen: () => void
  onTogglePreJoinMic: () => void
  onTogglePreJoinVideo: () => void
  onToggleVideo: () => void
  onAddScreenShare: () => void
  onStopAllStreams: () => void
  onTogglePanel: (panel: MeetingSidePanel) => void
}) {
  const [shareMenuOpen, setShareMenuOpen] = useState(false)
  const isConnected = state === 'connected' || state === 'reconnecting'
  const screenShareCap = detectScreenShareSupport() ? 'browser' : 'none'
  const showIOSShareNote = isIOS() && screenShareCap === 'none'

  // Pre-join state
  if (!isConnected && state !== 'failed' && state !== 'disconnected') {
    const isJoining = state === 'connecting' || state === 'requesting_permissions'
    return (
      <div className="flex items-center justify-center gap-1.5 px-3 sm:px-4 py-3 border-t shrink-0"
        style={{
          borderColor: 'var(--color-border)',
          paddingBottom: 'max(env(safe-area-inset-bottom, 0px), 12px)',
        }}
      >
        <ControlButton
          active={preJoinMicEnabled}
          danger={!preJoinMicEnabled}
          icon={preJoinMicEnabled ? Mic : MicOff}
          label={preJoinMicEnabled ? 'Mic On' : 'Mic Off'}
          onClick={onTogglePreJoinMic}
          disabled={isJoining}
        />
        <ControlButton
          active={preJoinVideoEnabled}
          icon={preJoinVideoEnabled ? Video : VideoOff}
          label={preJoinVideoEnabled ? 'Cam On' : 'Cam Off'}
          onClick={onTogglePreJoinVideo}
          disabled={isJoining}
        />
        <button onClick={onJoin}
          disabled={isJoining}
          className="flex items-center gap-2 text-xs font-mono px-5 py-2.5 rounded transition-colors"
          style={{
            background: isJoining ? 'var(--color-surface-raised)' : 'var(--color-ok)',
            color: isJoining ? 'var(--color-text-tertiary)' : 'var(--color-canvas)',
          }}
        >
          {isJoining ? 'Joining...' : 'Join Meeting'}
        </button>
        <ControlButton
          active={sidePanel === 'chat'}
          icon={MessageSquare}
          label="Chat"
          onClick={() => onTogglePanel('chat')}
        />
      </div>
    )
  }

  // Failed/disconnected state
  if (state === 'failed' || state === 'disconnected') {
    return (
      <div className="flex items-center justify-center gap-1.5 px-3 sm:px-4 py-3 border-t shrink-0"
        style={{
          borderColor: 'var(--color-border)',
          paddingBottom: 'max(env(safe-area-inset-bottom, 0px), 12px)',
        }}
      >
        <ControlButton
          active={preJoinMicEnabled}
          danger={!preJoinMicEnabled}
          icon={preJoinMicEnabled ? Mic : MicOff}
          label={preJoinMicEnabled ? 'Mic On' : 'Mic Off'}
          onClick={onTogglePreJoinMic}
        />
        <ControlButton
          active={preJoinVideoEnabled}
          danger={!preJoinVideoEnabled}
          icon={preJoinVideoEnabled ? Video : VideoOff}
          label={preJoinVideoEnabled ? 'Cam On' : 'Cam Off'}
          onClick={onTogglePreJoinVideo}
        />
        <button onClick={onJoin}
          className="flex items-center gap-2 text-xs font-mono px-4 py-2 rounded transition-colors"
          style={{ background: 'var(--color-ok)', color: 'var(--color-canvas)' }}
        >
          Retry
        </button>
        <ControlButton
          active={sidePanel === 'chat'}
          icon={MessageSquare}
          label="Chat"
          onClick={() => onTogglePanel('chat')}
        />
        {error && (
          <span className="text-[9px] font-mono max-w-48 truncate hidden sm:inline" style={{ color: 'var(--color-danger)' }}>
            {error}
          </span>
        )}
      </div>
    )
  }

  // Connected state
  return (
    <div className="relative flex items-center justify-center gap-1 sm:gap-1.5 px-2 sm:px-3 py-2.5 border-t shrink-0"
      style={{
        borderColor: 'var(--color-border)',
        background: 'var(--color-surface)',
        paddingBottom: 'max(env(safe-area-inset-bottom, 0px), 10px)',
      }}
    >
      <ControlButton
        active={!isMuted}
        danger={isMuted}
        icon={isMuted ? MicOff : Mic}
        label={isMuted ? 'Unmute' : 'Mute'}
        onClick={onToggleMute}
      />
      <ControlButton
        active={isVideoOn}
        icon={isVideoOn ? Video : VideoOff}
        label={isVideoOn ? 'Stop Video' : 'Video'}
        onClick={onToggleVideo}
      />

      <div className="relative">
        <ControlButton
          active={localStreamCount > 0}
          icon={localStreamCount > 0 ? ScreenShare : Monitor}
          label={localStreamCount > 0 ? `Sharing (${localStreamCount})` : 'Share'}
          onClick={() => setShareMenuOpen(!shareMenuOpen)}
        />
        {localStreamCount > 0 && (
          <div className="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full flex items-center justify-center text-[7px] font-mono font-bold"
            style={{ background: 'var(--color-cyan)', color: 'var(--color-canvas)' }}
          >
            {localStreamCount}
          </div>
        )}
      </div>

      <div className="w-px h-6 mx-0.5 hidden sm:block" style={{ background: 'var(--color-border)' }} />

      <ControlButton
        active={sidePanel === 'chat'}
        icon={MessageSquare}
        label="Chat"
        onClick={() => onTogglePanel('chat')}
      />
      <ControlButton
        active={sidePanel === 'agenda'}
        icon={ClipboardList}
        label="Agenda"
        onClick={() => onTogglePanel('agenda')}
      />
      <ControlButton
        active={sidePanel === 'notes'}
        icon={StickyNote}
        label="Notes"
        onClick={() => onTogglePanel('notes')}
      />
      <ControlButton
        active={sidePanel === 'actions'}
        icon={ListTodo}
        label="Actions"
        onClick={() => onTogglePanel('actions')}
      />

      <div className="w-px h-6 mx-0.5 hidden sm:block" style={{ background: 'var(--color-border)' }} />
      <button onClick={onLeave}
        className="flex items-center gap-1.5 text-[10px] font-mono px-2 sm:px-3 py-2 rounded transition-colors"
        style={{ background: 'var(--color-danger)', color: 'var(--color-canvas)' }}
      >
        <PhoneOff size={13} /> <span className="hidden sm:inline">Leave</span>
      </button>
      <button onClick={onEndMeeting}
        className="flex items-center gap-1.5 text-[10px] font-mono px-2 sm:px-3 py-2 rounded transition-colors hidden sm:flex"
        style={{ background: 'var(--color-danger)', color: 'var(--color-canvas)', opacity: 0.8 }}
        title="End meeting for all participants"
      >
        <PhoneOff size={13} /> End Meeting
      </button>

      {shareMenuOpen && (
        <ShareMenu
          canAdd={canAddStream}
          showIOSNote={showIOSShareNote}
          screenShareSupported={screenShareCap !== 'none'}
          localStreamCount={localStreamCount}
          onAddScreen={() => { onAddScreenShare(); setShareMenuOpen(false) }}
          onStopAll={() => { onStopAllStreams(); setShareMenuOpen(false) }}
          onClose={() => setShareMenuOpen(false)}
        />
      )}
    </div>
  )
}

function ShareMenu({
  canAdd,
  showIOSNote,
  screenShareSupported,
  localStreamCount,
  onAddScreen,
  onStopAll,
  onClose,
}: {
  canAdd: boolean
  showIOSNote: boolean
  screenShareSupported: boolean
  localStreamCount: number
  onAddScreen: () => void
  onStopAll: () => void
  onClose: () => void
}) {
  return (
    <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-56 rounded-lg border shadow-lg overflow-hidden"
      style={{ background: 'var(--color-surface-raised)', borderColor: 'var(--color-border)', zIndex: 50 }}
    >
      <div className="px-3 py-2 border-b flex items-center justify-between"
        style={{ borderColor: 'var(--color-border)' }}
      >
        <span className="text-[10px] font-mono font-semibold" style={{ color: 'var(--color-text-primary)' }}>
          Share Sources
        </span>
        <button onClick={onClose} className="p-0.5 rounded">
          <X size={10} style={{ color: 'var(--color-text-tertiary)' }} />
        </button>
      </div>

      {!screenShareSupported && (
        <div className="px-3 py-2 flex items-start gap-2"
          style={{ background: 'var(--color-warn-dim)' }}
        >
          <AlertTriangle size={12} style={{ color: 'var(--color-warn)' }} className="flex-shrink-0 mt-0.5" />
          <p className="text-[9px] font-mono" style={{ color: 'var(--color-warn)' }}>
            {showIOSNote
              ? 'Screen share is not supported in iOS Safari. Use the native app wrapper or a desktop browser.'
              : 'Screen share is not available in this browser.'}
          </p>
        </div>
      )}

      {screenShareSupported && (
        <div className="p-1">
          <ShareMenuItem
            icon={Monitor}
            label="Screen"
            desc="Share your entire screen"
            disabled={!canAdd}
            onClick={onAddScreen}
          />
          <ShareMenuItem
            icon={AppWindow}
            label="Window"
            desc="Share an application window"
            disabled={!canAdd}
            onClick={onAddScreen}
          />
          <ShareMenuItem
            icon={Globe}
            label="Browser Tab"
            desc="Share a browser tab"
            disabled={!canAdd}
            onClick={onAddScreen}
          />
        </div>
      )}

      {localStreamCount > 0 && (
        <div className="px-1 pb-1 border-t" style={{ borderColor: 'var(--color-border)' }}>
          <button onClick={onStopAll}
            className="w-full flex items-center gap-2 px-2 py-1.5 rounded text-[9px] font-mono transition-colors hover:bg-surface"
            style={{ color: 'var(--color-danger)' }}
          >
            <MonitorOff size={12} />
            Stop All Streams ({localStreamCount})
          </button>
        </div>
      )}
    </div>
  )
}

function ShareMenuItem({
  icon: Icon,
  label,
  desc,
  disabled,
  onClick,
}: {
  icon: typeof Monitor
  label: string
  desc: string
  disabled: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="w-full flex items-center gap-2 px-2 py-1.5 rounded text-left transition-colors hover:bg-surface disabled:opacity-40 disabled:cursor-not-allowed"
    >
      <Icon size={14} style={{ color: disabled ? 'var(--color-text-tertiary)' : 'var(--color-cyan)' }} />
      <div>
        <span className="text-[10px] font-mono block" style={{ color: 'var(--color-text-primary)' }}>{label}</span>
        <span className="text-[8px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>{desc}</span>
      </div>
    </button>
  )
}

function ControlButton({
  active,
  danger,
  icon: Icon,
  label,
  onClick,
  disabled,
}: {
  active: boolean
  danger?: boolean
  icon: typeof Mic
  label: string
  onClick: () => void
  disabled?: boolean
}) {
  return (
    <button onClick={onClick}
      disabled={disabled}
      className="flex flex-col items-center gap-0.5 px-2 sm:px-2.5 py-1.5 rounded transition-colors disabled:opacity-40 disabled:cursor-not-allowed min-w-[44px] min-h-[44px] justify-center"
      style={{
        background: danger ? 'var(--color-danger)' : active ? 'var(--color-surface-raised)' : 'transparent',
        color: danger ? 'var(--color-canvas)' : active ? 'var(--color-text-primary)' : 'var(--color-text-tertiary)',
      }}
      title={label}
    >
      <Icon size={16} />
      <span className="text-[8px] font-mono">{label}</span>
    </button>
  )
}

function ConnectionBanner({ state, error, reconnectAttempts }: { state: ConferenceRoomState; error: string | null; reconnectAttempts: number }) {
  if (state === 'idle' || state === 'connected') return null

  const config: Record<string, { bg: string; color: string; text: string; icon: typeof Wifi }> = {
    requesting_permissions: { bg: 'var(--color-cyan-glow)', color: 'var(--color-cyan)', text: 'Requesting mic...', icon: Mic },
    connecting: { bg: 'var(--color-cyan-glow)', color: 'var(--color-cyan)', text: 'Joining...', icon: Activity },
    reconnecting: {
      bg: 'var(--color-warn-dim)',
      color: 'var(--color-warn)',
      text: reconnectAttempts > 0 ? `Reconnecting (${reconnectAttempts}/5)...` : 'Reconnecting...',
      icon: Activity,
    },
    suspended: { bg: 'var(--color-warn-dim)', color: 'var(--color-warn)', text: 'Backgrounded — tap to resume', icon: Activity },
    failed: { bg: 'var(--color-danger-dim)', color: 'var(--color-danger)', text: error || 'Connection failed', icon: WifiOff },
    disconnected: { bg: 'var(--color-warn-dim)', color: 'var(--color-warn)', text: 'Disconnected', icon: WifiOff },
  }

  const c = config[state]
  if (!c) return null
  const Icon = c.icon
  const animating = state === 'connecting' || state === 'reconnecting' || state === 'requesting_permissions'

  return (
    <div className="w-full rounded px-3 py-2 mb-3 flex items-center gap-2" style={{ background: c.bg }}>
      <Icon size={12} style={{ color: c.color }}
        className={animating ? 'animate-pulse' : ''}
      />
      <span className="text-[10px] font-mono flex-1" style={{ color: c.color }}>{c.text}</span>
    </div>
  )
}

function StreamGrid({
  streams,
  focusedStream,
  onFocus,
  getVideoElement,
  onStopStream,
  localIdentity,
}: {
  streams: Array<MediaStreamSource & { participantName: string }>
  focusedStream: string | null
  onFocus: (sid: string | null) => void
  getVideoElement: (sid: string) => HTMLVideoElement | null
  onStopStream: (sid: string) => Promise<void>
  localIdentity: string | undefined
}) {
  if (streams.length === 0) return null

  const focused = focusedStream ? streams.find(s => s.trackSid === focusedStream) : null

  if (focused) {
    return (
      <div className="w-full mb-3">
        <StreamTile
          stream={focused}
          focused
          getVideoElement={getVideoElement}
          onFocus={() => onFocus(null)}
          onStop={focused.participantIdentity === localIdentity ? () => onStopStream(focused.trackSid) : undefined}
          isOwner={focused.participantIdentity === localIdentity}
        />
        {streams.length > 1 && (
          <div className="flex gap-1.5 mt-1.5 overflow-x-auto pb-1 -mx-1 px-1">
            {streams.filter(s => s.trackSid !== focusedStream).map(s => (
              <div key={s.trackSid} className="flex-shrink-0" style={{ width: 120, height: 68 }}>
                <StreamTile
                  stream={s}
                  compact
                  getVideoElement={getVideoElement}
                  onFocus={() => onFocus(s.trackSid)}
                  onStop={s.participantIdentity === localIdentity ? () => onStopStream(s.trackSid) : undefined}
                  isOwner={s.participantIdentity === localIdentity}
                />
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }

  const gridCols = streams.length === 1 ? 'grid-cols-1' :
    streams.length <= 4 ? 'grid-cols-2' : 'grid-cols-2 sm:grid-cols-3'

  return (
    <div className={`w-full grid ${gridCols} gap-1.5 mb-3`}>
      {streams.map(s => (
        <StreamTile
          key={s.trackSid}
          stream={s}
          getVideoElement={getVideoElement}
          onFocus={() => onFocus(s.trackSid)}
          onStop={s.participantIdentity === localIdentity ? () => onStopStream(s.trackSid) : undefined}
          isOwner={s.participantIdentity === localIdentity}
        />
      ))}
    </div>
  )
}

function StreamTile({
  stream,
  focused,
  compact,
  getVideoElement,
  onFocus,
  onStop,
  isOwner,
}: {
  stream: MediaStreamSource & { participantName: string }
  focused?: boolean
  compact?: boolean
  getVideoElement: (sid: string) => HTMLVideoElement | null
  onFocus: () => void
  onStop?: () => void
  isOwner: boolean
}) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mountedSidRef = useRef<string | null>(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    let cancelled = false
    let pollTimer: ReturnType<typeof setInterval> | undefined

    function tryMount() {
      if (cancelled || !container) return
      if (mountedSidRef.current === stream.trackSid) return

      const el = getVideoElement(stream.trackSid)
      if (el) {
        el.style.display = 'block'
        el.style.width = '100%'
        el.style.height = '100%'
        el.style.objectFit = 'contain'
        el.style.borderRadius = '4px'
        el.style.position = 'absolute'
        container.appendChild(el)
        mountedSidRef.current = stream.trackSid
        if (pollTimer) clearInterval(pollTimer)
      }
    }

    tryMount()
    if (mountedSidRef.current !== stream.trackSid) {
      pollTimer = setInterval(tryMount, 200)
    }

    return () => {
      cancelled = true
      if (pollTimer) clearInterval(pollTimer)
      if (mountedSidRef.current === stream.trackSid) {
        const el = getVideoElement(stream.trackSid)
        if (el) {
          el.style.display = 'none'
          el.style.position = 'absolute'
          document.body.appendChild(el)
        }
        mountedSidRef.current = null
      }
    }
  }, [stream.trackSid, getVideoElement])

  const Icon = SOURCE_TYPE_ICONS[stream.sourceType] || Monitor
  const label = SOURCE_TYPE_LABELS[stream.sourceType] || stream.sourceType
  const dims = stream.dimensions
  const fps = stream.frameRate

  return (
    <div
      className={`relative rounded border overflow-hidden group ${focused ? 'aspect-video' : compact ? '' : 'aspect-video'}`}
      style={{
        borderColor: 'var(--color-border)',
        background: 'var(--color-surface)',
        height: compact ? '100%' : undefined,
      }}
    >
      <div ref={containerRef} className="absolute inset-0" />

      <div className="absolute bottom-0 left-0 right-0 px-2 py-1 flex items-center gap-1.5"
        style={{ background: 'rgba(0,0,0,0.6)' }}
      >
        <Icon size={compact ? 8 : 10} style={{ color: 'var(--color-cyan)' }} />
        {!compact && (
          <>
            <span className="text-[9px] font-mono truncate" style={{ color: '#fff' }}>
              {stream.participantName}
            </span>
            <span className="text-[8px] font-mono" style={{ color: 'rgba(255,255,255,0.6)' }}>
              {label}
            </span>
            {dims && (
              <span className="text-[7px] font-mono ml-auto" style={{ color: 'rgba(255,255,255,0.5)' }}>
                {dims.width}x{dims.height}{fps ? `@${Math.round(fps)}` : ''}
              </span>
            )}
          </>
        )}
      </div>

      <div className="absolute top-1 right-1 flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
        <button onClick={onFocus}
          className="p-1 rounded"
          style={{ background: 'rgba(0,0,0,0.6)' }}
          title={focused ? 'Minimize' : 'Focus'}
        >
          {focused ? <Minimize2 size={10} color="#fff" /> : <Maximize2 size={10} color="#fff" />}
        </button>
        {isOwner && onStop && (
          <button onClick={onStop}
            className="p-1 rounded"
            style={{ background: 'rgba(220,38,38,0.8)' }}
            title="Stop stream"
          >
            <X size={10} color="#fff" />
          </button>
        )}
      </div>
    </div>
  )
}

function ParticipantStrip({ participants }: { participants: ConferenceParticipant[] }) {
  return (
    <div className="w-full flex items-center gap-2 mb-3 overflow-x-auto pb-1">
      {participants.map((p) => (
        <div key={p.identity} className="flex items-center gap-1.5 px-2 py-1.5 rounded shrink-0"
          style={{
            background: 'var(--color-surface)',
            outline: p.isSpeaking ? '2px solid var(--color-ok)' : '1px solid var(--color-border)',
            outlineOffset: p.isSpeaking ? '1px' : 0,
          }}
        >
          <div className="w-6 h-6 rounded-full flex items-center justify-center text-[8px] font-mono font-bold"
            style={{ background: 'var(--color-surface-overlay)', color: 'var(--color-text-secondary)' }}
          >
            {p.name.charAt(0).toUpperCase()}
          </div>
          <span className="text-[9px] font-mono" style={{ color: 'var(--color-text-primary)' }}>
            {p.name}
          </span>
          {p.identity.startsWith('guest-') && (
            <span className="text-[6px] px-0.5 rounded" style={{ background: 'var(--color-warn-dim, rgba(255,170,0,0.1))', color: 'var(--color-warn, #ffaa00)' }}>GUEST</span>
          )}
          <div className="flex items-center gap-1">
            {p.isVideoOn && <Video size={9} style={{ color: 'var(--color-ok)' }} />}
            {p.streamCount > 0 && <ScreenShare size={9} style={{ color: 'var(--color-cyan)' }} />}
            {p.isMuted ? (
              <MicOff size={9} style={{ color: 'var(--color-danger)' }} />
            ) : (
              <Mic size={9} style={{ color: 'var(--color-ok)' }} />
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

function AIGovernanceBadge({
  governance,
  onUpdate,
}: {
  governance: AIGovernancePermissions
  onUpdate: (patch: Partial<AIGovernancePermissions>) => void
}) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="w-full rounded border mt-1 mb-2" style={{ borderColor: 'var(--color-border)' }}>
      <button onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-1.5 px-3 py-1.5 text-[9px] font-mono"
        style={{ color: 'var(--color-text-tertiary)' }}
      >
        <Bot size={10} style={{ color: 'var(--color-violet)' }} />
        <span>AI Governance</span>
        {expanded ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
      </button>
      {expanded && (
        <div className="px-3 pb-2 space-y-1.5">
          <p className="text-[9px] font-mono" style={{ color: 'var(--color-text-secondary)' }}>
            AI participants can join this room with operator permission.
          </p>
          <GovernanceToggle icon={Users} label="Join" field="ai_can_join" value={governance.ai_can_join} onUpdate={onUpdate} />
          <GovernanceToggle icon={Eye} label="Listen" field="ai_can_listen" value={governance.ai_can_listen} onUpdate={onUpdate} />
          <GovernanceToggle icon={Mic} label="Speak" field="ai_can_speak" value={governance.ai_can_speak} onUpdate={onUpdate} />
          <GovernanceToggle icon={FileText} label="Transcribe" field="ai_can_transcribe" value={governance.ai_can_transcribe} onUpdate={onUpdate} />
          <GovernanceToggle icon={StickyNote} label="Summarize" field="ai_can_summarize" value={governance.ai_can_summarize} onUpdate={onUpdate} />
          <GovernanceToggle icon={ListTodo} label="Create Actions" field="ai_can_create_action_items" value={governance.ai_can_create_action_items} onUpdate={onUpdate} />
          <GovernanceRow icon={Shield} label="Access Log" value={governance.ai_access_logged ? 'All AI actions recorded' : 'Logging disabled'} />
        </div>
      )}
    </div>
  )
}

function GovernanceToggle({
  icon: Icon,
  label,
  field,
  value,
  onUpdate,
}: {
  icon: typeof Bot
  label: string
  field: keyof AIGovernancePermissions
  value: boolean
  onUpdate: (patch: Partial<AIGovernancePermissions>) => void
}) {
  return (
    <button
      onClick={() => onUpdate({ [field]: !value })}
      className="flex items-center gap-2 text-[9px] font-mono w-full"
    >
      <Icon size={10} style={{ color: 'var(--color-violet)' }} />
      <span style={{ color: 'var(--color-text-secondary)', minWidth: 80 }}>{label}</span>
      <div className="w-3 h-3 rounded-full border"
        style={{
          borderColor: value ? 'var(--color-ok)' : 'var(--color-border)',
          background: value ? 'var(--color-ok)' : 'transparent',
        }}
      />
      <span style={{ color: value ? 'var(--color-ok)' : 'var(--color-text-tertiary)' }}>
        {value ? 'Enabled' : 'Disabled'}
      </span>
    </button>
  )
}

function GovernanceRow({ icon: Icon, label, value }: { icon: typeof Bot; label: string; value: string }) {
  return (
    <div className="flex items-center gap-2 text-[9px] font-mono">
      <Icon size={10} style={{ color: 'var(--color-violet)' }} />
      <span style={{ color: 'var(--color-text-secondary)', minWidth: 80 }}>{label}</span>
      <span style={{ color: 'var(--color-text-tertiary)' }}>{value}</span>
    </div>
  )
}

function ProductionTestChecklist({ items }: { items: ProductionTestItem[] }) {
  const [expanded, setExpanded] = useState(false)

  const passCount = items.filter(i => i.status === 'pass').length

  return (
    <div className="w-full rounded border mt-1 mb-2" style={{ borderColor: 'var(--color-border)' }}>
      <button onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-1.5 px-3 py-1.5 text-[9px] font-mono"
        style={{ color: 'var(--color-text-tertiary)' }}
      >
        <CheckCircle2 size={10} style={{ color: passCount === items.length ? 'var(--color-ok)' : 'var(--color-text-tertiary)' }} />
        <span>Production Test Checklist ({passCount}/{items.length})</span>
        {expanded ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
      </button>
      {expanded && (
        <div className="px-3 pb-2 space-y-0.5">
          {items.map((item) => (
            <div key={item.label} className="flex items-center justify-between">
              <span className="text-[9px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
                {item.label}
              </span>
              <div className="flex items-center gap-1">
                <div className="w-1.5 h-1.5 rounded-full"
                  style={{
                    background: item.status === 'pass' ? 'var(--color-ok)' :
                      item.status === 'fail' ? 'var(--color-danger)' :
                        item.status === 'pending' ? 'var(--color-warn)' :
                          'var(--color-text-tertiary)',
                  }}
                />
                <span className="text-[9px] font-mono max-w-[140px] truncate"
                  style={{ color: 'var(--color-text-secondary)' }}
                >
                  {item.detail}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function MeetingChat({ channelId }: { channelId: string }) {
  const messages = useRoomsStore((s) => s.messages)
  const fetchMessages = useRoomsStore((s) => s.fetchMessages)
  const sendMessage = useRoomsStore((s) => s.sendMessage)
  const typingUsers = useRoomsStore((s) => s.typingUsers)

  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchMessages(channelId)
  }, [channelId, fetchMessages])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length])

  const handleSend = async (e: FormEvent) => {
    e.preventDefault()
    const text = input.trim()
    if (!text || sending) return
    setSending(true)
    setInput('')
    await sendMessage(channelId, text)
    setSending(false)
  }

  const channelMessages = messages.filter((m) => m.channel_id === channelId)
  const typing = typingUsers[channelId] || []

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto overscroll-contain">
        {channelMessages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <p className="text-[10px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
              No messages yet
            </p>
          </div>
        )}
        {channelMessages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} />
        ))}
        <div ref={bottomRef} />
      </div>

      {typing.length > 0 && (
        <div className="px-3 py-0.5">
          <span className="text-[8px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
            {typing.join(', ')} typing...
          </span>
        </div>
      )}

      <form onSubmit={handleSend}
        className="flex items-center gap-1.5 px-2 py-1.5 border-t shrink-0"
        style={{
          borderColor: 'var(--color-border)',
          paddingBottom: 'max(env(safe-area-inset-bottom, 0px), 6px)',
        }}
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Message..."
          disabled={sending}
          className="flex-1 text-[10px] font-mono px-2 py-1.5 rounded border bg-transparent outline-none"
          style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-primary)' }}
        />
        <button type="submit"
          disabled={!input.trim() || sending}
          className="p-1.5 rounded transition-colors min-w-[36px] min-h-[36px] flex items-center justify-center"
          style={{
            background: input.trim() ? 'var(--color-cyan)' : 'transparent',
            color: input.trim() ? 'var(--color-canvas)' : 'var(--color-text-tertiary)',
          }}
        >
          <Send size={11} />
        </button>
      </form>
    </div>
  )
}

function ChatMessage({ message: msg }: { message: RoomMessage }) {
  if (msg.deleted) return null

  return (
    <div className="px-3 py-1 hover:bg-surface-raised transition-colors">
      <div className="flex items-baseline gap-1.5">
        <span className="text-[9px] font-mono font-semibold" style={{ color: 'var(--color-cyan)' }}>
          {msg.author_name}
        </span>
        <span className="text-[8px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
          {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>
      <p className="text-[10px] font-mono whitespace-pre-wrap break-words" style={{ color: 'var(--color-text-primary)' }}>
        {msg.content}
      </p>
    </div>
  )
}

function AgendaPanel({
  channelId,
  meeting,
  updateMeeting,
}: {
  channelId: string
  meeting: ReturnType<typeof useRoomsStore.getState>['meetingStates'][string]
  updateMeeting: ReturnType<typeof useRoomsStore.getState>['updateMeeting']
}) {
  return (
    <div className="flex flex-col h-full p-3 overflow-y-auto">
      <div className="space-y-1 mb-3">
        {(meeting?.agenda || []).map((item, i) => (
          <div key={i} className="flex items-center gap-2">
            <CircleDot size={10} style={{ color: 'var(--color-cyan)' }} />
            <span className="text-[11px] font-mono" style={{ color: 'var(--color-text-primary)' }}>{item}</span>
          </div>
        ))}
        {(meeting?.agenda || []).length === 0 && (
          <p className="text-[10px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
            No agenda items yet
          </p>
        )}
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
        className="w-full text-xs font-mono px-3 py-2 rounded border bg-transparent outline-none mt-auto"
        style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-primary)' }}
      />

      {/* Decisions section */}
      <div className="mt-4">
        <div className="text-[9px] font-mono uppercase tracking-wider mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
          Decisions
        </div>
        <div className="space-y-1 mb-2">
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
          className="w-full text-xs font-mono px-3 py-2 rounded border bg-transparent outline-none"
          style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-primary)' }}
        />
      </div>
    </div>
  )
}

function NotesPanel({
  channelId,
  meeting,
  updateMeeting,
}: {
  channelId: string
  meeting: ReturnType<typeof useRoomsStore.getState>['meetingStates'][string]
  updateMeeting: ReturnType<typeof useRoomsStore.getState>['updateMeeting']
}) {
  return (
    <div className="flex flex-col h-full p-3">
      <textarea
        value={meeting?.notes || ''}
        onChange={(e) => updateMeeting(channelId, { notes: e.target.value })}
        placeholder="Meeting notes..."
        className="flex-1 w-full text-xs font-mono px-3 py-2 rounded border bg-transparent outline-none resize-none"
        style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-primary)' }}
      />
    </div>
  )
}

function ActionsPanel({
  channelId,
  meeting,
  addActionItem,
  toggleActionItem,
}: {
  channelId: string
  meeting: ReturnType<typeof useRoomsStore.getState>['meetingStates'][string]
  addActionItem: ReturnType<typeof useRoomsStore.getState>['addMeetingActionItem']
  toggleActionItem: ReturnType<typeof useRoomsStore.getState>['toggleMeetingActionItem']
}) {
  const [newAction, setNewAction] = useState('')
  const [newAssignee, setNewAssignee] = useState('')

  const handleAdd = async (e: FormEvent) => {
    e.preventDefault()
    if (!newAction.trim()) return
    await addActionItem(channelId, {
      text: newAction.trim(),
      assignee: newAssignee.trim() || 'unassigned',
      due_date: null,
      completed: false,
    })
    setNewAction('')
    setNewAssignee('')
  }

  return (
    <div className="flex flex-col h-full p-3 overflow-y-auto">
      <div className="space-y-1 flex-1">
        {(meeting?.action_items || []).map((item) => (
          <div key={item.id} className="flex items-center gap-2">
            <button onClick={() => toggleActionItem(channelId, item.id)}>
              <div
                className="w-4 h-4 rounded border flex items-center justify-center shrink-0"
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
            <span className="text-[9px] font-mono shrink-0" style={{ color: 'var(--color-text-tertiary)' }}>
              {item.assignee}
            </span>
          </div>
        ))}
        {(meeting?.action_items || []).length === 0 && (
          <p className="text-[10px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
            No action items yet
          </p>
        )}
      </div>

      <form onSubmit={handleAdd} className="flex gap-2 mt-3 shrink-0">
        <input
          value={newAction}
          onChange={(e) => setNewAction(e.target.value)}
          placeholder="New action item"
          className="flex-1 text-xs font-mono px-3 py-1.5 rounded border bg-transparent outline-none"
          style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-primary)' }}
        />
        <input
          value={newAssignee}
          onChange={(e) => setNewAssignee(e.target.value)}
          placeholder="Assignee"
          className="w-20 text-xs font-mono px-2 py-1.5 rounded border bg-transparent outline-none"
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
    </div>
  )
}

function DiagnosticsPanel({ diagnostics, state }: { diagnostics: ConferenceDiagnostics; state: string }) {
  const [expanded, setExpanded] = useState(false)

  if (state === 'idle' && !diagnostics.lastEvent) return null

  return (
    <div className="w-full rounded border mt-2" style={{ borderColor: 'var(--color-border)' }}>
      <button onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-1 px-3 py-1.5 text-[9px] font-mono"
        style={{ color: 'var(--color-text-tertiary)' }}
      >
        {expanded ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
        diagnostics
      </button>
      {expanded && (
        <div className="px-3 pb-2 space-y-1">
          <DiagRow label="state" value={state} />
          <DiagRow label="join stage" value={diagnostics.joinStage} />
          <DiagRow label="mic state" value={diagnostics.micState} />
          <DiagRow label="cam state" value={diagnostics.cameraState} />
          <DiagRow label="url" value={diagnostics.livekitUrl} />
          <DiagRow label="room" value={diagnostics.roomName} />
          <DiagRow label="identity" value={diagnostics.participantIdentity} />
          <DiagRow label="token" value={diagnostics.tokenReceived ? 'yes' : 'no'} />
          <DiagRow label="signal" value={diagnostics.signalConnected ? 'yes' : 'no'} />
          <DiagRow label="mic perm" value={diagnostics.micPermission} />
          <DiagRow label="mic actual" value={diagnostics.micEnabledActual ? 'on' : 'off'} />
          <DiagRow label="audio sid" value={diagnostics.audioTrackSid} />
          {diagnostics.lastMicError && <DiagRow label="mic error" value={diagnostics.lastMicError} error />}
          <DiagRow label="cam perm" value={diagnostics.cameraPermission} />
          <DiagRow label="cam actual" value={diagnostics.cameraEnabledActual ? 'on' : 'off'} />
          <DiagRow label="video sid" value={diagnostics.videoTrackSid} />
          {diagnostics.lastVideoError && <DiagRow label="cam error" value={diagnostics.lastVideoError} error />}
          <DiagRow label="screenshare" value={diagnostics.screenShareSupport ? 'yes' : 'no'} />
          {diagnostics.lastScreenShareError && <DiagRow label="share error" value={diagnostics.lastScreenShareError} error />}
          <DiagRow label="reconnects" value={String(diagnostics.reconnectAttempts)} />
          <DiagRow label="published" value={String(diagnostics.publishedTrackCount)} />
          <DiagRow label="subscribed" value={String(diagnostics.subscribedTrackCount)} />
          <DiagRow label="visibility" value={diagnostics.visibility.lastVisibilityState} />
          {diagnostics.visibility.backgroundDurationMs !== null && (
            <DiagRow label="bg duration" value={`${Math.round(diagnostics.visibility.backgroundDurationMs / 1000)}s`} />
          )}
          {diagnostics.joinTiming.joinClickToOperationalMs !== null && (
            <DiagRow label="join total" value={`${diagnostics.joinTiming.joinClickToOperationalMs}ms`} />
          )}
          <DiagRow label="last" value={diagnostics.lastEvent} />
          {diagnostics.lastError && (
            <DiagRow label="error" value={diagnostics.lastError} error />
          )}
        </div>
      )}
    </div>
  )
}

function DiagRow({ label, value, error }: { label: string; value: string | null; error?: boolean }) {
  return (
    <div className="flex gap-2 text-[9px] font-mono">
      <span style={{ color: 'var(--color-text-tertiary)', minWidth: 80 }}>{label}</span>
      <span style={{ color: error ? 'var(--color-danger)' : 'var(--color-text-secondary)', wordBreak: 'break-all' }}>
        {value ?? '—'}
      </span>
    </div>
  )
}
