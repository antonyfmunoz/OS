/**
 * Wave 2 — execution surface-authority verification (source-level).
 *
 * Asserts the C6 convergence contract:
 *  1. Chat execution card is STATUS-ONLY: no approve/reject/authorize controls.
 *  2. Execution DECISIONS are HUD-only: w2-execution-decision + w2-exec-*-btn
 *     testids exist ONLY in ControlPanel.
 *  3. All 10 required w2-* execution testids are present at their surfaces.
 *  4. Execution-cluster aliases resolve to the one canonical Execution surface.
 *  5. The execution store never persists to localStorage/sessionStorage
 *     (persistence-by-refetch against the backend attempt ledger).
 */
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { resolvePanelId, isCanonicalPanelId } from '../panels/registry'

const src = (rel: string): string => readFileSync(resolve(__dirname, '..', rel), 'utf-8')

describe('wave2 — chat execution card is status-only', () => {
  it('ChatExecutionCard has no decision controls', () => {
    const card = src('components/cards/ChatExecutionCard.tsx')
    // No decision testids, and no approve/reject/authorize CLICK HANDLERS (the
    // status label "AUTHORIZED" is fine — a decision handler is not).
    expect(card).not.toMatch(/wg-approve-btn|wg-reject-btn|w2-exec-approve-btn|w2-exec-reject-btn/)
    expect(card).not.toMatch(/onClick=\{[^}]*(approve|reject|authorize)/i)
    expect(card).not.toMatch(/data-testid="[^"]*(approve|reject|authorize)/i)
    expect(card).toMatch(/w2-open-execution-btn/)
    expect(card).toMatch(/w2-exec-card-root/)
  })
})

describe('wave2 — execution decisions live ONLY in the Top HUD', () => {
  it('ControlPanel owns the execution decision testids', () => {
    const hud = src('components/ControlPanel.tsx')
    expect(hud).toMatch(/w2-execution-decision/)
    expect(hud).toMatch(/w2-exec-approve-btn/)
    expect(hud).toMatch(/w2-exec-reject-btn/)
  })

  it('no other surface declares the execution decision testids', () => {
    for (const rel of [
      'components/cards/ChatExecutionCard.tsx',
      'components/execution/AttemptsView.tsx',
      'panels/ExecutionPanel.tsx',
      'panels/WorkPanel.tsx',
      'panels/WorkDetailPanel.tsx',
    ]) {
      expect(src(rel), rel).not.toMatch(/w2-execution-decision|w2-exec-approve-btn|w2-exec-reject-btn/)
    }
  })
})

describe('wave2 — all required execution testids exist', () => {
  it('the 10 w2-* execution testids are present at their surfaces', () => {
    const panel = src('panels/ExecutionPanel.tsx')
    const attempts = src('components/execution/AttemptsView.tsx')
    const hud = src('components/ControlPanel.tsx')
    const collective = panel + attempts + hud
    for (const testid of [
      'w2-execution-root',
      'w2-execution-attempt',
      'w2-assignment',
      'w2-environment-lease',
      'w2-worker-status',
      'w2-verification-status',
      'w2-proof-link',
      'w2-execution-decision',
      'w2-execution-cancel',
      'w2-execution-retry',
    ]) {
      expect(collective, testid).toContain(testid)
    }
  })
})

describe('wave2 — alias convergence + persistence-by-refetch', () => {
  it('execution-cluster aliases resolve to canonical execution', () => {
    for (const alias of ['unifiedexecution', 'executor', 'distributedruntime', 'runtime', 'execcoord', 'agentfleet']) {
      expect(resolvePanelId(alias), alias).toBe('execution')
      expect(isCanonicalPanelId(resolvePanelId(alias))).toBe(true)
    }
  })

  it('executionAttemptStore never persists execution state to browser storage', () => {
    const store = src('stores/executionAttemptStore.ts')
    expect(store).not.toMatch(/localStorage|sessionStorage/)
    // Mutations reread canonical truth (POST echo is never trusted).
    expect(store).toMatch(/fetchAttempt|fetchAttempts/)
  })
})
