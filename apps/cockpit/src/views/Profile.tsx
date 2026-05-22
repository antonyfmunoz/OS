import { useCockpitStore } from '../stores/cockpitStore.ts'
import { clsx } from 'clsx'

function InfoRow({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-border/50">
      <span className="wv-label">{label}</span>
      <span className={clsx('text-[11px] font-mono', color ?? 'text-text-primary')}>{value}</span>
    </div>
  )
}

export function Profile() {
  const { profile } = useCockpitStore()

  if (!profile) {
    return (
      <div className="h-full flex flex-col p-4">
        <h1 className="text-[14px] font-mono uppercase tracking-widest text-text-secondary mb-4">Profile</h1>
        <div className="flex-1 flex items-center justify-center text-text-tertiary text-[11px]">Loading profile...</div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col p-4 overflow-hidden">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-[14px] font-mono uppercase tracking-widest text-text-secondary">Profile</h1>
      </div>
      <div className="max-w-lg space-y-4">
        <div className="wv-card p-4">
          <div className="wv-label mb-3">IDENTITY</div>
          <div className="space-y-0">
            <InfoRow label="NAME" value={profile.name} color="text-cyan" />
            <InfoRow label="ORG" value={profile.org} />
            <InfoRow label="STAGE" value={profile.stage} />
            <InfoRow label="IDENTITY ID" value={profile.identity_id} color="text-text-tertiary" />
          </div>
        </div>
        <div className="wv-card p-4">
          <div className="wv-label mb-3">CONTINUITY</div>
          <div className="flex items-center gap-4">
            <div className="wv-metric text-cyan">{(profile.continuity_score * 100).toFixed(0)}%</div>
            <div className="flex-1 h-2 bg-border rounded-full overflow-hidden">
              <div className="h-full bg-cyan rounded-full transition-all" style={{ width: `${profile.continuity_score * 100}%` }} />
            </div>
          </div>
        </div>
        <div className="wv-card p-4">
          <div className="wv-label mb-3">VENTURES</div>
          <div className="flex flex-wrap gap-2">
            {profile.ventures.map((v) => (
              <span key={v} className="wv-badge wv-badge-violet">{v}</span>
            ))}
            {profile.ventures.length === 0 && <span className="text-[11px] text-text-tertiary">No ventures configured</span>}
          </div>
        </div>
      </div>
    </div>
  )
}
