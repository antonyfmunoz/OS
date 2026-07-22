/**
 * Panel identity registry — the single naming authority for Cockpit panels.
 *
 * Convergence Law (.claude/rules/convergence-law.md): one concept, one
 * operator surface. Every panel id is either CANONICAL (owns a surface) or an
 * ALIAS that resolves to a canonical id. Retired panel ids never dead-link —
 * they alias to the surface that absorbed them.
 *
 * This module is pure data + resolution. Navigation state stays owned by
 * cockpitStore; the ad-hoc `redirects` map in `setPanel` migrates to
 * `resolvePanelId` (Wave 1 C4). `chat` is a right-rail surface, not a Panel —
 * aliases targeting `chat` are handled by navigation as "open the chat rail".
 */

/** Panels that own their surface. Wave 1 additions: workdetail (Plan/Task
 * inspection, contextual from chat + kanban cards); `work` is the canonical
 * Task kanban; `approvals` is the expanded view of the SAME Top HUD
 * ControlPanel Decision surface (one component/store — never a second
 * decision implementation). */
export const CANONICAL_PANEL_IDS = [
  // primary
  'commandcenter',
  'canvas',
  'work',
  'editor',
  'rooms',
  'vision',
  // decision surface (expanded ControlPanel view)
  'approvals',
  // Wave 1 — contextual Plan/Task detail (reached from chat + kanban cards,
  // NEVER from the HUD)
  'workdetail',
  // chat rail surface (communication only — no decision controls)
  'chat',
  // established canonical panels (unchanged by Wave 1)
  'activity',
  'execution',
  'organismmap',
  'broadcast',
  'knowledge',
  'browser',
  'settings',
  'goals',
  'delegation',
  'selfbuild',
  'buildloop',
  'actions',
  'memory',
  'operations',
  'proofinspector',
  'recoverydashboard',
] as const

export type CanonicalPanelId = (typeof CANONICAL_PANEL_IDS)[number]

/**
 * Alias → canonical id. Sources: Wave 1 planning-cluster convergence
 * (intent / intentloop / objectiveplan → workdetail; tasks / universalwork →
 * work; commands → chat) plus the pre-existing ad-hoc redirects from
 * cockpitStore.setPanel, migrated here as the one alias table.
 */
export const PANEL_ALIASES: Readonly<Record<string, string>> = {
  // Wave 1 planning-cluster convergence
  intent: 'workdetail',
  intentloop: 'workdetail',
  objectiveplan: 'workdetail',
  tasks: 'work',
  universalwork: 'work',
  commands: 'chat',
  // pre-existing redirects (migrated from cockpitStore.setPanel)
  dashboard: 'commandcenter',
  runtime: 'execution',
  skills: 'knowledge',
  infrastructure: 'organismmap',
  agents: 'canvas',
  workflows: 'canvas',
}

const CANONICAL_SET: ReadonlySet<string> = new Set(CANONICAL_PANEL_IDS)

/**
 * Resolve any panel id (canonical, alias, or unknown) to its canonical id.
 * Alias chains resolve transitively; cycles are impossible to construct
 * silently (guarded), and unknown ids resolve to themselves so legacy panels
 * outside the registry keep working unchanged.
 */
export function resolvePanelId(id: string): string {
  let current = id
  const seen = new Set<string>()
  while (PANEL_ALIASES[current] !== undefined) {
    if (seen.has(current)) {
      // A cycle is a registry defect; fail open to the last stable id.
      console.error(`panel registry: alias cycle at '${current}'`)
      return current
    }
    seen.add(current)
    current = PANEL_ALIASES[current]
  }
  return current
}

export function isCanonicalPanelId(id: string): id is CanonicalPanelId {
  return CANONICAL_SET.has(id)
}

/** True when the id is a retired/alias id (it no longer owns a surface). */
export function isAliasPanelId(id: string): boolean {
  return PANEL_ALIASES[id] !== undefined
}
