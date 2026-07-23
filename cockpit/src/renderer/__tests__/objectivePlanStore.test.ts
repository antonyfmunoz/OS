// Regression: the objective-plan store's decide() must establish post-decision
// truth EXCLUSIVELY from canonical rereads (fetchPlan/fetchSurface), never from
// the decision POST's echoed body. Owner order (FINAL WAVE 1 MERGE-READINESS
// CLOSURE, defect A): echoed POST data cannot masquerade as canonical truth.
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { ApiError } from '../api/client'

// fetchApi is the single network seam the store uses. Mock it so each call in a
// decide() flow (POST decision → GET plan → GET surface) can be driven precisely.
const fetchApiMock = vi.fn()
vi.mock('../api/client', async () => {
  // Preserve the real ApiError class (structural 409 classification depends on it).
  const actual = await vi.importActual<typeof import('../api/client')>('../api/client')
  return { ...actual, fetchApi: (...args: unknown[]) => fetchApiMock(...args) }
})

// Imported AFTER the mock is registered so the store binds the mocked fetchApi.
import { useObjectivePlanStore, type PlanDetail } from '../stores/objectivePlanStore'

const PLAN_ID = 'opr-abc123'

function makePlan(overrides: Partial<PlanDetail> = {}): PlanDetail {
  return {
    plan_record_id: PLAN_ID,
    objective_id: 'goal-deadbeef',
    graph_version: 2,
    status: 'approved',
    conversation_id: 'conv-1',
    nodes: [],
    edges: [],
    lanes: [],
    workpacket_ids: [],
    approval_request_ids: [],
    decision_log: [],
    packets: [],
    created_at: '2026-07-22T00:00:00Z',
    updated_at: '2026-07-22T00:00:01Z',
    ...overrides,
  }
}

beforeEach(() => {
  fetchApiMock.mockReset()
  useObjectivePlanStore.setState({
    plans: [],
    planById: {},
    versionsByObjective: {},
    selectedPlanId: null,
    loading: false,
    detailLoading: false,
    error: null,
    decidingPlanId: null,
  })
})

describe('objectivePlanStore.decide — canonical reread is the only truth', () => {
  it('returns the CANONICAL reread plan, never the POST echo', async () => {
    // The POST echoes a DIFFERENT (stale/forged) plan than the canonical GET.
    const echoedPlan = makePlan({ status: 'awaiting_approval', graph_version: 1 })
    const canonicalPlan = makePlan({ status: 'approved', graph_version: 2 })

    fetchApiMock.mockImplementation(async (path: string, opts?: { method?: string }) => {
      if (opts?.method === 'POST') return { ok: true, plan: echoedPlan }
      if (path === `/objective-plan/${PLAN_ID}`) return canonicalPlan // fetchPlan
      if (path === '/objective-plan') return [] // fetchSurface
      throw new Error(`unexpected path ${path}`)
    })

    const res = await useObjectivePlanStore.getState().decide(PLAN_ID, 'approve', undefined, 2)

    expect(res.ok).toBe(true)
    // The returned plan is the canonical reread, NOT the echoed POST body.
    expect(res.plan?.status).toBe('approved')
    expect(res.plan?.graph_version).toBe(2)
    expect(res.plan).not.toBe(echoedPlan)
  })

  it('preserves and surfaces a canonical reread FAILURE and returns NO plan', async () => {
    // POST succeeds and echoes a plausible plan, but the canonical reread fails.
    const echoedPlan = makePlan()
    fetchApiMock.mockImplementation(async (path: string, opts?: { method?: string }) => {
      if (opts?.method === 'POST') return { ok: true, plan: echoedPlan }
      if (path === `/objective-plan/${PLAN_ID}`) {
        throw new ApiError(503, 'canonical read unavailable') // fetchPlan fails
      }
      return []
    })

    const res = await useObjectivePlanStore.getState().decide(PLAN_ID, 'approve', undefined, 2)

    // The reread failure is the outcome — echoed POST data must NOT masquerade as truth.
    expect(res.ok).toBe(false)
    expect(res.plan).toBeUndefined()
    expect(res.error).toContain('canonical read unavailable')
    // The store's surfaced error is the READ failure, not a POST status.
    expect(useObjectivePlanStore.getState().error).toContain('canonical read unavailable')
  })

  it('never overwrites the reread error with result.error', async () => {
    // POST reports its own error string; the reread ALSO fails with a different one.
    fetchApiMock.mockImplementation(async (path: string, opts?: { method?: string }) => {
      if (opts?.method === 'POST') return { ok: false, error: 'post-level-error' }
      if (path === `/objective-plan/${PLAN_ID}`) {
        throw new ApiError(500, 'reread-level-error')
      }
      return []
    })

    const res = await useObjectivePlanStore.getState().decide(PLAN_ID, 'approve', undefined, 2)

    expect(res.ok).toBe(false)
    expect(res.error).toContain('reread-level-error')
    expect(res.error).not.toContain('post-level-error')
  })

  it('classifies a 409 POST as a version conflict via ApiError.status (not string match)', async () => {
    fetchApiMock.mockImplementation(async (_path: string, opts?: { method?: string }) => {
      if (opts?.method === 'POST') throw new ApiError(409, 'stale') // no "conflict"/"version" word
      return null
    })

    const res = await useObjectivePlanStore.getState().decide(PLAN_ID, 'approve', undefined, 2)

    expect(res.ok).toBe(false)
    expect(res.conflict).toBe(true)
    expect(res.plan).toBeUndefined()
  })
})
