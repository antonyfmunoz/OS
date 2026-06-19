import { useEffect } from 'react'
import { clsx } from 'clsx'
import { useOperationsStore } from '../stores/operationsStore'
import { usePolling } from '../hooks/usePolling'

const stateColor: Record<string, string> = {
  idle: 'text-gray-400',
  active: 'text-green-400',
  saturated: 'text-yellow-400',
  blocked: 'text-red-400',
  degraded: 'text-red-500',
  optimal: 'text-green-400',
  constrained: 'text-yellow-400',
  overloaded: 'text-orange-400',
}

const stateBg: Record<string, string> = {
  idle: 'bg-gray-500/10',
  active: 'bg-green-500/10',
  saturated: 'bg-yellow-500/10',
  blocked: 'bg-red-500/10',
  degraded: 'bg-red-500/10',
  optimal: 'bg-green-500/10',
  constrained: 'bg-yellow-500/10',
  overloaded: 'bg-orange-500/10',
}

function StateBadge({ label, state }: { label: string; state: string }) {
  return (
    <div className={clsx('inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs font-mono', stateBg[state], stateColor[state])}>
      <span className={clsx('w-1.5 h-1.5 rounded-full', stateColor[state]?.replace('text-', 'bg-'))} />
      {label}: {state.toUpperCase()}
    </div>
  )
}

function MetricCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="wv-card p-3">
      <div className="text-xs text-gray-400">{label}</div>
      <div className="text-lg font-bold text-gray-100">{value}</div>
      {sub && <div className="text-xs text-gray-500 mt-0.5">{sub}</div>}
    </div>
  )
}

function FabricSection() {
  const fabric = useOperationsStore((s) => s.fabric)
  if (!fabric) return <div className="wv-card p-4 text-gray-400">Execution fabric unavailable</div>

  const nodes = (fabric.compute_nodes as Record<string, unknown>[]) || []
  const cap = fabric as Record<string, unknown>

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <h3 className="text-sm font-semibold text-gray-200">Execution Fabric</h3>
        <StateBadge label="Fabric" state={String(fabric.fabric_state || 'idle')} />
        <StateBadge label="Execution" state={String(fabric.execution_state || 'idle')} />
      </div>
      <div className="grid grid-cols-5 gap-3">
        <MetricCard label="Active Plans" value={((fabric.active_plans as unknown[]) || []).length} />
        <MetricCard label="Queue Depth" value={Number(cap.queue_depth || 0)} />
        <MetricCard label="Awaiting Approval" value={Number(cap.awaiting_approval_count || 0)} />
        <MetricCard label="Compute Nodes" value={nodes.length} />
        <MetricCard label="Online Devices" value={((fabric.online_devices as unknown[]) || []).length} />
      </div>
      {nodes.length > 0 && (
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400 mb-2">Compute Nodes</div>
          <div className="space-y-1">
            {nodes.map((n, i) => (
              <div key={i} className="flex items-center gap-3 text-xs font-mono">
                <span className={clsx('w-1.5 h-1.5 rounded-full', n.health === 'healthy' ? 'bg-green-400' : n.health === 'degraded' ? 'bg-yellow-400' : 'bg-red-400')} />
                <span className="text-gray-300 w-24 truncate">{String(n.display_name || n.node_id)}</span>
                <span className="text-gray-500">{String(n.node_type)}</span>
                <span className="text-gray-400">{String(n.active_workers)}/{String(n.max_workers)} workers</span>
                <span className={stateColor[String(n.health)] || 'text-gray-400'}>{String(n.health)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function ActiveExecutionsSection() {
  const fabric = useOperationsStore((s) => s.fabric)
  const plans = ((fabric?.active_plans as Record<string, unknown>[]) || [])
  if (!plans.length) return null

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold text-gray-200">Active Executions</h3>
      <div className="wv-card overflow-hidden">
        <table className="w-full text-xs font-mono">
          <thead>
            <tr className="text-gray-400 border-b border-gray-700">
              <th className="text-left p-2">Plan</th>
              <th className="text-left p-2">Target</th>
              <th className="text-left p-2">Status</th>
              <th className="text-left p-2">Session</th>
            </tr>
          </thead>
          <tbody>
            {plans.map((p, i) => (
              <tr key={i} className="border-b border-gray-800 hover:bg-gray-800/30">
                <td className="p-2 text-gray-300">{String(p.plan_id || p.description || `plan-${i}`)}</td>
                <td className="p-2 text-gray-400">{String(p.target_type || p.executor_type || '—')}</td>
                <td className="p-2">
                  <span className={stateColor[String(p.status)] || 'text-gray-400'}>{String(p.status)}</span>
                </td>
                <td className="p-2 text-gray-500">{String(p.session_id || '—')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function WorkforceSection() {
  const workforce = useOperationsStore((s) => s.workforce)
  if (!workforce) return <div className="wv-card p-4 text-gray-400">Agent workforce unavailable</div>

  const idle = (workforce.idle_agents as Record<string, unknown>[]) || []
  const overloaded = (workforce.overloaded_agents as Record<string, unknown>[]) || []
  const pending = (workforce.pending_delegations as Record<string, unknown>[]) || []

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <h3 className="text-sm font-semibold text-gray-200">Agent Workforce</h3>
        <StateBadge label="Health" state={String(workforce.health || 'idle')} />
      </div>
      <div className="grid grid-cols-5 gap-3">
        <MetricCard label="Agent Types" value={Number(workforce.total_agent_types || 0)} />
        <MetricCard label="Available" value={Number(workforce.available_executor_count || 0)} />
        <MetricCard label="Active Dispatches" value={((workforce.active_dispatches as unknown[]) || []).length} />
        <MetricCard label="Delegation Rate" value={`${(Number(workforce.delegation_success_rate || 0) * 100).toFixed(0)}%`} />
        <MetricCard label="Queue" value={Number(workforce.queue_depth || 0)} />
      </div>
      <div className="grid grid-cols-3 gap-3">
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400 mb-1">Idle ({idle.length})</div>
          {idle.length === 0 ? <div className="text-xs text-gray-500">None</div> : (
            <div className="space-y-0.5">
              {idle.map((a, i) => (
                <div key={i} className="text-xs text-green-400 font-mono">{String(a.label || a.agent_type_id)}</div>
              ))}
            </div>
          )}
        </div>
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400 mb-1">Overloaded ({overloaded.length})</div>
          {overloaded.length === 0 ? <div className="text-xs text-gray-500">None</div> : (
            <div className="space-y-0.5">
              {overloaded.map((a, i) => (
                <div key={i} className="text-xs text-orange-400 font-mono">{String(a.label || a.agent_type_id)} ×{String(a.active_count)}</div>
              ))}
            </div>
          )}
        </div>
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400 mb-1">Pending Delegations ({pending.length})</div>
          {pending.length === 0 ? <div className="text-xs text-gray-500">None</div> : (
            <div className="space-y-0.5">
              {pending.slice(0, 5).map((d, i) => (
                <div key={i} className="text-xs text-yellow-400 font-mono truncate">{String(d.work_id || d.description || `delegation-${i}`)}</div>
              ))}
              {pending.length > 5 && <div className="text-xs text-gray-500">+{pending.length - 5} more</div>}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function QueueSection() {
  const fabric = useOperationsStore((s) => s.fabric)
  const blocked = ((fabric?.blocked_work as Record<string, unknown>[]) || [])
  if (!blocked.length && !Number(fabric?.queue_depth || 0) && !Number(fabric?.awaiting_approval_count || 0)) return null

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold text-gray-200">Blocked Work</h3>
      {blocked.length === 0 ? (
        <div className="wv-card p-3 text-xs text-gray-500">No blocked work</div>
      ) : (
        <div className="wv-card p-3 space-y-1">
          {blocked.map((b, i) => (
            <div key={i} className="flex items-center gap-2 text-xs font-mono">
              <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
              <span className="text-gray-300">{String(b.work_id || b.id || `blocked-${i}`)}</span>
              <span className="text-gray-500">{String(b.blocker_type || b.reason || '—')}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function SessionsSection() {
  const sm = useOperationsStore((s) => s.sessionMachine)
  if (!sm) return <div className="wv-card p-4 text-gray-400">Session machine unavailable</div>

  const bindings = (sm.bindings as Record<string, unknown>[]) || []

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <h3 className="text-sm font-semibold text-gray-200">Sessions & Machines</h3>
        <span className="text-xs text-gray-400 font-mono">
          {sm.online_devices}/{sm.total_devices} online · {sm.active_sessions}/{sm.total_sessions} active
        </span>
      </div>
      {bindings.length === 0 ? (
        <div className="wv-card p-3 text-xs text-gray-500">No device bindings</div>
      ) : (
        <div className="space-y-2">
          {bindings.map((b, i) => {
            const sessions = (b.sessions as Record<string, unknown>[]) || []
            return (
              <div key={i} className="wv-card p-3">
                <div className="flex items-center gap-2 mb-1">
                  <span className={clsx('w-1.5 h-1.5 rounded-full', b.online ? 'bg-green-400' : 'bg-gray-500')} />
                  <span className="text-xs font-semibold text-gray-200">{String(b.device_display_name || b.device_id)}</span>
                  <span className="text-xs text-gray-500">{String(b.device_type)}</span>
                  <span className="text-xs text-gray-400 ml-auto">{String(b.active_sessions)}/{String(b.total_sessions)} sessions</span>
                </div>
                {sessions.length > 0 && (
                  <div className="pl-4 space-y-0.5">
                    {sessions.map((s, j) => (
                      <div key={j} className="flex items-center gap-2 text-xs font-mono">
                        <span className={clsx(s.authority === 'primary' || s.authority === 'PRIMARY' ? 'text-cyan-400' : 'text-gray-400')}>
                          {s.authority === 'primary' || s.authority === 'PRIMARY' ? '★' : '·'}
                        </span>
                        <span className="text-gray-300">{String(s.session_type || s.type || 'session')}</span>
                        <span className={clsx(s.status === 'active' ? 'text-green-400' : 'text-gray-500')}>{String(s.status)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

function WorkspacesSection() {
  const sm = useOperationsStore((s) => s.sessionMachine)
  const workspaces = ((sm?.active_workspaces as Record<string, unknown>[]) || [])
  if (!workspaces.length) return null

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold text-gray-200">Active Workspaces</h3>
      <div className="wv-card p-3 space-y-1">
        {workspaces.map((w, i) => (
          <div key={i} className="flex items-center gap-3 text-xs font-mono">
            <span className="text-gray-400">{String(w.device || '—')}</span>
            <span className="text-cyan-400">{String(w.repo || w.directory || '—')}</span>
            {w.branch && <span className="text-green-400">{String(w.branch)}</span>}
          </div>
        ))}
      </div>
    </div>
  )
}

export function OperationsPanel() {
  const fetchAll = useOperationsStore((s) => s.fetchAll)

  useEffect(() => { fetchAll() }, [])
  usePolling(fetchAll, 10000, true, 2000)

  return (
    <div className="h-full overflow-y-auto p-4 space-y-6">
      <div className="flex items-center gap-3 mb-2">
        <h2 className="text-base font-bold text-gray-100">Operations</h2>
        <span className="text-xs text-gray-500 font-mono">Live execution operations</span>
      </div>
      <FabricSection />
      <ActiveExecutionsSection />
      <WorkforceSection />
      <QueueSection />
      <SessionsSection />
      <WorkspacesSection />
    </div>
  )
}
