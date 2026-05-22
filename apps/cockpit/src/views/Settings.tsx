import { useState } from 'react'
import { useCockpitStore } from '../stores/cockpitStore.ts'
import { api, type SettingsResponse } from '../api/client.ts'
import { clsx } from 'clsx'

function Toggle({ enabled, onToggle, label }: { enabled: boolean; onToggle: () => void; label: string }) {
  return (
    <button onClick={onToggle} className="flex items-center justify-between w-full group">
      <span className="text-[11px] text-text-secondary">{label}</span>
      <span className={clsx('px-2 py-0.5 text-[9px] font-mono uppercase tracking-wider border transition-colors cursor-pointer', enabled ? 'text-ok border-ok-dim bg-ok/10 group-hover:bg-ok/20' : 'text-danger border-danger-dim bg-danger/10 group-hover:bg-danger/20')}>
        {enabled ? 'on' : 'off'}
      </span>
    </button>
  )
}

function RoutingTable({ routing, onToggle }: { routing: { provider: string; priority: number; enabled: boolean }[]; onToggle: (provider: string) => void }) {
  return (
    <div className="wv-card overflow-hidden">
      <div className="px-3 py-2 border-b border-border"><span className="wv-label">MODEL ROUTING</span></div>
      <div className="divide-y divide-border/50">
        <div className="flex items-center gap-3 px-3 py-2 text-[10px] font-mono text-text-tertiary uppercase tracking-wider">
          <span className="w-6">#</span><span className="flex-1">PROVIDER</span><span className="w-16 text-right">STATUS</span>
        </div>
        {routing.map((r) => (
          <button key={r.provider} onClick={() => onToggle(r.provider)} className="w-full flex items-center gap-3 px-3 py-2 text-[11px] font-mono hover:bg-surface-hover transition-colors">
            <span className="text-text-tertiary w-6">{r.priority}</span>
            <span className="text-text-primary flex-1 text-left">{r.provider}</span>
            <span className={clsx('w-16 text-right', r.enabled ? 'text-ok' : 'text-text-tertiary')}>{r.enabled ? 'ON' : 'OFF'}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

function GovernancePanel({ governance, onToggle }: { governance: { auto_approve_low: boolean; critical_block: boolean }; onToggle: (key: string) => void }) {
  return (
    <div className="wv-card p-4">
      <div className="wv-label mb-3">GOVERNANCE POLICIES</div>
      <div className="space-y-3">
        <Toggle enabled={governance.auto_approve_low} onToggle={() => onToggle('auto_approve_low')} label="Auto-approve low risk" />
        <Toggle enabled={governance.critical_block} onToggle={() => onToggle('critical_block')} label="Block critical actions" />
      </div>
    </div>
  )
}

function NotificationsPanel({ notifications, onToggle }: { notifications: { discord: boolean; file: boolean }; onToggle: (key: string) => void }) {
  return (
    <div className="wv-card p-4">
      <div className="wv-label mb-3">NOTIFICATIONS</div>
      <div className="space-y-3">
        <Toggle enabled={notifications.discord} onToggle={() => onToggle('discord')} label="Discord alerts" />
        <Toggle enabled={notifications.file} onToggle={() => onToggle('file')} label="File logging" />
      </div>
    </div>
  )
}

export function Settings() {
  const { settings } = useCockpitStore()
  const [local, setLocal] = useState<SettingsResponse | null>(null)
  const active = local ?? settings

  if (!active) {
    return (
      <div className="h-full flex flex-col p-4">
        <h1 className="text-[14px] font-mono uppercase tracking-widest text-text-secondary mb-4">Settings</h1>
        <div className="flex-1 flex items-center justify-center text-text-tertiary text-[11px]">Loading settings...</div>
      </div>
    )
  }

  const update = (patch: Partial<SettingsResponse>) => {
    const next = { ...active, ...patch }
    setLocal(next)
    api.updateSettings(patch)
  }

  const toggleRouting = (provider: string) => {
    const next = active.model_routing.map((r) =>
      r.provider === provider ? { ...r, enabled: !r.enabled } : r,
    )
    update({ model_routing: next })
  }

  const toggleGovernance = (key: string) => {
    update({ governance: { ...active.governance, [key]: !active.governance[key as keyof typeof active.governance] } })
  }

  const toggleNotifications = (key: string) => {
    update({ notifications: { ...active.notifications, [key]: !active.notifications[key as keyof typeof active.notifications] } })
  }

  return (
    <div className="h-full flex flex-col p-4 overflow-hidden">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-[14px] font-mono uppercase tracking-widest text-text-secondary">Settings</h1>
        {local && <span className="text-[9px] text-warn font-mono uppercase">modified (runtime-only)</span>}
      </div>
      <div className="flex-1 overflow-y-auto space-y-4">
        <RoutingTable routing={active.model_routing} onToggle={toggleRouting} />
        <div className="grid grid-cols-2 gap-4">
          <GovernancePanel governance={active.governance} onToggle={toggleGovernance} />
          <NotificationsPanel notifications={active.notifications} onToggle={toggleNotifications} />
        </div>
      </div>
    </div>
  )
}
