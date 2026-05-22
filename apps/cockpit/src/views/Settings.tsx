import { useCockpitStore } from '../stores/cockpitStore.ts'
import { clsx } from 'clsx'

function RoutingTable({ routing }: { routing: { provider: string; priority: number; enabled: boolean }[] }) {
  return (
    <div className="wv-card overflow-hidden">
      <div className="px-3 py-2 border-b border-border"><span className="wv-label">MODEL ROUTING</span></div>
      <div className="divide-y divide-border/50">
        <div className="flex items-center gap-3 px-3 py-2 text-[10px] font-mono text-text-tertiary uppercase tracking-wider">
          <span className="w-6">#</span><span className="flex-1">PROVIDER</span><span className="w-16 text-right">STATUS</span>
        </div>
        {routing.map((r) => (
          <div key={r.provider} className="flex items-center gap-3 px-3 py-2 text-[11px] font-mono">
            <span className="text-text-tertiary w-6">{r.priority}</span>
            <span className="text-text-primary flex-1">{r.provider}</span>
            <span className={clsx('w-16 text-right', r.enabled ? 'text-ok' : 'text-text-tertiary')}>{r.enabled ? 'ON' : 'OFF'}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function GovernancePanel({ governance }: { governance: { auto_approve_low: boolean; critical_block: boolean } }) {
  return (
    <div className="wv-card p-4">
      <div className="wv-label mb-3">GOVERNANCE POLICIES</div>
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-[11px] text-text-secondary">Auto-approve low risk</span>
          <span className={clsx('wv-badge', governance.auto_approve_low ? 'wv-badge-ok' : 'wv-badge-danger')}>{governance.auto_approve_low ? 'enabled' : 'disabled'}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-[11px] text-text-secondary">Block critical actions</span>
          <span className={clsx('wv-badge', governance.critical_block ? 'wv-badge-ok' : 'wv-badge-danger')}>{governance.critical_block ? 'enabled' : 'disabled'}</span>
        </div>
      </div>
    </div>
  )
}

function NotificationsPanel({ notifications }: { notifications: { discord: boolean; file: boolean } }) {
  return (
    <div className="wv-card p-4">
      <div className="wv-label mb-3">NOTIFICATIONS</div>
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-[11px] text-text-secondary">Discord alerts</span>
          <span className={clsx('wv-badge', notifications.discord ? 'wv-badge-ok' : 'wv-badge-danger')}>{notifications.discord ? 'on' : 'off'}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-[11px] text-text-secondary">File logging</span>
          <span className={clsx('wv-badge', notifications.file ? 'wv-badge-ok' : 'wv-badge-danger')}>{notifications.file ? 'on' : 'off'}</span>
        </div>
      </div>
    </div>
  )
}

export function Settings() {
  const { settings } = useCockpitStore()

  if (!settings) {
    return (
      <div className="h-full flex flex-col p-4">
        <h1 className="text-[14px] font-mono uppercase tracking-widest text-text-secondary mb-4">Settings</h1>
        <div className="flex-1 flex items-center justify-center text-text-tertiary text-[11px]">Loading settings...</div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col p-4 overflow-hidden">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-[14px] font-mono uppercase tracking-widest text-text-secondary">Settings</h1>
      </div>
      <div className="flex-1 overflow-y-auto space-y-4">
        <RoutingTable routing={settings.model_routing} />
        <div className="grid grid-cols-2 gap-4">
          <GovernancePanel governance={settings.governance} />
          <NotificationsPanel notifications={settings.notifications} />
        </div>
      </div>
    </div>
  )
}
