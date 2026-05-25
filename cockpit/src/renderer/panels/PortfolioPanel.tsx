import { useState, useEffect } from 'react'
import { fetchApi } from '../api/client'

interface DepartmentData {
  name: string
  slug: string
  agent_name: string
  permission_tier: string
  roles: string[]
  metrics: string[]
  workflows: string[]
  agent: {
    skill_count: number
    skills: string[]
    permission_tier: string
    browser_capable: boolean
  } | null
}

interface RoleData {
  name: string
  department: string
  operator: string
  permission_tier: string
  responsibilities: string[]
  workflows: string[]
  metrics: string[]
}

interface ProductConnection {
  product: string
  status: string
  capabilities: string[]
  signal_types: string[]
  error: string
}

interface ProductSummary {
  total_products: number
  connected: number
  products: string[]
  total_capabilities: number
  total_signal_types: number
  compounding: boolean
}

type View = 'portfolio' | 'department' | 'role'

export function PortfolioPanel() {
  const [departments, setDepartments] = useState<DepartmentData[]>([])
  const [roles, setRoles] = useState<RoleData[]>([])
  const [products, setProducts] = useState<ProductConnection[]>([])
  const [productSummary, setProductSummary] = useState<ProductSummary | null>(null)
  const [selectedDept, setSelectedDept] = useState<string | null>(null)
  const [view, setView] = useState<View>('portfolio')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  async function loadData() {
    setLoading(true)
    try {
      const [deptRes, roleRes, prodRes] = await Promise.all([
        fetchApi<{ departments: DepartmentData[] }>('/entities/departments'),
        fetchApi<{ roles: RoleData[] }>('/entities/roles'),
        fetchApi<{ connections: ProductConnection[]; summary: ProductSummary }>('/products'),
      ])
      setDepartments(deptRes.departments || [])
      setRoles(roleRes.roles || [])
      setProducts(prodRes.connections || [])
      setProductSummary(prodRes.summary || null)
    } catch {
      // API not available — show empty state
    }
    setLoading(false)
  }

  const tierColor = (tier: string) => {
    switch (tier) {
      case 'commit': return 'var(--accent-red)'
      case 'execute': return 'var(--accent-amber)'
      case 'draft': return 'var(--accent-cyan)'
      default: return 'var(--text-tertiary)'
    }
  }

  const statusColor = (status: string) => {
    switch (status) {
      case 'connected':
      case 'configured': return 'var(--accent-green)'
      case 'error': return 'var(--accent-red)'
      default: return 'var(--text-tertiary)'
    }
  }

  const filteredRoles = selectedDept ? roles.filter(r => r.department === selectedDept) : roles

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full" style={{ color: 'var(--text-tertiary)' }}>
        Loading entity data...
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full overflow-y-auto p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>
            {view === 'portfolio' ? 'Portfolio' : view === 'department' ? `Department: ${selectedDept}` : 'All Roles'}
          </h2>
          <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
            {departments.length} departments · {roles.length} roles
          </span>
        </div>
        <div className="flex gap-2">
          {(['portfolio', 'department', 'role'] as View[]).map(v => (
            <button
              key={v}
              onClick={() => { setView(v); if (v === 'portfolio') setSelectedDept(null) }}
              className="px-2 py-1 text-xs rounded"
              style={{
                background: view === v ? 'var(--surface-2)' : 'transparent',
                color: view === v ? 'var(--text-primary)' : 'var(--text-secondary)',
                border: '1px solid var(--border)',
              }}
            >
              {v.charAt(0).toUpperCase() + v.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Product Connections */}
      {view === 'portfolio' && (
        <section className="mb-6">
          <h3 className="hud-text mb-3">Product Connections</h3>
          <div className="grid grid-cols-3 gap-3">
            {products.map(p => (
              <div
                key={p.product}
                className="p-3 rounded"
                style={{ background: 'var(--surface-1)', border: '1px solid var(--border)' }}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                    {p.product.toUpperCase()}
                  </span>
                  <span className="text-xs px-1.5 py-0.5 rounded" style={{ color: statusColor(p.status), border: `1px solid ${statusColor(p.status)}` }}>
                    {p.status}
                  </span>
                </div>
                <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                  {p.capabilities.length} capabilities · {p.signal_types.length} signals
                </div>
                {p.error && (
                  <div className="text-xs mt-1" style={{ color: 'var(--accent-red)' }}>
                    {p.error}
                  </div>
                )}
              </div>
            ))}
          </div>
          {productSummary && productSummary.compounding && (
            <div className="mt-2 text-xs" style={{ color: 'var(--accent-green)' }}>
              Cross-product intelligence compounding active ({productSummary.connected} products linked)
            </div>
          )}
        </section>
      )}

      {/* Department Grid */}
      {(view === 'portfolio' || view === 'department') && (
        <section className="mb-6">
          <h3 className="hud-text mb-3">Departments</h3>
          <div className="grid grid-cols-2 gap-3">
            {departments.map(dept => (
              <div
                key={dept.slug}
                className="p-3 rounded cursor-pointer transition-colors"
                style={{
                  background: selectedDept === dept.slug ? 'var(--surface-2)' : 'var(--surface-1)',
                  border: `1px solid ${selectedDept === dept.slug ? 'var(--accent-cyan)' : 'var(--border)'}`,
                }}
                onClick={() => { setSelectedDept(dept.slug); setView('department') }}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                    {dept.name}
                  </span>
                  <span
                    className="text-xs px-1.5 py-0.5 rounded uppercase"
                    style={{ color: tierColor(dept.permission_tier), border: `1px solid ${tierColor(dept.permission_tier)}` }}
                  >
                    {dept.permission_tier}
                  </span>
                </div>
                <div className="text-xs mb-1" style={{ color: 'var(--text-secondary)' }}>
                  {dept.agent?.skill_count ?? 0} skills · {dept.roles.length} roles · {dept.metrics.length} KPIs
                </div>
                {dept.agent && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {dept.agent.skills.slice(0, 4).map(s => (
                      <span key={s} className="text-xs px-1 py-0.5 rounded" style={{ background: 'var(--surface-2)', color: 'var(--text-tertiary)' }}>
                        {s}
                      </span>
                    ))}
                    {dept.agent.skills.length > 4 && (
                      <span className="text-xs px-1 py-0.5" style={{ color: 'var(--text-tertiary)' }}>
                        +{dept.agent.skills.length - 4}
                      </span>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Roles Table */}
      {(view === 'role' || (view === 'department' && selectedDept)) && (
        <section>
          <h3 className="hud-text mb-3">
            {selectedDept ? `Roles in ${selectedDept}` : 'All Roles'}
          </h3>
          <div className="space-y-2">
            {filteredRoles.map(role => (
              <div
                key={`${role.department}-${role.name}`}
                className="p-3 rounded"
                style={{ background: 'var(--surface-1)', border: '1px solid var(--border)' }}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                      {role.name}
                    </span>
                    <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                      {role.department}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs px-1.5 py-0.5 rounded" style={{ color: 'var(--accent-cyan)', border: '1px solid var(--accent-cyan)' }}>
                      {role.operator}
                    </span>
                    <span
                      className="text-xs px-1.5 py-0.5 rounded uppercase"
                      style={{ color: tierColor(role.permission_tier), border: `1px solid ${tierColor(role.permission_tier)}` }}
                    >
                      {role.permission_tier}
                    </span>
                  </div>
                </div>
                <div className="flex flex-wrap gap-1 mt-1">
                  {role.responsibilities.map(r => (
                    <span key={r} className="text-xs px-1 py-0.5 rounded" style={{ background: 'var(--surface-2)', color: 'var(--text-secondary)' }}>
                      {r}
                    </span>
                  ))}
                </div>
                <div className="text-xs mt-1" style={{ color: 'var(--text-tertiary)' }}>
                  KPIs: {role.metrics.join(', ')}
                </div>
              </div>
            ))}
            {filteredRoles.length === 0 && (
              <div className="text-xs p-4 text-center" style={{ color: 'var(--text-tertiary)' }}>
                No roles {selectedDept ? `in ${selectedDept}` : 'found'}
              </div>
            )}
          </div>
        </section>
      )}
    </div>
  )
}
