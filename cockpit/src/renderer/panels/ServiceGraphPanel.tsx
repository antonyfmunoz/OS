import React, { useEffect, useState } from 'react';
import { useServiceGraphStore } from '../stores/serviceGraphStore';
import { useCollapseStore } from '../stores/collapseStore';

const criticalityColor = (criticality: string): string => {
  switch (criticality) {
    case 'critical': return '#ef4444';
    case 'core': return '#f97316';
    case 'supporting': return '#eab308';
    case 'optional': return '#6b7280';
    default: return '#6b7280';
  }
};

const severityColor = (severity: string): string => {
  switch (severity) {
    case 'critical': return '#ef4444';
    case 'high': return '#f97316';
    case 'medium': return '#eab308';
    case 'low': return '#22c55e';
    default: return '#6b7280';
  }
};

type TabId = 'services' | 'critical-path' | 'impact';

const ServiceCard: React.FC<{ service: any; onSelect: (role: string) => void }> = ({ service, onSelect }) => {
  const key = `service:${service.service_role}`
  const expanded = useCollapseStore((s) => s.isOpen(key))
  const toggle = useCollapseStore((s) => s.toggle)

  return (
    <div
      style={{
        border: '1px solid #374151',
        borderRadius: 8,
        padding: 12,
        marginBottom: 8,
        background: '#1f2937',
        cursor: 'pointer',
      }}
      onClick={() => toggle(key)}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ fontWeight: 600, fontSize: 13 }}>{service.service_role}</div>
        <div
          style={{
            fontSize: 11,
            padding: '2px 8px',
            borderRadius: 4,
            background: criticalityColor(service.criticality) + '22',
            color: criticalityColor(service.criticality),
            textTransform: 'uppercase',
          }}
        >
          {service.criticality}
        </div>
      </div>
      <div style={{ fontSize: 12, color: '#9ca3af', marginTop: 4 }}>{service.description}</div>
      {expanded && (
        <div style={{ fontSize: 12, color: '#9ca3af', marginTop: 8, borderTop: '1px solid #374151', paddingTop: 8 }}>
          <div>Node: {service.owner_node}</div>
          {service.state_domains.length > 0 && (
            <div>Domains: {service.state_domains.join(', ')}</div>
          )}
          <button
            style={{
              marginTop: 8,
              padding: '4px 12px',
              fontSize: 11,
              background: '#374151',
              border: '1px solid #4b5563',
              borderRadius: 4,
              color: '#d1d5db',
              cursor: 'pointer',
            }}
            onClick={(e) => { e.stopPropagation(); onSelect(service.service_role); }}
          >
            Show Failure Impact
          </button>
        </div>
      )}
    </div>
  );
};

export const ServiceGraphPanel: React.FC = () => {
  const { services, impact, criticalPath, loading, error, fetchServices, fetchImpact, fetchCriticalPath } = useServiceGraphStore();
  const [activeTab, setActiveTab] = useState<TabId>('services');

  useEffect(() => {
    fetchServices();
    fetchCriticalPath();
  }, [fetchServices, fetchCriticalPath]);

  const handleImpactSelect = (role: string) => {
    fetchImpact(role);
    setActiveTab('impact');
  };

  if (loading && services.length === 0) return <div style={{ padding: 16, color: '#9ca3af' }}>Loading service graph...</div>;
  if (error) return <div style={{ padding: 16, color: '#ef4444' }}>Error: {error}</div>;

  const tabs: { id: TabId; label: string }[] = [
    { id: 'services', label: 'Services' },
    { id: 'critical-path', label: 'Critical Path' },
    { id: 'impact', label: 'Failure Impact' },
  ];

  return (
    <div style={{ padding: 16 }}>
      <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600, marginBottom: 12 }}>Service Dependency Graph</h3>
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        {tabs.map((tab) => (
          <button
            key={tab.id}
            style={{
              padding: '6px 14px',
              fontSize: 12,
              background: activeTab === tab.id ? '#374151' : 'transparent',
              border: '1px solid #374151',
              borderRadius: 6,
              color: activeTab === tab.id ? '#f9fafb' : '#9ca3af',
              cursor: 'pointer',
            }}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'services' && (
        <div>
          <div style={{ fontSize: 13, color: '#9ca3af', marginBottom: 8 }}>{services.length} services</div>
          {services.map((svc) => (
            <ServiceCard key={svc.service_role} service={svc} onSelect={handleImpactSelect} />
          ))}
        </div>
      )}

      {activeTab === 'critical-path' && (
        <div>
          {criticalPath.map((entry, i) => (
            <div
              key={entry.service_role}
              style={{
                border: '1px solid #374151',
                borderRadius: 8,
                padding: 12,
                marginBottom: 8,
                background: '#1f2937',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <div>
                <div style={{ fontWeight: 600, fontSize: 13 }}>#{i + 1} {entry.service_role}</div>
                <div style={{ fontSize: 12, color: '#9ca3af' }}>
                  {entry.direct_dependents} direct, {entry.transitive_dependents} transitive
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: 18, fontWeight: 700, color: criticalityColor(entry.criticality) }}>
                  {entry.blast_radius}
                </div>
                <div style={{ fontSize: 11, color: '#9ca3af' }}>blast radius</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {activeTab === 'impact' && impact && (
        <div style={{ border: '1px solid #374151', borderRadius: 8, padding: 16, background: '#1f2937' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
            <div style={{ fontWeight: 600, fontSize: 14 }}>If {impact.failed_service} fails</div>
            <div
              style={{
                fontSize: 12,
                padding: '2px 10px',
                borderRadius: 4,
                background: severityColor(impact.severity) + '22',
                color: severityColor(impact.severity),
                textTransform: 'uppercase',
              }}
            >
              {impact.severity}
            </div>
          </div>
          <div style={{ fontSize: 13, color: '#9ca3af', marginBottom: 8 }}>
            Blast radius: {impact.blast_radius} services
          </div>
          {impact.directly_affected.length > 0 && (
            <div style={{ marginBottom: 8 }}>
              <div style={{ fontSize: 12, color: '#d1d5db', marginBottom: 4 }}>Directly affected:</div>
              {impact.directly_affected.map((s) => (
                <span key={s} style={{ fontSize: 12, color: '#ef4444', marginRight: 8 }}>{s}</span>
              ))}
            </div>
          )}
          {impact.transitively_affected.length > 0 && (
            <div style={{ marginBottom: 8 }}>
              <div style={{ fontSize: 12, color: '#d1d5db', marginBottom: 4 }}>Transitively affected:</div>
              {impact.transitively_affected.map((s) => (
                <span key={s} style={{ fontSize: 12, color: '#eab308', marginRight: 8 }}>{s}</span>
              ))}
            </div>
          )}
          {impact.affected_state_domains.length > 0 && (
            <div>
              <div style={{ fontSize: 12, color: '#d1d5db', marginBottom: 4 }}>Affected state domains:</div>
              {impact.affected_state_domains.map((d) => (
                <span key={d} style={{ fontSize: 12, color: '#f97316', marginRight: 8 }}>{d}</span>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'impact' && !impact && (
        <div style={{ padding: 16, color: '#9ca3af', fontSize: 13 }}>
          Select a service from the Services tab to see its failure impact.
        </div>
      )}
    </div>
  );
};

export default ServiceGraphPanel;
