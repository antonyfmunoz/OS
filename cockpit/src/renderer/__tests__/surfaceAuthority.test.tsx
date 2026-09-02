/**
 * Wave 1 test O — UI-level surface-authority verification.
 *
 * Asserts the owner-ruled surface contract at the component/source level:
 *  1. Chat plan cards are link-only: PlanSummaryCard renders NO decision
 *     controls (no approve/reject), only status + Open Plan.
 *  2. Decisions are HUD-only: the wg-approve-btn / wg-reject-btn testids
 *     exist ONLY in the Top HUD ControlPanel source, never in the chat card
 *     or the Work Detail panel (which allows cancel only).
 *  3. Retired panel ids resolve through the registry to canonical surfaces
 *     (aliases never dead-link, no rival panel remains reachable by id).
 *  4. The `approvals` id remains a canonical id (the expanded view of the
 *     SAME ControlPanel decision surface — never a second implementation).
 */
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import {
  CANONICAL_PANEL_IDS,
  PANEL_ALIASES,
  isAliasPanelId,
  isCanonicalPanelId,
  resolvePanelId,
} from '../panels/registry'

const src = (rel: string): string =>
  readFileSync(resolve(__dirname, '..', rel), 'utf-8')

describe('test O — chat surface is communication only', () => {
  it('PlanSummaryCard has no decision controls', () => {
    const card = src('components/cards/PlanSummaryCard.tsx')
    expect(card).not.toMatch(/wg-approve-btn|wg-reject-btn/)
    expect(card).not.toMatch(/onClick=\{[^}]*(approve|reject)/i)
    expect(card).toMatch(/wg-open-plan-btn/)
    expect(card).toMatch(/wg-plan-root/)
  })

  it('WorkDetailPanel allows cancel only — no accept/reject authority', () => {
    const panel = src('panels/WorkDetailPanel.tsx')
    expect(panel).not.toMatch(/wg-approve-btn|wg-reject-btn/)
    expect(panel).toMatch(/wg-cancel-btn/)
  })
})

describe('test O — decisions live ONLY in the Top HUD ControlPanel', () => {
  it('ControlPanel owns the decision testids', () => {
    const hud = src('components/ControlPanel.tsx')
    expect(hud).toMatch(/wg-approval-row/)
    expect(hud).toMatch(/wg-approve-btn/)
    expect(hud).toMatch(/wg-reject-btn/)
  })

  it('no other wave-1 surface declares the decision testids', () => {
    for (const rel of [
      'components/cards/PlanSummaryCard.tsx',
      'panels/WorkDetailPanel.tsx',
      'panels/UniversalWorkPanel.tsx',
      'components/RightRail.tsx',
      // Wave 2: the execution chat card + attempts view carry NO decision
      // testids — execution decisions stay HUD-only.
      'components/cards/ChatExecutionCard.tsx',
      'components/execution/AttemptsView.tsx',
    ]) {
      expect(src(rel), rel).not.toMatch(/wg-approve-btn|wg-reject-btn/)
    }
  })
})

describe('test O — retired ids resolve, no rival surface reachable', () => {
  it('planning-cluster aliases resolve to canonical surfaces', () => {
    expect(resolvePanelId('intent')).toBe('workdetail')
    expect(resolvePanelId('intentloop')).toBe('workdetail')
    expect(resolvePanelId('objectiveplan')).toBe('workdetail')
    expect(resolvePanelId('tasks')).toBe('work')
    expect(resolvePanelId('universalwork')).toBe('work')
    expect(resolvePanelId('commands')).toBe('chat')
  })

  it('every alias target is canonical (never a dead link)', () => {
    for (const [alias, target] of Object.entries(PANEL_ALIASES)) {
      const resolved = resolvePanelId(alias)
      expect(isCanonicalPanelId(resolved), `${alias} → ${target}`).toBe(true)
    }
  })

  it('retired panel components are non-executable redirect stubs', () => {
    for (const rel of [
      'panels/IntentPanel.tsx',
      'panels/IntentLoopPanel.tsx',
      'panels/CommandsPanel.tsx',
      'panels/TasksPanel.tsx',
      // Wave 2 execution-cluster convergence — the retired execution panels are
      // non-executable redirect stubs into the one canonical Execution surface.
      'panels/UnifiedExecutionPanel.tsx',
      'panels/ExecutorPanel.tsx',
      'panels/RuntimePanel.tsx',
      'panels/DistributedRuntimePanel.tsx',
    ]) {
      const stub = src(rel)
      expect(stub, rel).toMatch(/resolvePanelId/)
      // No data fetching, no mutation, no decision controls in a stub.
      expect(stub, rel).not.toMatch(/fetchApi|approve|reject|POST/i)
    }
  })

  it('execution-cluster aliases resolve to the canonical Execution surface', () => {
    expect(resolvePanelId('unifiedexecution')).toBe('execution')
    expect(resolvePanelId('executor')).toBe('execution')
    expect(resolvePanelId('distributedruntime')).toBe('execution')
    expect(resolvePanelId('runtime')).toBe('execution')
    expect(resolvePanelId('execcoord')).toBe('execution')
    expect(resolvePanelId('agentfleet')).toBe('execution')
    expect(CANONICAL_PANEL_IDS).toContain('execution')
  })

  it('approvals stays canonical — the expanded HUD view, not an alias to a rival', () => {
    expect(isCanonicalPanelId('approvals')).toBe(true)
    expect(isAliasPanelId('approvals')).toBe(false)
    expect(CANONICAL_PANEL_IDS).toContain('workdetail')
  })
})
