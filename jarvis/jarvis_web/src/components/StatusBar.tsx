import { useCockpitStore } from '../stores/cockpitStore.ts'
import { formatUptime } from '../lib/time.ts'
import { clsx } from 'clsx'

export function StatusBar() {
  const { pulse, wsConnected, models } = useCockpitStore()
  const activeModel = models.find((m) => m.status === 'active')

  return (
    <div className="flex items-center justify-between px-4 py-1 bg-surface border-t border-border text-[10px] font-mono">
      <div className="flex items-center gap-4">
        <span className="flex items-center gap-1.5">
          <span className={clsx('w-1.5 h-1.5 rounded-full', wsConnected ? 'bg-ok' : 'bg-danger')} />
          <span className="text-text-tertiary">{wsConnected ? 'CONNECTED' : 'OFFLINE'}</span>
        </span>
        <span className="text-text-tertiary">
          UP {formatUptime(pulse.uptime)}
        </span>
        <span className="text-text-tertiary">
          CPU {pulse.cpuPercent}%
        </span>
        <span className="text-text-tertiary">
          MEM {pulse.memoryPercent}%
        </span>
      </div>
      <div className="flex items-center gap-4">
        <span className="text-text-tertiary">
          {pulse.activeAgents} agents · {pulse.pendingTasks} tasks · {pulse.pendingApprovals} approvals
        </span>
        {activeModel && (
          <span className="text-cyan">
            {activeModel.name} ({activeModel.latencyMs}ms)
          </span>
        )}
      </div>
    </div>
  )
}
