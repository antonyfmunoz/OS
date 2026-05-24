import { useSystemStore } from '../stores/systemStore'
import { usePolling } from '../hooks/usePolling'
import { RingGauge } from '../components/RingGauge'
import { useCockpitStore } from '../stores/cockpitStore'

export function DashboardPanel() {
  const pulse = useSystemStore((s) => s.pulse)
  const meshNodes = useSystemStore((s) => s.meshNodes)
  const fetchPulse = useSystemStore((s) => s.fetchPulse)
  const fetchMeshNodes = useSystemStore((s) => s.fetchMeshNodes)
  const setApiStatus = useCockpitStore((s) => s.setApiStatus)

  usePolling(async () => {
    try {
      await fetchPulse()
      setApiStatus('connected')
    } catch {
      setApiStatus('disconnected')
    }
  }, 3000)

  usePolling(fetchMeshNodes, 10000)

  return (
    <div className="flex flex-col h-full overflow-y-auto p-4">
      {/* Panel header */}
      <div className="flex items-center mb-4">
        <h2 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>
          Command Center
        </h2>
        <span className="ml-2 text-xs" style={{ color: 'var(--text-tertiary)' }}>
          system intelligence overview
        </span>
      </div>

      {/* System vitals */}
      <section className="mb-6">
        <h3 className="hud-text mb-3">System Vitals</h3>
        <div className="flex gap-6 flex-wrap">
          <RingGauge
            value={pulse?.cpu_percent ?? 0}
            max={100}
            label="CPU"
            unit="%"
            color={
              (pulse?.cpu_percent ?? 0) > 80
                ? 'var(--accent-red)'
                : (pulse?.cpu_percent ?? 0) > 50
                  ? 'var(--accent-amber)'
                  : 'var(--accent-cyan)'
            }
          />
          <RingGauge
            value={pulse?.memory_used_gb ?? 0}
            max={pulse?.memory_total_gb ?? 8}
            label="RAM"
            unit="G"
            color="var(--accent-cyan)"
          />
          <RingGauge
            value={pulse?.disk_used_gb ?? 0}
            max={pulse?.disk_total_gb ?? 100}
            label="DISK"
            unit="G"
            color="var(--accent-green)"
          />
          <RingGauge
            value={pulse?.active_agents ?? 0}
            max={10}
            label="AGENTS"
            color="var(--accent-purple)"
          />
          <RingGauge
            value={pulse?.pending_tasks ?? 0}
            max={20}
            label="PENDING"
            color="var(--accent-amber)"
          />
        </div>
      </section>

      {/* Mesh nodes */}
      <section className="mb-6">
        <h3 className="hud-text mb-3">Mesh Topology</h3>
        {meshNodes.length === 0 ? (
          <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>No mesh nodes connected</p>
        ) : (
          <div className="grid grid-cols-2 gap-2">
            {meshNodes.map((node) => (
              <div
                key={node.node_id}
                className="flex items-center gap-2 px-3 py-2 rounded"
                style={{ background: 'var(--surface-2)', border: '1px solid var(--border)' }}
              >
                <span
                  className="w-2 h-2 rounded-full"
                  style={{
                    background: node.status === 'online' ? 'var(--accent-green)' : 'var(--accent-red)',
                  }}
                />
                <div className="flex-1 min-w-0">
                  <p className="text-sm truncate" style={{ color: 'var(--text-primary)' }}>
                    {node.hostname}
                  </p>
                  <p className="hud-text">{node.role}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Uptime */}
      {pulse && (
        <section>
          <h3 className="hud-text mb-2">Runtime</h3>
          <p className="font-mono text-sm" style={{ color: 'var(--accent-cyan)' }}>
            {formatUptime(pulse.uptime_seconds)}
          </p>
        </section>
      )}
    </div>
  )
}

function formatUptime(seconds: number): string {
  const d = Math.floor(seconds / 86400)
  const h = Math.floor((seconds % 86400) / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const parts: string[] = []
  if (d > 0) parts.push(`${d}d`)
  if (h > 0) parts.push(`${h}h`)
  parts.push(`${m}m`)
  return parts.join(' ')
}
