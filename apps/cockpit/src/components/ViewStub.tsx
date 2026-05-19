import type { LucideIcon } from 'lucide-react'

interface ViewStubProps {
  title: string
  icon: LucideIcon
  description: string
  features: string[]
}

export function ViewStub({ title, icon: Icon, description, features }: ViewStubProps) {
  return (
    <div className="h-full flex flex-col p-4">
      <h1 className="text-[14px] font-mono uppercase tracking-widest text-text-secondary mb-4">
        {title}
      </h1>
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center max-w-md">
          <Icon size={48} className="text-border mx-auto mb-4" />
          <div className="text-[12px] text-text-secondary mb-4">{description}</div>
          <div className="wv-card p-4 text-left">
            <div className="wv-label mb-2">PLANNED CAPABILITIES</div>
            <ul className="space-y-1">
              {features.map((f) => (
                <li key={f} className="text-[11px] text-text-tertiary flex items-center gap-2">
                  <span className="text-border">○</span>
                  {f}
                </li>
              ))}
            </ul>
          </div>
          <div className="wv-badge wv-badge-cyan mt-4">Awaiting backend integration</div>
        </div>
      </div>
    </div>
  )
}
