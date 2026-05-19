export type PresenceMode =
  | 'full-screen'
  | 'floating-overlay'
  | 'voice-wave'
  | 'ghost-background'

export interface PresenceState {
  mode: PresenceMode
  opacity: number
  expanded: boolean
}
