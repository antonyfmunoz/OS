import { useState, useEffect } from 'react'
import { fetchApi } from '../api/client'

interface CompanyData {
  id: string; name: string; stage: number; stage_name: string; north_star: string
}

interface DepartmentData {
  name: string; slug: string; agent_name: string; permission_tier: string
  roles: string[]; metrics: string[]; workflows: string[]
}

interface RoleData {
  name: string; department: string; operator: string; permission_tier: string
  responsibilities: string[]
}

interface WorkflowData {
  name: string; department: string; trigger: string; steps: string[]; status: string
}

type View = 'overview' | 'departments' | 'workflows'

export function CompanyPanel() {
  const [companies, setCompanies] = useState<CompanyData[]>([])
  const [departments, setDepartments] = useState<DepartmentData[]>([])
  const [roles, setRoles] = useState<RoleData[]>([])
  const [workflows, setWorkflows] = useState<WorkflowData[]>([])
  const [selectedCompany, setSelectedCompany] = useState<CompanyData | null>(null)
  const [selectedDept, setSelectedDept] = useState<string | null>(null)
  const [view, setView] = useState<View>('overview')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  async function loadData() {
    setLoading(true)
    try {
      const [compRes, deptRes, roleRes, wfRes] = await Promise.all([
        fetchApi<{ companies: CompanyData[] }>('/entities/companies'),
        fetchApi<{ departments: DepartmentData[] }>('/entities/departments'),
        fetchApi<{ roles: RoleData[] }>('/entities/roles'),
        fetchApi<{ workflows: WorkflowData[] }>('/entities/workflows'),
      ])
      const comps = compRes.companies || []
      setCompanies(comps)
      setDepartments(deptRes.departments || [])
      setRoles(roleRes.roles || [])
      setWorkflows(wfRes.workflows || [])
      if (comps.length > 0) setSelectedCompany(comps[0])
    } catch {
      // API not available — show empty state
    }
    setLoading(false)
  }

  const tierColor = (tier: string) => {
    switch (tier) {
      case 'commit': return 'var(--color-danger)'
      case 'execute': return 'var(--color-warn)'
      case 'draft': return 'var(--color-cyan)'
      default: return 'var(--color-text-tertiary)'
    }
  }

  const statusColor = (status: string) => {
    switch (status) {
      case 'active': return 'var(--color-ok)'
      case 'paused': return 'var(--color-warn)'
      case 'draft': return 'var(--color-text-tertiary)'
      default: return 'var(--color-text-tertiary)'
    }
  }

  const stageColor = (stage: number) => {
    if (stage <= 2) return 'var(--color-warn)'
    if (stage <= 4) return 'var(--color-cyan)'
    return 'var(--color-ok)'
  }

  const deptRoles = (slug: string) => roles.filter(r => r.department === slug)
  const deptWorkflows = selectedDept
    ? workflows.filter(w => w.department === selectedDept)
    : workflows
  const deptKpis = (slug: string) => {
    const dept = departments.find(d => d.slug === slug)
    return dept?.metrics || []
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full" style={{ color: 'var(--color-text-tertiary)' }}>
        Loading company data...
      </div>
    )
  }

  if (companies.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-2" style={{ color: 'var(--color-text-tertiary)' }}>
        <span className="text-2xl">◆</span>
        <span className="text-sm">No companies registered</span>
        <span className="text-xs">Register a company through the UMH API to see it here.</span>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full overflow-y-auto p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          {companies.length > 1 ? (
            <select
              value={selectedCompany?.id || ''}
              onChange={(e) => setSelectedCompany(companies.find(c => c.id === e.target.value) || null)}
              className="text-lg font-semibold bg-transparent outline-none cursor-pointer"
              style={{ color: 'var(--color-text-primary)', border: 'none' }}
            >
              {companies.map(c => (
                <option key={c.id} value={c.id} style={{ background: 'var(--color-surface)' }}>{c.name}</option>
              ))}
            </select>
          ) : (
            <h2 className="text-lg font-semibold" style={{ color: 'var(--color-text-primary)' }}>
              {selectedCompany?.name}
            </h2>
          )}
          {selectedCompany && (
            <span
              className="text-xs px-2 py-0.5 rounded-full font-medium"
              style={{ color: stageColor(selectedCompany.stage), border: `1px solid ${stageColor(selectedCompany.stage)}` }}
            >
              Stage {selectedCompany.stage} — {selectedCompany.stage_name}
            </span>
          )}
        </div>
        <div className="flex gap-2">
          {(['overview', 'departments', 'workflows'] as View[]).map(v => (
            <button
              key={v}
              onClick={() => { setView(v); if (v === 'overview') setSelectedDept(null) }}
              className="px-2 py-1 text-xs rounded"
              style={{
                background: view === v ? 'var(--color-surface-raised)' : 'transparent',
                color: view === v ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
                border: '1px solid var(--color-border)',
              }}
            >
              {v.charAt(0).toUpperCase() + v.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* North Star */}
      {selectedCompany?.north_star && view === 'overview' && (
        <div
          className="mb-4 p-3 rounded"
          style={{ background: 'var(--color-surface)', border: '1px solid var(--color-ok)', borderLeft: '3px solid var(--color-ok)' }}
        >
          <div className="text-xs uppercase tracking-wider mb-1" style={{ color: 'var(--color-ok)' }}>
            North Star
          </div>
          <div className="text-sm" style={{ color: 'var(--color-text-primary)' }}>
            {selectedCompany.north_star}
          </div>
        </div>
      )}

      {/* Department Grid */}
      {(view === 'overview' || view === 'departments') && (
        <section className="mb-6">
          <h3 className="wv-label mb-3">Departments</h3>
          <div className="grid grid-cols-2 gap-3">
            {departments.map(dept => (
              <div
                key={dept.slug}
                className="p-3 rounded cursor-pointer transition-colors"
                style={{
                  background: selectedDept === dept.slug ? 'var(--color-surface-raised)' : 'var(--color-surface)',
                  border: `1px solid ${selectedDept === dept.slug ? 'var(--color-cyan)' : 'var(--color-border)'}`,
                }}
                onClick={() => { setSelectedDept(dept.slug); setView('departments') }}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium" style={{ color: 'var(--color-text-primary)' }}>
                    {dept.name}
                  </span>
                  <span
                    className="text-xs px-1.5 py-0.5 rounded uppercase"
                    style={{ color: tierColor(dept.permission_tier), border: `1px solid ${tierColor(dept.permission_tier)}` }}
                  >
                    {dept.permission_tier}
                  </span>
                </div>
                <div className="text-xs mb-1" style={{ color: 'var(--color-text-secondary)' }}>
                  {dept.agent_name} · {dept.roles.length} roles · {dept.workflows.length} workflows
                </div>
                {dept.metrics.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {dept.metrics.slice(0, 3).map(m => (
                      <span key={m} className="text-xs px-1 py-0.5 rounded" style={{ background: 'var(--color-surface-raised)', color: 'var(--color-text-tertiary)' }}>
                        {m}
                      </span>
                    ))}
                    {dept.metrics.length > 3 && (
                      <span className="text-xs px-1 py-0.5" style={{ color: 'var(--color-text-tertiary)' }}>
                        +{dept.metrics.length - 3}
                      </span>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
          {departments.length === 0 && (
            <div className="text-xs p-4 text-center" style={{ color: 'var(--color-text-tertiary)' }}>
              No departments configured
            </div>
          )}
        </section>
      )}

      {/* Department Detail: Roles */}
      {view === 'departments' && selectedDept && (
        <section className="mb-6">
          <h3 className="wv-label mb-3">Roles in {selectedDept}</h3>
          <div className="space-y-2">
            {deptRoles(selectedDept).map(role => (
              <div
                key={`${role.department}-${role.name}`}
                className="p-3 rounded"
                style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium" style={{ color: 'var(--color-text-primary)' }}>{role.name}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs px-1.5 py-0.5 rounded" style={{ color: 'var(--color-cyan)', border: '1px solid var(--color-cyan)' }}>
                      {role.operator}
                    </span>
                    <span className="text-xs px-1.5 py-0.5 rounded uppercase" style={{ color: tierColor(role.permission_tier), border: `1px solid ${tierColor(role.permission_tier)}` }}>
                      {role.permission_tier}
                    </span>
                  </div>
                </div>
                <div className="flex flex-wrap gap-1 mt-1">
                  {role.responsibilities.map(r => (
                    <span key={r} className="text-xs px-1 py-0.5 rounded" style={{ background: 'var(--color-surface-raised)', color: 'var(--color-text-secondary)' }}>{r}</span>
                  ))}
                </div>
              </div>
            ))}
            {deptRoles(selectedDept).length === 0 && (
              <div className="text-xs p-4 text-center" style={{ color: 'var(--color-text-tertiary)' }}>No roles in {selectedDept}</div>
            )}
          </div>
        </section>
      )}

      {/* KPI Summary */}
      {view === 'departments' && selectedDept && deptKpis(selectedDept).length > 0 && (
        <section className="mb-6">
          <h3 className="wv-label mb-3">KPIs</h3>
          <div className="grid grid-cols-3 gap-2">
            {deptKpis(selectedDept).map(kpi => (
              <div key={kpi} className="p-2 rounded text-center" style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}>
                <span className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>{kpi}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Workflow List */}
      {(view === 'workflows' || (view === 'departments' && selectedDept)) && (
        <section>
          <h3 className="wv-label mb-3">
            {selectedDept ? `Workflows in ${selectedDept}` : 'All Workflows'}
          </h3>
          <div className="space-y-2">
            {deptWorkflows.map(wf => (
              <div
                key={`${wf.department}-${wf.name}`}
                className="p-3 rounded"
                style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium" style={{ color: 'var(--color-text-primary)' }}>{wf.name}</span>
                    <span className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>{wf.department}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs px-1.5 py-0.5 rounded" style={{ color: 'var(--color-cyan)', border: '1px solid var(--color-cyan)' }}>
                      {wf.trigger}
                    </span>
                    <span className="text-xs px-1.5 py-0.5 rounded" style={{ color: statusColor(wf.status), border: `1px solid ${statusColor(wf.status)}` }}>
                      {wf.status}
                    </span>
                  </div>
                </div>
                <div className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>
                  {wf.steps.length} steps
                </div>
              </div>
            ))}
            {deptWorkflows.length === 0 && (
              <div className="text-xs p-4 text-center" style={{ color: 'var(--color-text-tertiary)' }}>
                No workflows {selectedDept ? `in ${selectedDept}` : 'found'}
              </div>
            )}
          </div>
        </section>
      )}

      {/* Overview KPI Summary */}
      {view === 'overview' && departments.length > 0 && (
        <section>
          <h3 className="wv-label mb-3">KPI Summary</h3>
          <div className="grid grid-cols-4 gap-3">
            {[
              { value: departments.length, label: 'Departments', color: 'var(--color-ok)' },
              { value: roles.length, label: 'Roles', color: 'var(--color-cyan)' },
              { value: workflows.length, label: 'Workflows', color: 'var(--color-warn)' },
              { value: departments.reduce((s, d) => s + d.metrics.length, 0), label: 'KPIs', color: 'var(--color-text-primary)' },
            ].map(stat => (
              <div key={stat.label} className="p-3 rounded text-center" style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}>
                <div className="text-xl font-semibold" style={{ color: stat.color }}>{stat.value}</div>
                <div className="text-xs mt-1" style={{ color: 'var(--color-text-tertiary)' }}>{stat.label}</div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
