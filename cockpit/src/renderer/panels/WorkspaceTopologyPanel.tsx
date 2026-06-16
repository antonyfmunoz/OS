/**
 * WorkspaceTopologyPanel — workspace→repos→runtimes→devices topology view.
 *
 * Separate from existing WorkspacePanel (file/git/test operations).
 * Read-only topology visualization with health indicators.
 *
 * Phase 27.
 */

import React, { useEffect, useState } from 'react';
import { useWorkspaceTopologyStore, type WorkspaceEntry } from '../stores/workspaceTopologyStore';

const healthColor = (h: string): string => {
  switch (h) {
    case 'healthy': return '#22c55e';
    case 'degraded': return '#eab308';
    case 'blocked': return '#ef4444';
    default: return '#6b7280';
  }
};

const healthLabel = (h: string): string => {
  switch (h) {
    case 'healthy': return 'Healthy';
    case 'degraded': return 'Degraded';
    case 'blocked': return 'Blocked';
    default: return 'Unknown';
  }
};

const WorkspaceCard: React.FC<{ ws: WorkspaceEntry }> = ({ ws }) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      style={{
        border: '1px solid var(--wv-border, #333)',
        borderRadius: 6,
        padding: 12,
        marginBottom: 8,
        background: 'var(--wv-surface, #1a1a2e)',
      }}
    >
      <div
        style={{ display: 'flex', alignItems: 'center', cursor: 'pointer', gap: 8 }}
        onClick={() => setExpanded(!expanded)}
      >
        <span style={{ fontSize: 12, color: '#888' }}>{expanded ? '▼' : '▶'}</span>
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: healthColor(ws.health),
            display: 'inline-block',
          }}
        />
        <strong>{ws.name}</strong>
        <span style={{ fontSize: 12, color: '#888', marginLeft: 'auto' }}>
          {ws.workspace_type} · {healthLabel(ws.health)}
        </span>
      </div>

      {expanded && (
        <div style={{ marginTop: 10, paddingLeft: 16 }}>
          <div style={{ marginBottom: 8 }}>
            <div style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>Repositories</div>
            {ws.repositories.map((r) => (
              <div key={r.repository_id} style={{ fontSize: 13, marginBottom: 2 }}>
                {r.name} <span style={{ color: '#666' }}>({r.branch})</span>
                {r.path && <span style={{ color: '#555', fontSize: 11 }}> — {r.path}</span>}
              </div>
            ))}
          </div>

          <div style={{ marginBottom: 8 }}>
            <div style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>Runtimes</div>
            {ws.runtimes.map((r) => (
              <div key={r.runtime_id} style={{ fontSize: 13, marginBottom: 2 }}>
                {r.runtime_id}{' '}
                <span style={{ color: '#666' }}>
                  ({r.runtime_type} @ {r.host_device_id})
                </span>
              </div>
            ))}
          </div>

          <div style={{ marginBottom: 8 }}>
            <div style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>Build Targets</div>
            {ws.build_targets.map((b) => (
              <div key={b.target_id} style={{ fontSize: 13, marginBottom: 2 }}>
                {b.build_type} → {b.device_id}
                {b.preferred && <span style={{ color: '#22c55e', marginLeft: 4 }}>★</span>}
              </div>
            ))}
          </div>

          <div>
            <div style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>Devices</div>
            <div style={{ fontSize: 13, color: '#aaa' }}>{ws.device_ids.join(', ')}</div>
          </div>
        </div>
      )}
    </div>
  );
};

const WorkspaceTopologyPanel: React.FC = () => {
  const { topology, loading, error, fetchTopology } = useWorkspaceTopologyStore();

  useEffect(() => {
    fetchTopology();
  }, [fetchTopology]);

  if (loading) {
    return <div style={{ padding: 16, color: '#888' }}>Loading topology...</div>;
  }

  if (error) {
    return <div style={{ padding: 16, color: '#ef4444' }}>Error: {error}</div>;
  }

  if (!topology) {
    return <div style={{ padding: 16, color: '#888' }}>No topology data</div>;
  }

  return (
    <div style={{ padding: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 16, gap: 12 }}>
        <h3 style={{ margin: 0 }}>Workspace Topology</h3>
        <span style={{ fontSize: 12, color: '#666' }}>
          {topology.workspace_count} workspaces
        </span>
        <button
          onClick={fetchTopology}
          style={{
            marginLeft: 'auto',
            padding: '4px 12px',
            fontSize: 12,
            background: 'var(--wv-surface, #1a1a2e)',
            border: '1px solid var(--wv-border, #333)',
            borderRadius: 4,
            color: '#ccc',
            cursor: 'pointer',
          }}
        >
          Refresh
        </button>
      </div>

      {topology.workspaces.map((ws) => (
        <WorkspaceCard key={ws.workspace_id} ws={ws} />
      ))}
    </div>
  );
};

export default WorkspaceTopologyPanel;
