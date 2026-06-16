import React, { useEffect, useState } from 'react';
import { useUMHNodeStore } from '../stores/umhNodeStore';

const STATUS_COLORS: Record<string, string> = {
  online: '#22c55e',
  offline: '#ef4444',
  degraded: '#f59e0b',
  unknown: '#6b7280',
  coherent: '#22c55e',
  drifted: '#ef4444',
};

function NodeCard({ node }: { node: any }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      style={{
        border: '1px solid #333',
        borderRadius: 6,
        padding: 12,
        marginBottom: 8,
        background: '#1a1a2e',
      }}
    >
      <div
        style={{ display: 'flex', justifyContent: 'space-between', cursor: 'pointer' }}
        onClick={() => setExpanded(!expanded)}
      >
        <div>
          <strong>{node.node_id}</strong>
          <span style={{ color: '#9ca3af', marginLeft: 8 }}>{node.purpose}</span>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {node.primary && (
            <span style={{ color: '#60a5fa', fontSize: 12 }}>PRIMARY</span>
          )}
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: STATUS_COLORS[node.status] || '#6b7280',
              display: 'inline-block',
            }}
          />
          <span style={{ fontSize: 12 }}>{expanded ? '▲' : '▼'}</span>
        </div>
      </div>

      {expanded && (
        <div style={{ marginTop: 10, fontSize: 13 }}>
          <div><strong>Device:</strong> {node.device_id}</div>
          <div><strong>Roles:</strong> {node.roles?.join(', ')}</div>
          <div><strong>Workspaces:</strong> {node.workspace_ids?.join(', ')}</div>

          <div style={{ marginTop: 8 }}>
            <strong>Services ({node.active_services?.length || 0}):</strong>
            <div style={{ marginLeft: 12 }}>
              {node.active_services?.map((s: any) => (
                <div key={s.service_id} style={{ color: s.active ? '#d1d5db' : '#6b7280' }}>
                  {s.service_role} {s.active ? '●' : '○'}
                </div>
              ))}
            </div>
          </div>

          <div style={{ marginTop: 8 }}>
            <strong>Capabilities ({node.capability_ids?.length || 0}):</strong>
            <div style={{ marginLeft: 12, color: '#9ca3af' }}>
              {node.capability_ids?.join(', ')}
            </div>
          </div>

          {node.version?.git_commit && (
            <div style={{ marginTop: 8 }}>
              <strong>Version:</strong>{' '}
              <span style={{ fontFamily: 'monospace', color: '#60a5fa' }}>
                {node.version.git_commit.substring(0, 8)}
              </span>
              {' '}on {node.version.branch}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function UMHNodePanel() {
  const { topology, versionStatus, loading, fetchTopology, fetchVersionStatus } =
    useUMHNodeStore();

  useEffect(() => {
    fetchTopology();
    fetchVersionStatus();
  }, [fetchTopology, fetchVersionStatus]);

  if (loading) return <div style={{ padding: 16 }}>Loading node topology...</div>;

  return (
    <div style={{ padding: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h3 style={{ margin: 0 }}>UMH Organism Nodes</h3>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <span style={{ fontSize: 13, color: '#9ca3af' }}>Version:</span>
          <span
            style={{
              color: STATUS_COLORS[versionStatus] || '#6b7280',
              fontWeight: 600,
            }}
          >
            {versionStatus.toUpperCase()}
          </span>
          <span style={{ fontSize: 13, color: '#6b7280' }}>
            {topology?.node_count || 0} nodes
          </span>
        </div>
      </div>

      {topology?.nodes?.map((node: any) => (
        <NodeCard key={node.node_id} node={node} />
      ))}

      {(!topology?.nodes || topology.nodes.length === 0) && (
        <div style={{ color: '#6b7280', textAlign: 'center', padding: 32 }}>
          No UMH nodes registered
        </div>
      )}
    </div>
  );
}
