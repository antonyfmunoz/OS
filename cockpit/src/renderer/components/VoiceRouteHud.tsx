import React from 'react'
import { useVoiceStore } from '../stores/voiceStore'
import { useDeviceSessionStore } from '../stores/deviceSessionStore'

/**
 * VoiceRouteHud — compact display of the active voice route.
 * Shown only when mic or TTS is active.
 *
 * VOICE ROUTE
 * Input: desktop_browser
 * Output: source_device
 * Target: cockpit
 * Mode: conversation
 */
export function VoiceRouteHud() {
  const micState = useVoiceStore((s) => s.micState)
  const ttsState = useVoiceStore((s) => s.ttsState)
  const voiceRoute = useDeviceSessionStore((s) => s.voiceRoute)

  const isActive =
    micState !== 'idle' ||
    ttsState === 'speaking' ||
    ttsState === 'generating_tts'

  if (!isActive && !voiceRoute) return null

  const route = voiceRoute

  const labelStyle: React.CSSProperties = {
    fontSize: 9,
    fontFamily: 'monospace',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    color: 'var(--color-text-tertiary)',
  }

  const valueStyle: React.CSSProperties = {
    fontSize: 9,
    fontFamily: 'monospace',
    color: 'var(--color-cyan)',
  }

  return (
    <div
      style={{
        marginBottom: 6,
        padding: '4px 6px',
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderLeft: '2px solid var(--color-cyan)',
        borderRadius: 2,
      }}
    >
      <div style={{ ...labelStyle, color: 'var(--color-cyan)', marginBottom: 3 }}>
        VOICE ROUTE
      </div>
      {route ? (
        <>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={labelStyle}>Input</span>
            <span style={valueStyle}>{route.inputDevice || 'unknown'}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={labelStyle}>Output</span>
            <span style={valueStyle}>{route.audioOutputDevice || 'source'}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={labelStyle}>Target</span>
            <span style={valueStyle}>{route.executionTarget || 'cockpit'}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={labelStyle}>Mode</span>
            <span style={valueStyle}>{route.handoffMode || 'conversation'}</span>
          </div>
        </>
      ) : (
        <div style={{ ...labelStyle, color: 'var(--color-text-tertiary)' }}>
          {micState !== 'idle' ? 'Resolving route...' : 'No route data'}
        </div>
      )}
    </div>
  )
}
