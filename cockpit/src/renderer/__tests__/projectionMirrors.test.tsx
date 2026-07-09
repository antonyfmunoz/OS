// P4S-30 — LyfeOS + CreatorOS projection mirror panels.
//
// Proves the panel renders read-surface truth only (registration, runtime
// registration, connection status, seed info, link-out to the native app)
// and never reimplements projection-native UX. Endpoints under test:
// GET /api/umh/lyfeos/activation, GET /api/umh/creatoros/activation
// (transports/api/cockpit_core_lyfeos_routes.py /
// cockpit_core_creatoros_routes.py).
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { setTokenGetter } from '../api/client'
import { ProjectionMirrorsPanel } from '../panels/ProjectionMirrorsPanel'
import { useLyfeOSMirrorStore, useCreatorOSMirrorStore } from '../stores/projectionMirrorStore'
import type { ProjectionMirrorReadiness } from '../stores/projectionMirrorStore'

const LYFEOS_INITIAL = useLyfeOSMirrorStore.getState()
const CREATOROS_INITIAL = useCreatorOSMirrorStore.getState()

function readiness(overrides: Partial<ProjectionMirrorReadiness> = {}): ProjectionMirrorReadiness {
  return {
    projection_id: 'lyfeos',
    registered_in_seed: true,
    runtime_registered: false,
    seed: {
      app_name: 'lyfeos-app',
      health_url: '/api/health',
      public_url: 'https://lyfeos.net',
      l4_workflow: 'clerk_login_renders',
    },
    connection_status: 'disconnected',
    boot_eligible: false,
    poll_interval: null,
    error: null,
    ...overrides,
  }
}

type RouteHandler = (url: string) => unknown

function stubFetch(handler: RouteHandler) {
  const mockFetch = vi.fn(async (url: string) => ({
    ok: true,
    status: 200,
    json: async () => handler(url),
  }))
  vi.stubGlobal('fetch', mockFetch)
  return mockFetch
}

beforeEach(() => {
  useLyfeOSMirrorStore.setState({ ...LYFEOS_INITIAL }, true)
  useCreatorOSMirrorStore.setState({ ...CREATOROS_INITIAL }, true)
  vi.stubGlobal('Clerk', undefined)
  setTokenGetter(async () => 'hdr.pay.sig')
})

afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe('projection mirror endpoint wiring', () => {
  it('fetches both /lyfeos/activation and /creatoros/activation on mount', async () => {
    const mockFetch = stubFetch((url) => {
      if (url.includes('lyfeos')) return readiness({ projection_id: 'lyfeos' })
      if (url.includes('creatoros')) return readiness({ projection_id: 'cos' })
      throw new Error(`unexpected url ${url}`)
    })

    render(<ProjectionMirrorsPanel />)

    await screen.findByTestId('projection-mirror-lyfeos')
    await screen.findByTestId('projection-mirror-cos')

    const calledUrls = mockFetch.mock.calls.map((c) => c[0])
    expect(calledUrls).toContain('/api/umh/lyfeos/activation')
    expect(calledUrls).toContain('/api/umh/creatoros/activation')
  })
})

describe('read-surface truth rendering', () => {
  it('renders registration, runtime registration, and connection status from the server response', async () => {
    stubFetch((url) => {
      if (url.includes('lyfeos')) {
        return readiness({
          projection_id: 'lyfeos',
          registered_in_seed: true,
          runtime_registered: true,
          connection_status: 'configured',
        })
      }
      return readiness({ projection_id: 'cos', registered_in_seed: false, connection_status: 'disconnected' })
    })

    render(<ProjectionMirrorsPanel />)

    const lyfeosCard = within(await screen.findByTestId('projection-mirror-lyfeos'))
    expect(lyfeosCard.getByText('configured')).toBeInTheDocument()
    expect(lyfeosCard.getByText('lyfeos-app')).toBeInTheDocument()
    expect(lyfeosCard.getByText('clerk_login_renders')).toBeInTheDocument()

    const cosCard = within(await screen.findByTestId('projection-mirror-cos'))
    expect(cosCard.getByText('disconnected')).toBeInTheDocument()
  })

  it('renders a link-out to the native app public_url, never absorbing its UX', async () => {
    stubFetch((url) => {
      if (url.includes('lyfeos')) return readiness({ projection_id: 'lyfeos', seed: { ...readiness().seed, public_url: 'https://lyfeos.net' } })
      return readiness({ projection_id: 'cos', seed: { ...readiness().seed, public_url: 'https://creatoros.example' } })
    })

    render(<ProjectionMirrorsPanel />)

    const lyfeosCard = within(await screen.findByTestId('projection-mirror-lyfeos'))
    const link = lyfeosCard.getByTestId('projection-mirror-open-native') as HTMLAnchorElement
    expect(link.href).toBe('https://lyfeos.net/')
    expect(link.target).toBe('_blank')
  })

  it('shows "no public URL" affordance safely when seed has none', async () => {
    stubFetch((url) => {
      if (url.includes('lyfeos')) {
        return readiness({ projection_id: 'lyfeos', seed: { app_name: null, health_url: null, public_url: null, l4_workflow: null } })
      }
      return readiness({ projection_id: 'cos' })
    })

    render(<ProjectionMirrorsPanel />)

    const lyfeosCard = within(await screen.findByTestId('projection-mirror-lyfeos'))
    expect(lyfeosCard.queryByTestId('projection-mirror-open-native')).toBeNull()
    expect(lyfeosCard.getByText('No public URL registered')).toBeInTheDocument()
  })

  it('never raises on an env-disabled-safe error response', async () => {
    stubFetch((url) => {
      if (url.includes('lyfeos')) {
        return { error: 'boom', projection_id: 'lyfeos', registered_in_seed: false }
      }
      return readiness({ projection_id: 'cos' })
    })

    render(<ProjectionMirrorsPanel />)

    const lyfeosCard = within(await screen.findByTestId('projection-mirror-lyfeos'))
    expect(lyfeosCard.getByTestId('projection-mirror-error')).toHaveTextContent('boom')
  })
})

describe('mirror discipline — no projection-native UX reimplemented', () => {
  it('never renders approve/reject/execute controls (that is EOS action-queue territory, not a read mirror)', async () => {
    stubFetch((url) => {
      if (url.includes('lyfeos')) return readiness({ projection_id: 'lyfeos' })
      return readiness({ projection_id: 'cos' })
    })

    render(<ProjectionMirrorsPanel />)
    await screen.findByTestId('projection-mirror-lyfeos')
    await screen.findByTestId('projection-mirror-cos')

    expect(screen.queryByRole('button', { name: /approve/i })).toBeNull()
    expect(screen.queryByRole('button', { name: /reject/i })).toBeNull()
    expect(screen.queryByRole('button', { name: /execute/i })).toBeNull()
    // Only the read-only link-out affordance is interactive.
    expect(screen.getAllByTestId('projection-mirror-open-native').length).toBeGreaterThan(0)
  })
})
