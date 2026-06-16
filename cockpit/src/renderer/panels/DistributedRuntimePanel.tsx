import { useState, useEffect, useCallback } from 'react'
import { fetchApi } from '../api/client'
import { usePolling } from '../hooks/usePolling'

type Tab = 'topology' | 'devices' | 'workers' | 'capacity' | 'assignments'

interface DeviceSummary {
  device_id: string
  device_name: string
  role: string
  os: string
  online: boolean
  capabilities: string[]
  capacity: { max_workers: number; active_workers: number; utilization: number; accepting_work: boolean; headroom: number }
  worker_count: number
  workers: Worker[]
}

interface Worker {
  worker_id: string
  device_id: string
  runtime_id: string
  capabilities: string[]
  status: string
  current_task_id: string
  started_at: number
  last_heartbeat: number
}

interface Placement {
  packet_id: string
  required_capability: string
  matched_worker_id: string
  device_id: string
  workspace_path: string
  runtime_id: string
  routing_chain: string[]
  reason: string
  requires_remote_dispatch: boolean
  created_at: number
}

interface CapMatrix {
  capabilities: string[]
  devices: string[]
  matrix: Record<string, Record<string, boolean>>
}

interface RuntimeData {
  devices: DeviceSummary[]
  workers: { workers: Record<string, Worker>; active_count: number }
  capacity: { devices: { device_id: string; max_workers: number; active_workers: number; utilization: number; accepting_work: boolean; headroom: number }[]; total_headroom: number; saturated_count: number }
  topology: { capabilities: Record<string, { worker_id: string; device_id: string; status: string; device_name: string }[]>; total_capabilities: number; total_workers: number }
}

const STATUS_COLORS: Record<string, string> = {
  idle: 'bg-ok',
  working: 'bg-warn',
  spawning: 'bg-info',
  stopping: 'bg-text-tertiary',
  failed: 'bg-danger',
  terminated: 'bg-text-tertiary',
}

function StatusDot({ status }: { status: string }) {
  const color = STATUS_COLORS[status] || 'bg-text-tertiary'
  return <span className={`inline-block w-2 h-2 rounded-full shrink-0 ${color}`} title={status} />
}

function UtilBar({ value, max }: { value: number; max: number }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0
  const color = pct > 80 ? 'bg-danger' : pct > 50 ? 'bg-warn' : 'bg-ok'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-surface rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-text-secondary w-8 text-right">{pct}%</span>
    </div>
  )
}

function TopologyTab({ topology }: { topology: RuntimeData['topology'] | null }) {
  if (!topology) return <div className="p-4 text-text-secondary">Loading...</div>
  const caps = Object.entries(topology.capabilities || {}).sort(([a], [b]) => a.localeCompare(b))
  return (
    <div className="p-4 space-y-3">
      <div className="flex gap-4 text-xs text-text-secondary mb-2">
        <span>{topology.total_capabilities} capabilities</span>
        <span>{topology.total_workers} active workers</span>
      </div>
      {caps.map(([cap, workers]) => (
        <div key={cap} className="border border-border rounded p-3">
          <div className="text-sm font-medium text-text-primary mb-2">{cap}</div>
          {workers.length === 0 ? (
            <div className="text-xs text-text-tertiary">No active workers</div>
          ) : (
            <div className="space-y-1">
              {workers.map((w) => (
                <div key={w.worker_id} className="flex items-center gap-2 text-xs">
                  <StatusDot status={w.status} />
                  <span className="text-text-secondary font-mono">{w.worker_id}</span>
                  <span className="text-text-tertiary">on</span>
                  <span className="text-text-primary">{w.device_name}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

function DevicesTab({ devices }: { devices: DeviceSummary[] }) {
  return (
    <div className="p-4 grid gap-3">
      {devices.map((d) => (
        <div key={d.device_id} className="border border-border rounded p-3">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${d.online ? 'bg-ok' : 'bg-text-tertiary'}`} />
              <span className="text-sm font-medium text-text-primary">{d.device_name}</span>
              <span className="text-xs text-text-secondary">({d.role})</span>
            </div>
            <span className="text-xs text-text-tertiary">{d.os}</span>
          </div>
          <UtilBar value={d.capacity.active_workers} max={d.capacity.max_workers} />
          <div className="flex flex-wrap gap-1 mt-2">
            {d.capabilities.map((c) => (
              <span key={c} className="px-1.5 py-0.5 text-xs bg-surface rounded">{c}</span>
            ))}
          </div>
          <div className="text-xs text-text-secondary mt-1">{d.worker_count} workers</div>
        </div>
      ))}
    </div>
  )
}

function WorkersTab({ workers }: { workers: Worker[] }) {
  return (
    <div className="p-4 overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="text-text-secondary border-b border-border">
            <th className="text-left py-1 px-2">Worker</th>
            <th className="text-left py-1 px-2">Device</th>
            <th className="text-left py-1 px-2">Capabilities</th>
            <th className="text-left py-1 px-2">Status</th>
            <th className="text-left py-1 px-2">Task</th>
            <th className="text-left py-1 px-2">Heartbeat</th>
          </tr>
        </thead>
        <tbody>
          {workers.map((w) => (
            <tr key={w.worker_id} className="border-b border-border/50">
              <td className="py-1.5 px-2 font-mono">{w.worker_id}</td>
              <td className="py-1.5 px-2">{w.device_id}</td>
              <td className="py-1.5 px-2">{w.capabilities.join(', ')}</td>
              <td className="py-1.5 px-2"><StatusDot status={w.status} /> {w.status}</td>
              <td className="py-1.5 px-2 font-mono text-text-tertiary">{w.current_task_id || '—'}</td>
              <td className="py-1.5 px-2 text-text-tertiary">{w.last_heartbeat ? `${Math.round((Date.now() / 1000 - w.last_heartbeat))}s ago` : '—'}</td>
            </tr>
          ))}
          {workers.length === 0 && (
            <tr><td colSpan={6} className="py-4 text-center text-text-tertiary">No active workers</td></tr>
          )}
        </tbody>
      </table>
    </div>
  )
}

function CapacityTab({ capacity }: { capacity: RuntimeData['capacity'] | null }) {
  if (!capacity) return <div className="p-4 text-text-secondary">Loading...</div>
  return (
    <div className="p-4 space-y-3">
      <div className="flex gap-4 text-xs text-text-secondary mb-2">
        <span>Total headroom: {capacity.total_headroom}</span>
        <span>Saturated: {capacity.saturated_count}</span>
      </div>
      {capacity.devices.map((d) => (
        <div key={d.device_id} className="border border-border rounded p-3">
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm text-text-primary">{d.device_id}</span>
            <span className={`text-xs px-1.5 py-0.5 rounded ${d.accepting_work ? 'bg-ok/20 text-ok' : 'bg-danger/20 text-danger'}`}>
              {d.accepting_work ? 'Accepting' : 'Saturated'}
            </span>
          </div>
          <UtilBar value={d.active_workers} max={d.max_workers} />
          <div className="text-xs text-text-tertiary mt-1">{d.active_workers}/{d.max_workers} workers · {d.headroom} headroom</div>
        </div>
      ))}
    </div>
  )
}

function AssignmentsTab({ assignments }: { assignments: Placement[] }) {
  return (
    <div className="p-4 space-y-2">
      {assignments.map((p, i) => (
        <div key={`${p.packet_id}-${i}`} className="border border-border rounded p-3 text-xs">
          <div className="flex items-center justify-between mb-1">
            <span className="font-mono text-text-primary">{p.packet_id || '(no id)'}</span>
            {p.requires_remote_dispatch && <span className="px-1.5 py-0.5 bg-warn/20 text-warn rounded">Remote</span>}
          </div>
          <div className="flex flex-wrap gap-1 mb-1">
            {p.routing_chain.map((step, j) => (
              <span key={j} className="px-1.5 py-0.5 bg-surface rounded">{step}</span>
            ))}
          </div>
          <div className="text-text-secondary">{p.reason}</div>
          <div className="text-text-tertiary mt-1">
            {p.workspace_path && <span>Workspace: {p.workspace_path}</span>}
          </div>
        </div>
      ))}
      {assignments.length === 0 && <div className="text-text-tertiary text-sm">No recent assignments</div>}
    </div>
  )
}

export function DistributedRuntimePanel() {
  const [tab, setTab] = useState<Tab>('topology')
  const [data, setData] = useState<RuntimeData | null>(null)
  const [assignments, setAssignments] = useState<Placement[]>([])
  const [allWorkers, setAllWorkers] = useState<Worker[]>([])

  const fetchData = useCallback(async () => {
    try {
      const d = await fetchApi<RuntimeData>('/organism/distributed-runtime')
      setData(d)
      if (d?.workers?.workers) {
        setAllWorkers(Object.values(d.workers.workers))
      }
    } catch {
      /* ignore */
    }
  }, [])

  const fetchAssignments = useCallback(async () => {
    try {
      const d = await fetchApi<{ assignments: Placement[] }>('/organism/distributed-runtime/assignments')
      setAssignments(d?.assignments || [])
    } catch {
      /* ignore */
    }
  }, [])

  usePolling(fetchData, 10_000)
  usePolling(fetchAssignments, 10_000)

  useEffect(() => {
    fetchData()
    fetchAssignments()
  }, [fetchData, fetchAssignments])

  const TABS: { key: Tab; label: string }[] = [
    { key: 'topology', label: 'Topology' },
    { key: 'devices', label: 'Devices' },
    { key: 'workers', label: 'Workers' },
    { key: 'capacity', label: 'Capacity' },
    { key: 'assignments', label: 'Assignments' },
  ]

  return (
    <div className="flex flex-col h-full">
      <div className="flex border-b border-border px-3">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
              tab === t.key
                ? 'border-accent text-accent'
                : 'border-transparent text-text-secondary hover:text-text-primary'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-y-auto">
        {tab === 'topology' && <TopologyTab topology={data?.topology || null} />}
        {tab === 'devices' && <DevicesTab devices={data?.devices || []} />}
        {tab === 'workers' && <WorkersTab workers={allWorkers} />}
        {tab === 'capacity' && <CapacityTab capacity={data?.capacity || null} />}
        {tab === 'assignments' && <AssignmentsTab assignments={assignments} />}
      </div>
    </div>
  )
}
