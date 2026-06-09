import { create } from 'zustand'
import { registerDevice, heartbeatDevice, disconnectDevice } from '../api/device-presence'

export interface VoiceRouteInfo {
  inputDevice: string
  controlSurface: string
  executionTarget: string
  audioOutputDevice: string
  audioOutputSession: string
  handoffMode: string
  routeReason: string
}

type ClientType = 'mobile_browser' | 'desktop_browser' | 'electron' | 'terminal'

interface DeviceSessionState {
  /** Persisted in localStorage — stable across page reloads */
  deviceId: string
  /** Persisted in sessionStorage — scoped to one browser tab */
  sessionId: string
  clientType: ClientType
  canCaptureAudio: boolean
  canPlayAudio: boolean
  registered: boolean
  lastHeartbeat: string | null
  voiceRoute: VoiceRouteInfo | null
  _heartbeatTimer: ReturnType<typeof setInterval> | null

  initialize: () => Promise<void>
  heartbeat: () => Promise<void>
  setVoiceRoute: (route: VoiceRouteInfo | null) => void
  getRoutingMetadata: () => Record<string, string>
  teardown: () => void
}

function detectClientType(): ClientType {
  if (typeof window === 'undefined') return 'terminal'
  if ((window as Record<string, unknown>).cockpit) return 'electron'
  const ua = navigator.userAgent || ''
  const mobile = /Mobi|Android|iPhone|iPad/i.test(ua) || window.innerWidth < 768
  if (mobile) return 'mobile_browser'
  return 'desktop_browser'
}

function deriveControlSurface(clientType: ClientType): string {
  switch (clientType) {
    case 'electron': return 'electron_cockpit'
    case 'terminal': return 'terminal'
    default: {
      const host = typeof window !== 'undefined' ? window.location.hostname : ''
      if (host === 'localhost' || host === '127.0.0.1' || /^100\./.test(host)) {
        return 'local_cockpit'
      }
      return 'fly_cockpit'
    }
  }
}

function generateId(prefix: string): string {
  const rand = Math.random().toString(36).slice(2, 10)
  return `${prefix}-${Date.now()}-${rand}`
}

function getOrCreateDeviceId(): string {
  try {
    const stored = localStorage.getItem('umh_device_id')
    if (stored) return stored
    const id = generateId('dev')
    localStorage.setItem('umh_device_id', id)
    return id
  } catch {
    return generateId('dev')
  }
}

function getOrCreateSessionId(): string {
  try {
    const stored = sessionStorage.getItem('umh_session_id')
    if (stored) return stored
    const id = generateId('sess')
    sessionStorage.setItem('umh_session_id', id)
    return id
  } catch {
    return generateId('sess')
  }
}

export const useDeviceSessionStore = create<DeviceSessionState>((set, get) => ({
  deviceId: '',
  sessionId: '',
  clientType: 'desktop_browser',
  canCaptureAudio: true,
  canPlayAudio: true,
  registered: false,
  lastHeartbeat: null,
  voiceRoute: null,
  _heartbeatTimer: null,

  initialize: async () => {
    const deviceId = getOrCreateDeviceId()
    const sessionId = getOrCreateSessionId()
    const clientType = detectClientType()
    const canCaptureAudio = clientType !== 'terminal'
    const canPlayAudio = clientType !== 'terminal'

    set({ deviceId, sessionId, clientType, canCaptureAudio, canPlayAudio })

    try {
      await registerDevice({
        device_id: deviceId,
        session_id: sessionId,
        client_type: clientType,
        control_surface: deriveControlSurface(clientType),
        can_capture_audio: canCaptureAudio,
        can_play_audio: canPlayAudio,
      })
      set({ registered: true, lastHeartbeat: new Date().toISOString() })
    } catch (err) {
      // Registration failure is non-critical — device presence degrades gracefully
      console.debug('[DeviceSession] registration failed:', err)
    }

    // Start heartbeat every 20 seconds
    const timer = setInterval(() => { get().heartbeat() }, 20_000)
    set({ _heartbeatTimer: timer })
  },

  heartbeat: async () => {
    const { sessionId, registered } = get()
    if (!sessionId || !registered) return
    try {
      await heartbeatDevice(sessionId)
      set({ lastHeartbeat: new Date().toISOString() })
    } catch (err) {
      console.debug('[DeviceSession] heartbeat failed:', err)
    }
  },

  setVoiceRoute: (route) => set({ voiceRoute: route }),

  getRoutingMetadata: () => {
    const { deviceId, sessionId, clientType } = get()
    return {
      source_device_id: deviceId,
      source_session_id: sessionId,
      control_surface: deriveControlSurface(clientType),
      audio_return_route: 'source_device',
    }
  },

  teardown: () => {
    const { _heartbeatTimer, sessionId, registered } = get()
    if (_heartbeatTimer) {
      clearInterval(_heartbeatTimer)
      set({ _heartbeatTimer: null })
    }
    if (sessionId && registered) {
      disconnectDevice(sessionId).catch(() => {
        // best-effort disconnect
      })
    }
  },
}))
