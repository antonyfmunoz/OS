import { describe, it, expect, beforeEach } from 'vitest'
import { useCockpitStore } from '../stores/cockpitStore'

beforeEach(() => {
  useCockpitStore.setState({
    activePanel: 'commandcenter',
    chatOpen: false,
    splitPanel: null,
    mode: 'EXECUTE',
    windowMode: 'maximized',
    railCollapsed: true,
    rightRailCollapsed: true,
    controlPanelExpanded: false,
    apiStatus: 'disconnected',
    wsStatus: 'disconnected',
    voiceStatus: 'disconnected',
  })
})

describe('cockpitStore — panel navigation', () => {
  it('sets active panel directly for non-redirected panels', () => {
    useCockpitStore.getState().setPanel('organism')
    expect(useCockpitStore.getState().activePanel).toBe('organism')
  })

  it('redirects dashboard to commandcenter', () => {
    useCockpitStore.getState().setPanel('dashboard')
    expect(useCockpitStore.getState().activePanel).toBe('commandcenter')
  })

  it('redirects tasks to work', () => {
    useCockpitStore.getState().setPanel('tasks')
    expect(useCockpitStore.getState().activePanel).toBe('work')
  })

  it('redirects agents to canvas', () => {
    useCockpitStore.getState().setPanel('agents')
    expect(useCockpitStore.getState().activePanel).toBe('canvas')
  })

  it('redirects workflows to canvas', () => {
    useCockpitStore.getState().setPanel('workflows')
    expect(useCockpitStore.getState().activePanel).toBe('canvas')
  })
})

describe('cockpitStore — mode cycling', () => {
  it('defaults to EXECUTE mode', () => {
    expect(useCockpitStore.getState().mode).toBe('EXECUTE')
  })

  it('cycles through PLAN and REVIEW', () => {
    const { setMode } = useCockpitStore.getState()
    setMode('PLAN')
    expect(useCockpitStore.getState().mode).toBe('PLAN')
    setMode('REVIEW')
    expect(useCockpitStore.getState().mode).toBe('REVIEW')
  })
})

describe('cockpitStore — window mode', () => {
  it('shrinks from maximized to large-fab', () => {
    useCockpitStore.getState().cycleWindowMode('shrink')
    expect(useCockpitStore.getState().windowMode).toBe('large-fab')
  })

  it('does not expand past maximized', () => {
    useCockpitStore.getState().cycleWindowMode('expand')
    expect(useCockpitStore.getState().windowMode).toBe('maximized')
  })

  it('does not shrink past invisible', () => {
    const { cycleWindowMode } = useCockpitStore.getState()
    cycleWindowMode('shrink')
    cycleWindowMode('shrink')
    cycleWindowMode('shrink')
    cycleWindowMode('shrink')
    cycleWindowMode('shrink') // past end
    expect(useCockpitStore.getState().windowMode).toBe('invisible')
  })
})

describe('cockpitStore — connection status', () => {
  it('sets API status', () => {
    useCockpitStore.getState().setApiStatus('connected')
    expect(useCockpitStore.getState().apiStatus).toBe('connected')
  })

  it('sets status via unified setter', () => {
    const { setConnectionStatus } = useCockpitStore.getState()
    setConnectionStatus('ws', 'connecting')
    setConnectionStatus('voice', 'connected')
    const state = useCockpitStore.getState()
    expect(state.wsStatus).toBe('connecting')
    expect(state.voiceStatus).toBe('connected')
  })
})

describe('cockpitStore — rail toggles', () => {
  it('toggles left rail', () => {
    expect(useCockpitStore.getState().railCollapsed).toBe(true)
    useCockpitStore.getState().toggleRail()
    expect(useCockpitStore.getState().railCollapsed).toBe(false)
  })

  it('toggles right rail', () => {
    expect(useCockpitStore.getState().rightRailCollapsed).toBe(true)
    useCockpitStore.getState().toggleRightRail()
    expect(useCockpitStore.getState().rightRailCollapsed).toBe(false)
  })
})
