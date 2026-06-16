import React, { useEffect } from 'react';
import { useOperatorHomeStore } from '../stores/operatorHomeStore';

const severityColor = (severity: string): string => {
  switch (severity) {
    case 'critical': return '#ef4444';
    case 'warning': return '#f59e0b';
    case 'info': return '#3b82f6';
    default: return '#6b7280';
  }
};

const statusColor = (status: string): string => {
  switch (status) {
    case 'healthy': return '#22c55e';
    case 'degraded': return '#f59e0b';
    case 'critical': return '#ef4444';
    default: return '#6b7280';
  }
};

const StatusCard: React.FC<{
  label: string;
  value: number | string;
  status: string;
  detail: string;
}> = ({ label, value, status, detail }) => (
  <div style={{
    background: '#1e1e2e',
    border: `1px solid ${statusColor(status)}40`,
    borderRadius: 8,
    padding: '16px 20px',
    flex: '1 1 0',
    minWidth: 140,
  }}>
    <div style={{ color: '#94a3b8', fontSize: 12, marginBottom: 4 }}>{label}</div>
    <div style={{ color: statusColor(status), fontSize: 28, fontWeight: 700 }}>{value}</div>
    <div style={{ color: '#64748b', fontSize: 11, marginTop: 4 }}>{detail}</div>
  </div>
);

const AttentionRow: React.FC<{
  title: string;
  detail: string;
  severity: string;
  type: string;
}> = ({ title, detail, severity, type }) => (
  <div style={{
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: '10px 16px',
    background: '#1e1e2e',
    borderRadius: 6,
    borderLeft: `3px solid ${severityColor(severity)}`,
  }}>
    <span style={{
      fontSize: 10,
      fontWeight: 600,
      color: severityColor(severity),
      textTransform: 'uppercase',
      minWidth: 60,
    }}>
      {severity}
    </span>
    <span style={{
      fontSize: 10,
      color: '#64748b',
      textTransform: 'uppercase',
      minWidth: 80,
    }}>
      {type}
    </span>
    <div style={{ flex: 1 }}>
      <div style={{ color: '#e2e8f0', fontSize: 13 }}>{title}</div>
      {detail && <div style={{ color: '#64748b', fontSize: 11, marginTop: 2 }}>{detail}</div>}
    </div>
  </div>
);

const TimelineRow: React.FC<{
  summary: string;
  domain: string;
  priority: string;
  timestamp: number;
}> = ({ summary, domain, priority, timestamp }) => (
  <div style={{
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: '8px 16px',
    borderBottom: '1px solid #1e293b',
  }}>
    <span style={{
      fontSize: 10,
      color: priority === 'critical' ? '#ef4444' : '#64748b',
      textTransform: 'uppercase',
      minWidth: 80,
    }}>
      {domain}
    </span>
    <span style={{ color: '#e2e8f0', fontSize: 12, flex: 1 }}>{summary}</span>
    <span style={{ color: '#475569', fontSize: 10 }}>
      {new Date(timestamp * 1000).toLocaleTimeString()}
    </span>
  </div>
);

const SectionHeader: React.FC<{ title: string; count?: number }> = ({ title, count }) => (
  <div style={{
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    marginBottom: 12,
    marginTop: 24,
  }}>
    <h3 style={{ color: '#e2e8f0', fontSize: 14, fontWeight: 600, margin: 0 }}>{title}</h3>
    {count !== undefined && (
      <span style={{
        background: '#334155',
        color: '#94a3b8',
        fontSize: 10,
        padding: '2px 8px',
        borderRadius: 10,
      }}>
        {count}
      </span>
    )}
  </div>
);

export const OperatorHomePanel: React.FC = () => {
  const { snapshot, attention, timeline, loading, error, fetchHome } = useOperatorHomeStore();

  useEffect(() => {
    fetchHome();
    const interval = setInterval(fetchHome, 10000);
    return () => clearInterval(interval);
  }, [fetchHome]);

  if (loading && !snapshot) {
    return <div style={{ color: '#94a3b8', padding: 24 }}>Loading operator context...</div>;
  }

  if (error && !snapshot) {
    return <div style={{ color: '#ef4444', padding: 24 }}>Error: {error}</div>;
  }

  const health = snapshot?.health_summary;
  const cards = health?.cards || [];
  const approvalCount = snapshot?.pending_approvals || 0;

  return (
    <div style={{ padding: 24, maxWidth: 960, color: '#e2e8f0' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700 }}>Organism Home</h2>
        {health && (
          <span style={{
            fontSize: 11,
            fontWeight: 600,
            color: statusColor(health.overall_status),
            textTransform: 'uppercase',
          }}>
            {health.overall_status}
          </span>
        )}
      </div>

      {/* Health Cards */}
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        {cards.map((card) => (
          <StatusCard
            key={card.label}
            label={card.label}
            value={card.value}
            status={card.status}
            detail={card.detail}
          />
        ))}
      </div>

      {/* Attention Items */}
      <SectionHeader title="Needs Attention" count={attention.length} />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {attention.length === 0 ? (
          <div style={{ color: '#64748b', fontSize: 13, padding: '8px 16px' }}>
            Nothing requires attention.
          </div>
        ) : (
          attention.map((item) => (
            <AttentionRow
              key={item.attention_id}
              title={item.title}
              detail={item.detail}
              severity={item.severity}
              type={item.attention_type}
            />
          ))
        )}
      </div>

      {/* Pending Approvals */}
      {approvalCount > 0 && (
        <>
          <SectionHeader title="Pending Approvals" count={approvalCount} />
          <div style={{
            background: '#1e1e2e',
            border: '1px solid #f59e0b40',
            borderRadius: 8,
            padding: 16,
            color: '#f59e0b',
            fontSize: 13,
          }}>
            {approvalCount} governance decision(s) awaiting operator input.
          </div>
        </>
      )}

      {/* Timeline */}
      <SectionHeader title="Recent Changes" count={timeline.length} />
      <div style={{
        background: '#1e1e2e',
        borderRadius: 8,
        overflow: 'hidden',
        maxHeight: 300,
        overflowY: 'auto',
      }}>
        {timeline.length === 0 ? (
          <div style={{ color: '#64748b', fontSize: 13, padding: '12px 16px' }}>
            No recent events.
          </div>
        ) : (
          timeline.slice(0, 20).map((event) => (
            <TimelineRow
              key={event.event_id}
              summary={event.summary}
              domain={event.domain}
              priority={event.priority}
              timestamp={event.timestamp}
            />
          ))
        )}
      </div>
    </div>
  );
};

export default OperatorHomePanel;
