import React, { useEffect, useState } from 'react';
import { useStateAuthorityStore } from '../stores/stateAuthorityStore';
import { useCollapseStore } from '../stores/collapseStore';

const statusColor = (status: string): string => {
  switch (status) {
    case 'coherent': return '#22c55e';
    case 'stale': return '#eab308';
    case 'drifted': return '#ef4444';
    default: return '#6b7280';
  }
};

const healthColor = (health: string): string => {
  switch (health) {
    case 'healthy': return '#22c55e';
    case 'degraded': return '#eab308';
    default: return '#6b7280';
  }
};

const DomainCard: React.FC<{ domain: any }> = ({ domain }) => {
  const key = `domain:${domain.domain}`
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
        <div style={{ fontWeight: 600, textTransform: 'uppercase', fontSize: 13 }}>
          {domain.domain}
        </div>
        <div
          style={{
            width: 10,
            height: 10,
            borderRadius: '50%',
            background: statusColor(domain.status),
          }}
        />
      </div>
      <div style={{ fontSize: 12, color: '#9ca3af', marginTop: 4 }}>
        Authority: {domain.authority_node || 'unknown'}
      </div>
      {expanded && (
        <div style={{ fontSize: 12, color: '#9ca3af', marginTop: 8, borderTop: '1px solid #374151', paddingTop: 8 }}>
          <div>Storage: {domain.storage_location || 'unknown'}</div>
          <div>Service: {domain.service_owner || 'unknown'}</div>
          <div>Status: {domain.status}</div>
        </div>
      )}
    </div>
  );
};

export const StateAuthorityPanel: React.FC = () => {
  const { coherence, loading, error, fetchCoherence } = useStateAuthorityStore();

  useEffect(() => {
    fetchCoherence();
  }, [fetchCoherence]);

  if (loading) return <div style={{ padding: 16, color: '#9ca3af' }}>Loading state authority...</div>;
  if (error) return <div style={{ padding: 16, color: '#ef4444' }}>Error: {error}</div>;
  if (!coherence) return <div style={{ padding: 16, color: '#9ca3af' }}>No state data</div>;

  return (
    <div style={{ padding: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>State Authority</h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div
            style={{
              width: 10,
              height: 10,
              borderRadius: '50%',
              background: healthColor(coherence.overall_health),
            }}
          />
          <span style={{ fontSize: 13, color: '#9ca3af' }}>
            {coherence.overall_health} ({coherence.domain_count} domains)
          </span>
        </div>
      </div>
      <div>
        {coherence.domains.map((domain) => (
          <DomainCard key={domain.domain} domain={domain} />
        ))}
      </div>
    </div>
  );
};

export default StateAuthorityPanel;
