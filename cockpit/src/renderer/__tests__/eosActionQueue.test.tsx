// WP-P4-EOS-ACTION-QUEUE-COCKPIT-001 — cockpit approval queue over the
// governed EOS action lifecycle (#183 read / #184 approve-reject / #185
// execute). Proves the packet's button rules, server authority, endpoint
// wiring, and the no-provider/no-secret/no-inline-DB constraints.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, within, waitFor, fireEvent } from '@testing-library/react'
import { readFileSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { setTokenGetter } from '../api/client'
import { EOSActionQueue } from '../components/EOSActionQueue'
import { useEOSActionQueueStore, safeErrorText } from '../stores/eosActionQueueStore'

const _DIR = dirname(fileURLToPath(import.meta.url))
const STORE_PATH = resolve(_DIR, '../stores/eosActionQueueStore.ts')
const COMPONENT_PATH = resolve(_DIR, '../components/EOSActionQueue.tsx')
const BACKEND_ROUTES_PATH = resolve(_DIR, '../../../..', 'transports/api/cockpit_core_eos_routes.py')

const INITIAL_STATE = useEOSActionQueueStore.getState()

interface ProposalOverrides {
  proposal_id?: string
  action_type?: string
  status?: string
  approval_state?: string
  execute_enabled?: boolean
  target_domain?: string | null
}

function proposal(overrides: ProposalOverrides = {}) {
  return {
    proposal_id: 'p1',
    agent_id: 'agent_1',
    agent_name: 'EA Agent',
    user_id: 'user_1',
    action_type: 'create_task',
    target_domain: 'work_management',
    requested_operation: 'Create Task',
    summary: 'Create follow-up task',
    status: 'pending',
    approval_state: 'PENDING',
    requires_approval: true,
    priority: 'medium',
    retry_count: 0,
    max_retries: 3,
    created_at: '2026-07-06T12:00:00',
    updated_at: '2026-07-06T12:00:00',
    source: 'eos_agent_actions',
    beast_head: '9c8725f',
    umh_primitive: 'Approval',
    execute_enabled: false,
    ...overrides,
  }
}

function envelope(proposals: ReturnType<typeof proposal>[]) {
  return {
    projection_id: 'eos',
    surface: 'action_proposals',
    connection_status: 'connected',
    source_build_safe: true,
    execute_enabled: false,
    executor_scope: 'non_provider_allowlist',
    allowed_action_types: 'create_document,create_task',
    retry_policy: 'human_reapproval_required',
    beast_head: '9c8725f',
    seam_id: 'approval-queue-row',
    proposal_count: proposals.length,
    proposals,
    error: null,
  }
}

type RouteHandler = (url: string, opts?: RequestInit) => unknown

function stubFetch(handler: RouteHandler) {
  const mockFetch = vi.fn(async (url: string, opts?: RequestInit) => ({
    ok: true,
    status: 200,
    json: async () => handler(url, opts),
  }))
  vi.stubGlobal('fetch', mockFetch)
  return mockFetch
}

async function loadQueue(handler: RouteHandler) {
  const mockFetch = stubFetch(handler)
  await useEOSActionQueueStore.getState().fetchProposals()
  render(<EOSActionQueue />)
  return mockFetch
}

function row(proposalId: string) {
  return within(screen.getByTestId(`eos-proposal-${proposalId}`))
}

beforeEach(() => {
  useEOSActionQueueStore.setState({ ...INITIAL_STATE, busy: {}, results: {}, proposals: [] }, true)
  vi.stubGlobal('Clerk', undefined)
  setTokenGetter(async () => 'hdr.pay.sig')
})

afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

// ── 1. Queue renders proposals from the read endpoint ───────────────────────

describe('queue rendering', () => {
  it('renders proposals returned by GET /eos/action-proposals', async () => {
    const mockFetch = await loadQueue(() =>
      envelope([
        proposal({ proposal_id: 'p1', action_type: 'create_task' }),
        proposal({ proposal_id: 'p2', action_type: 'send_email', target_domain: 'external_communication' }),
      ]),
    )

    expect(mockFetch.mock.calls[0][0]).toBe('/api/umh/eos/action-proposals')
    expect(screen.getByTestId('eos-proposal-p1')).toBeInTheDocument()
    expect(screen.getByTestId('eos-proposal-p2')).toBeInTheDocument()
    expect(screen.getByText('create_task')).toBeInTheDocument()
    expect(screen.getByText('send_email')).toBeInTheDocument()
    // provenance + retry policy from the envelope
    expect(screen.getByText(/source build-safe/)).toBeInTheDocument()
    expect(screen.getByText(/head 9c8725f/)).toBeInTheDocument()
    expect(screen.getByText(/human_reapproval_required/)).toBeInTheDocument()
  })

  it('renders a safe empty state when the queue has no rows', async () => {
    await loadQueue(() => envelope([]))
    expect(screen.getByText('No EOS action proposals')).toBeInTheDocument()
  })
})

// ── 2–5 + 10. Button rules (server-authoritative) ────────────────────────────

describe('button rules', () => {
  it('pending proposal shows approve + reject but never execute', async () => {
    await loadQueue(() => envelope([proposal({ proposal_id: 'p1', status: 'pending' })]))
    const r = row('p1')
    expect(r.getByRole('button', { name: 'approve' })).toBeInTheDocument()
    expect(r.getByRole('button', { name: 'reject' })).toBeInTheDocument()
    expect(r.queryByRole('button', { name: 'execute' })).toBeNull()
  })

  it('approved allowlisted proposal shows execute but not approve/reject', async () => {
    await loadQueue(() =>
      envelope([
        proposal({ proposal_id: 'p1', status: 'approved', approval_state: 'APPROVED', execute_enabled: true }),
      ]),
    )
    const r = row('p1')
    expect(r.getByRole('button', { name: 'execute' })).toBeInTheDocument()
    expect(r.queryByRole('button', { name: 'approve' })).toBeNull()
    expect(r.queryByRole('button', { name: 'reject' })).toBeNull()
  })

  it('rejected proposal cannot execute (no buttons at all)', async () => {
    await loadQueue(() =>
      envelope([
        proposal({ proposal_id: 'p1', status: 'rejected', approval_state: 'REJECTED', execute_enabled: false }),
      ]),
    )
    const r = row('p1')
    expect(r.queryByRole('button', { name: 'execute' })).toBeNull()
    expect(r.queryByRole('button', { name: 'approve' })).toBeNull()
    expect(r.queryByRole('button', { name: 'reject' })).toBeNull()
  })

  it('executed (completed) proposal cannot execute again', async () => {
    await loadQueue(() =>
      envelope([
        proposal({ proposal_id: 'p1', status: 'completed', approval_state: 'APPROVED', execute_enabled: false }),
      ]),
    )
    expect(row('p1').queryByRole('button', { name: 'execute' })).toBeNull()
  })

  it('failed and expired-style proposals cannot execute', async () => {
    await loadQueue(() =>
      envelope([
        proposal({ proposal_id: 'p1', status: 'failed', approval_state: 'EXPIRED', execute_enabled: false }),
      ]),
    )
    expect(row('p1').queryByRole('button', { name: 'execute' })).toBeNull()
  })

  it('approved PROVIDER action type (send_email) cannot execute — server flag wins', async () => {
    // The #185 read seam marks provider-coupled rows execute_enabled=false
    // even when approved. The UI must follow the server flag, never the status.
    await loadQueue(() =>
      envelope([
        proposal({
          proposal_id: 'p1',
          action_type: 'send_email',
          status: 'approved',
          approval_state: 'APPROVED',
          execute_enabled: false,
        }),
      ]),
    )
    const r = row('p1')
    expect(r.queryByRole('button', { name: 'execute' })).toBeNull()
    expect(r.queryByRole('button', { name: 'approve' })).toBeNull()
  })
})

// ── 6–9 + 11 (server authority). Endpoint wiring ─────────────────────────────

describe('endpoint wiring', () => {
  it('clicking approve calls the approve endpoint and re-reads the queue', async () => {
    let approved = false
    const mockFetch = await loadQueue((url, opts) => {
      if (url.endsWith('/eos/action-proposals/p1/approve')) {
        approved = true
        return {
          surface: 'action_decision', proposal_id: 'p1', decision: 'approve',
          decision_applied: true, prior_status: 'pending', new_status: 'approved',
          decided_at: '2026-07-06T13:00:00', error: null,
        }
      }
      return envelope([
        approved
          ? proposal({ proposal_id: 'p1', status: 'approved', approval_state: 'APPROVED', execute_enabled: true })
          : proposal({ proposal_id: 'p1', status: 'pending' }),
      ])
    })

    fireEvent.click(row('p1').getByRole('button', { name: 'approve' }))

    await waitFor(() => {
      const calls = mockFetch.mock.calls.map((c) => [c[0], (c[1] as RequestInit | undefined)?.method ?? 'GET'])
      expect(calls).toContainEqual(['/api/umh/eos/action-proposals/p1/approve', 'POST'])
    })
    // status changed ONLY because the server refetch said so
    await waitFor(() => {
      expect(row('p1').getByText('APPROVED')).toBeInTheDocument()
      expect(row('p1').getByRole('button', { name: 'execute' })).toBeInTheDocument()
    })
    // decision proof rendered from the server response
    expect(screen.getByText(/decided_at: 2026-07-06T13:00:00/)).toBeInTheDocument()
  })

  it('clicking reject calls the reject endpoint', async () => {
    let rejected = false
    const mockFetch = await loadQueue((url) => {
      if (url.endsWith('/eos/action-proposals/p1/reject')) {
        rejected = true
        return {
          surface: 'action_decision', proposal_id: 'p1', decision: 'reject',
          decision_applied: true, prior_status: 'pending', new_status: 'rejected',
          decided_at: '2026-07-06T13:01:00', error: null,
        }
      }
      return envelope([
        rejected
          ? proposal({ proposal_id: 'p1', status: 'rejected', approval_state: 'REJECTED' })
          : proposal({ proposal_id: 'p1', status: 'pending' }),
      ])
    })

    fireEvent.click(row('p1').getByRole('button', { name: 'reject' }))

    await waitFor(() => {
      const calls = mockFetch.mock.calls.map((c) => [c[0], (c[1] as RequestInit | undefined)?.method ?? 'GET'])
      expect(calls).toContainEqual(['/api/umh/eos/action-proposals/p1/reject', 'POST'])
    })
    await waitFor(() => {
      expect(row('p1').getByText('REJECTED')).toBeInTheDocument()
      expect(row('p1').queryByRole('button', { name: 'execute' })).toBeNull()
    })
  })

  it('clicking execute calls the execute endpoint and renders the proof envelope', async () => {
    let executed = false
    const mockFetch = await loadQueue((url) => {
      if (url.endsWith('/eos/action-proposals/p1/execute')) {
        executed = true
        return {
          surface: 'action_execution', proposal_id: 'p1', action_type: 'create_task',
          execution_applied: true, prior_status: 'approved', new_status: 'completed',
          result_ref: 'task_row_42', executed_at: '2026-07-06T13:05:00',
          envelope_id: 'env_abc123', governance_status: 'completed', error: null,
        }
      }
      return envelope([
        executed
          ? proposal({ proposal_id: 'p1', status: 'completed', approval_state: 'APPROVED', execute_enabled: false })
          : proposal({ proposal_id: 'p1', status: 'approved', approval_state: 'APPROVED', execute_enabled: true }),
      ])
    })

    fireEvent.click(row('p1').getByRole('button', { name: 'execute' }))

    await waitFor(() => {
      const calls = mockFetch.mock.calls.map((c) => [c[0], (c[1] as RequestInit | undefined)?.method ?? 'GET'])
      expect(calls).toContainEqual(['/api/umh/eos/action-proposals/p1/execute', 'POST'])
    })
    // execution result / proof renders from the server response
    await waitFor(() => {
      const result = screen.getByTestId('eos-result-p1')
      expect(result).toHaveTextContent('applied')
      expect(result).toHaveTextContent('result_ref: task_row_42')
      expect(result).toHaveTextContent('executed_at: 2026-07-06T13:05:00')
      expect(result).toHaveTextContent('envelope: env_abc123')
    })
    // and the executed row can never execute again
    await waitFor(() => {
      expect(row('p1').getByText('COMPLETED')).toBeInTheDocument()
      expect(row('p1').queryByRole('button', { name: 'execute' })).toBeNull()
    })
  })

  it('failed execution renders the safe error and requeue notice from the server', async () => {
    await loadQueue((url) => {
      if (url.endsWith('/execute')) {
        return {
          surface: 'action_execution', proposal_id: 'p1', execution_applied: false,
          prior_status: 'approved', new_status: 'pending', requeued_for_reapproval: true,
          retry_count: 1, max_retries: 3,
          error: 'insert failed: connection to <redacted-uri> refused',
        }
      }
      return envelope([
        proposal({ proposal_id: 'p1', status: 'approved', approval_state: 'APPROVED', execute_enabled: true }),
      ])
    })

    fireEvent.click(row('p1').getByRole('button', { name: 'execute' }))

    await waitFor(() => {
      const result = screen.getByTestId('eos-result-p1')
      expect(result).toHaveTextContent('not applied')
      expect(result).toHaveTextContent('requeued for human re-approval')
      expect(result).toHaveTextContent('error: insert failed')
    })
  })
})

// ── 12. Errors shown as safe strings only ────────────────────────────────────

describe('safe error handling', () => {
  it('safeErrorText redacts URI/DSN material and bounds length', () => {
    // Fixture DSN assembled at runtime so the committed source never contains
    // a secret-shaped literal (Gate 8: secret patterns).
    const scheme = 'postgresql'
    const fakePw = ['fake', 'pw', '123'].join('')
    const raw = `connect failed: ${scheme}://user:${fakePw}@db.example.test:5432/eos and more`
    const safe = safeErrorText(raw)
    expect(safe).not.toContain(fakePw)
    expect(safe).not.toContain('db.example.test')
    expect(safe).toContain('<redacted-uri>')
    expect(safeErrorText('x'.repeat(1000)).length).toBeLessThanOrEqual(300)
  })

  it('safeErrorText redacts libpq keyword-style credentials (no :// shape)', () => {
    const fakePw = ['fake', 'pw', '456'].join('')
    const raw = `connection failed: host=db.example.test password=${fakePw} user=eos dbname=prod`
    const safe = safeErrorText(raw)
    expect(safe).not.toContain(fakePw)
    expect(safe).toContain('<redacted-credential>')
  })

  it('queue-level errors from the envelope render scrubbed', async () => {
    const fakePw = ['fake', 'pw', '789'].join('')
    await loadQueue(() => ({
      ...envelope([]),
      error: `db down at ${'postgresql'}://user:${fakePw}@host/db`,
    }))
    const el = screen.getByTestId('eos-queue-error')
    expect(el).toHaveTextContent('<redacted-uri>')
    expect(el.textContent).not.toContain(fakePw)
  })
})

// ── 11 + 13–15. Static constraints on the UI source ─────────────────────────

describe('static constraints', () => {
  const storeSrc = readFileSync(STORE_PATH, 'utf-8')
  const componentSrc = readFileSync(COMPONENT_PATH, 'utf-8')
  const uiSrc = storeSrc + '\n' + componentSrc

  it('UI imports no provider SDKs', () => {
    for (const marker of [
      'googleapis', 'nodemailer', '@notionhq', 'gmail', '@google/', 'google-auth',
      'smtp', '@sendgrid', '@slack/', 'imap',
    ]) {
      expect(uiSrc.toLowerCase()).not.toContain(marker)
    }
  })

  it('UI reads no 1Password/op/env secret material', () => {
    for (const marker of ['op://', '1password', 'process.env', 'OP_SERVICE_ACCOUNT', 'SECRET', 'API_KEY', 'TOKEN=']) {
      expect(uiSrc).not.toContain(marker)
    }
    // no env reads at all in the queue store/component
    expect(uiSrc).not.toContain('import.meta.env')
  })

  it('UI constructs no inline DB writes', () => {
    for (const marker of ['INSERT INTO', 'UPDATE agent_actions', 'DELETE FROM', 'psycopg', 'drizzle', 'pgTable', 'neon(']) {
      expect(uiSrc).not.toContain(marker)
    }
  })

  it('UI mutates no proposal status locally — status only ever comes from server data', () => {
    // The store never writes a status field; proposals are replaced wholesale
    // from the GET response.
    expect(storeSrc).not.toMatch(/status\s*[:=]\s*['"]/)
    expect(componentSrc).not.toMatch(/status\s*[:=]\s*['"]/)
  })

  it('client paths match the backend routes exactly', () => {
    const backendSrc = readFileSync(BACKEND_ROUTES_PATH, 'utf-8')
    const clientPaths = [
      '/eos/action-proposals',
      '/eos/action-proposals/{proposal_id}/approve',
      '/eos/action-proposals/{proposal_id}/reject',
      '/eos/action-proposals/{proposal_id}/execute',
    ]
    for (const p of clientPaths) {
      expect(backendSrc).toContain(`"${p}"`)
    }
    // and the store actually uses those shapes
    expect(storeSrc).toContain("'/eos/action-proposals'")
    for (const verb of ['approve', 'reject', 'execute']) {
      expect(storeSrc).toContain(`/eos/action-proposals/\${proposalId}/${verb}`)
    }
  })

  it('client never supplies the actor identity — server derives it from auth', () => {
    // `decided_by?:` / `executed_by?:` may appear as optional RESPONSE fields;
    // the client must never WRITE them (no `decided_by:` / `executed_by:`
    // object-literal keys in any request body).
    expect(storeSrc).not.toContain('decided_by:')
    expect(storeSrc).not.toContain('executed_by:')
    expect(componentSrc).not.toContain('decided_by')
  })
})

// ── Server-authority under concurrency ───────────────────────────────────────

describe('refetch integrity', () => {
  it('post-mutation refetch bypasses the GET dedup cache with a fresh param', async () => {
    const mockFetch = await loadQueue((url) => {
      if (url.endsWith('/approve')) {
        return { surface: 'action_decision', proposal_id: 'p1', decision_applied: true, new_status: 'approved' }
      }
      return envelope([proposal({ proposal_id: 'p1', status: 'pending' })])
    })

    fireEvent.click(row('p1').getByRole('button', { name: 'approve' }))

    await waitFor(() => {
      const gets = mockFetch.mock.calls
        .map((c) => c[0] as string)
        .filter((u) => u.includes('/eos/action-proposals') && !u.includes('/approve'))
      expect(gets.some((u) => u.includes('?fresh='))).toBe(true)
    })
  })

  it('a stale in-flight GET cannot overwrite a newer response', async () => {
    const staleEnvelope = envelope([proposal({ proposal_id: 'p1', status: 'pending' })])
    const freshEnvelope = envelope([
      proposal({ proposal_id: 'p1', status: 'approved', approval_state: 'APPROVED', execute_enabled: true }),
    ])

    let resolveStale: ((v: unknown) => void) | null = null
    const mockFetch = vi.fn(async (url: string) => {
      if (!url.includes('fresh=')) {
        // first (poll-style) request: hang until we resolve it manually
        return new Promise((res) => {
          resolveStale = (v: unknown) => res({ ok: true, status: 200, json: async () => v })
        }) as Promise<Response>
      }
      return { ok: true, status: 200, json: async () => freshEnvelope } as unknown as Response
    })
    vi.stubGlobal('fetch', mockFetch)

    const store = useEOSActionQueueStore.getState()
    const stalePromise = store.fetchProposals() // issued first, resolves last
    await waitFor(() => expect(resolveStale).not.toBeNull())
    await store.fetchProposals({ fresh: true }) // newer request lands first
    expect(useEOSActionQueueStore.getState().proposals[0].status).toBe('approved')

    resolveStale!(staleEnvelope) // old response arrives late
    await stalePromise
    // the stale payload must NOT clobber the newer server truth
    expect(useEOSActionQueueStore.getState().proposals[0].status).toBe('approved')
  })
})
