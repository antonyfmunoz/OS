import { fetchApi } from './client'

export interface DeviceRegistration {
  device_id: string
  session_id: string
  operator_id?: string
  client_type: 'mobile_browser' | 'desktop_browser' | 'electron' | 'terminal'
  device_label?: string
  control_surface?: string
  can_capture_audio?: boolean
  can_play_audio?: boolean
  can_capture_video?: boolean
  reachable_nodes?: string[]
}

export interface DeviceSession {
  device_id: string
  session_id: string
  operator_id: string
  client_type: string
  device_label: string
  control_surface: string
  current_panel: string
  can_capture_audio: boolean
  can_play_audio: boolean
  can_capture_video: boolean
  reachable_nodes: string[]
  last_seen: string
  status: string
}

export async function registerDevice(session: DeviceRegistration): Promise<void> {
  await fetchApi('/device/register', {
    method: 'POST',
    body: JSON.stringify(session),
  })
}

export async function heartbeatDevice(
  sessionId: string,
  updates: Record<string, unknown> = {},
): Promise<void> {
  await fetchApi('/device/heartbeat', {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId, ...updates }),
  })
}

export async function disconnectDevice(sessionId: string): Promise<void> {
  await fetchApi('/device/disconnect', {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId }),
  })
}

export async function getActiveSessions(): Promise<DeviceSession[]> {
  const res = await fetchApi<{ sessions: DeviceSession[] }>('/device/sessions')
  return res.sessions ?? []
}
