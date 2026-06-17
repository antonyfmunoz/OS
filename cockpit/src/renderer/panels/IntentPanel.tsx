import { useEffect, useState } from 'react'
import { useIntentStore } from '../stores/intentStore'
import { ConnectionBanner } from '../components/ConnectionBanner'

const SCOPE_ORDER = ['empire', 'product', 'architecture', 'engineering', 'session']
const SCOPE_COLORS: Record<string, string> = {
  empire: 'bg-amber-500/20 text-amber-400',
  product: 'bg-blue-500/20 text-blue-400',
  architecture: 'bg-purple-500/20 text-purple-400',
  engineering: 'bg-green-500/20 text-green-400',
  session: 'bg-gray-500/20 text-gray-400',
}

export function IntentPanel() {
  const activeIntents = useIntentStore((s) => s.activeIntents)
  const conflicts = useIntentStore((s) => s.conflicts)
  const summary = useIntentStore((s) => s.summary)
  const loading = useIntentStore((s) => s.loading)
  const fetchActive = useIntentStore((s) => s.fetchActive)
  const fetchSummary = useIntentStore((s) => s.fetchSummary)
  const fetchConflicts = useIntentStore((s) => s.fetchConflicts)
  const [expandedScope, setExpandedScope] = useState<string | null>(null)

  useEffect(() => {
    fetchActive()
    fetchSummary()
    fetchConflicts()
  }, [fetchActive, fetchSummary, fetchConflicts])

  const byScope = SCOPE_ORDER.map((scope) => ({
    scope,
    intents: activeIntents.filter((i) => i.scope === scope),
  }))

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <ConnectionBanner />
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <h2 className="text-lg font-semibold text-foreground">Intent Runtime</h2>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <span>{activeIntents.length} active</span>
          {conflicts.length > 0 && (
            <span className="text-red-400">{conflicts.length} conflicts</span>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {loading && activeIntents.length === 0 && (
          <div className="text-muted-foreground text-sm">Loading intents...</div>
        )}

        {byScope.map(({ scope, intents }) => (
          <div key={scope} className="border border-border rounded-lg overflow-hidden">
            <button
              onClick={() => setExpandedScope(expandedScope === scope ? null : scope)}
              className="w-full flex items-center justify-between px-3 py-2 bg-surface-raised hover:bg-surface-raised/80"
            >
              <div className="flex items-center gap-2">
                <span className={`px-2 py-0.5 text-xs rounded-full ${SCOPE_COLORS[scope] ?? 'bg-gray-500/20 text-gray-400'}`}>
                  {scope.toUpperCase()}
                </span>
                <span className="text-xs text-muted-foreground">{intents.length} intent{intents.length !== 1 ? 's' : ''}</span>
              </div>
              <span className="text-xs text-muted-foreground">{expandedScope === scope ? '▲' : '▼'}</span>
            </button>
            {expandedScope === scope && (
              <div className="p-3 space-y-2">
                {intents.length === 0 ? (
                  <div className="text-xs text-muted-foreground italic">No active intents at this scope</div>
                ) : (
                  intents.map((intent) => (
                    <div key={intent.intent_id} className="p-2 rounded bg-surface border border-border/50">
                      <div className="text-sm text-foreground font-medium">{intent.statement}</div>
                      {intent.rationale && (
                        <div className="text-xs text-muted-foreground mt-1">{intent.rationale}</div>
                      )}
                      {intent.success_criteria.length > 0 && (
                        <div className="mt-2 space-y-1">
                          {intent.success_criteria.map((sc, i) => (
                            <div key={i} className="text-xs text-muted-foreground flex items-start gap-1">
                              <span className="text-green-400 mt-0.5">&bull;</span>
                              <span>{sc}</span>
                            </div>
                          ))}
                        </div>
                      )}
                      <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
                        <span>v{intent.version}</span>
                        <span>{intent.status}</span>
                        {intent.parent_id && <span>parent: {intent.parent_id.slice(0, 8)}</span>}
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        ))}

        {conflicts.length > 0 && (
          <div className="mt-4">
            <h3 className="text-sm font-semibold text-red-400 mb-2">Conflicts</h3>
            {conflicts.map((c) => (
              <div key={c.conflict_id} className="p-2 rounded bg-red-500/10 border border-red-500/20 mb-2">
                <div className="text-xs text-foreground">{c.description}</div>
                <div className="text-xs text-muted-foreground mt-1">
                  {c.conflict_type} &middot; {c.resolution || 'unresolved'}
                </div>
              </div>
            ))}
          </div>
        )}

        {summary && (
          <div className="mt-4 p-3 rounded-lg bg-surface-raised border border-border">
            <h3 className="text-sm font-semibold text-foreground mb-2">Summary</h3>
            <pre className="text-xs text-muted-foreground whitespace-pre-wrap break-all">
              {JSON.stringify(summary, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  )
}
