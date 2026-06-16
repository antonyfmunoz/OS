import { useEffect } from "react";
import { usePresenceStore } from "../stores/presenceStore";

const stateColor = (state: string): string => {
  switch (state) {
    case "active":
      return "#22c55e";
    case "idle":
      return "#eab308";
    case "away":
      return "#f97316";
    case "offline":
      return "#6b7280";
    default:
      return "#6b7280";
  }
};

const statusColor = (status: string): string => {
  switch (status) {
    case "current":
      return "#22c55e";
    case "resumable":
      return "#3b82f6";
    case "stale":
      return "#eab308";
    case "lost":
      return "#ef4444";
    default:
      return "#6b7280";
  }
};

function SectionHeader({ title }: { title: string }) {
  return (
    <h3
      style={{
        fontSize: 13,
        fontWeight: 600,
        color: "#94a3b8",
        textTransform: "uppercase",
        letterSpacing: "0.05em",
        marginBottom: 8,
        marginTop: 16,
      }}
    >
      {title}
    </h3>
  );
}

function CurrentSection() {
  const snapshot = usePresenceStore((s) => s.snapshot);
  if (!snapshot) return null;

  const ctx = snapshot.active_context;

  return (
    <div style={{ marginBottom: 16 }}>
      <SectionHeader title="Current" />
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 8,
        }}
      >
        <InfoCard
          label="State"
          value={snapshot.operator_state}
          color={stateColor(snapshot.operator_state)}
        />
        <InfoCard label="Device" value={snapshot.active_device} />
        <InfoCard label="Node" value={snapshot.active_node_id || "—"} />
        <InfoCard label="Workspace" value={ctx.workspace_name || "—"} />
        <InfoCard label="Session" value={ctx.session_type || "—"} />
        <InfoCard label="Runtime" value={ctx.runtime_id || "—"} />
      </div>
    </div>
  );
}

function InfoCard({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <div
      style={{
        background: "#1e293b",
        border: "1px solid #334155",
        borderRadius: 6,
        padding: "8px 12px",
      }}
    >
      <div style={{ fontSize: 11, color: "#64748b" }}>{label}</div>
      <div style={{ fontSize: 14, color: color || "#e2e8f0", fontWeight: 500 }}>
        {value}
      </div>
    </div>
  );
}

function ResumeSection() {
  const resume = usePresenceStore((s) => s.resume);
  const snapshot = usePresenceStore((s) => s.snapshot);

  const checkpoints = snapshot?.continuity_checkpoints || [];
  const resumable = checkpoints.filter(
    (c) => c.status === "current" || c.status === "resumable"
  );

  if (resumable.length === 0 && !resume?.resume_items?.length) {
    return null;
  }

  return (
    <div style={{ marginBottom: 16 }}>
      <SectionHeader title="Resume" />
      {resumable.map((cp) => (
        <div
          key={cp.checkpoint_id}
          style={{
            background: "#1e293b",
            border: "1px solid #334155",
            borderRadius: 6,
            padding: "8px 12px",
            marginBottom: 6,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span
              style={{
                fontSize: 11,
                padding: "1px 6px",
                borderRadius: 4,
                background: statusColor(cp.status) + "22",
                color: statusColor(cp.status),
                fontWeight: 500,
              }}
            >
              {cp.status}
            </span>
            <span style={{ fontSize: 13, color: "#e2e8f0" }}>{cp.title}</span>
          </div>
          {cp.detail && (
            <div style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>
              {cp.detail}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function TimelineSection() {
  const timeline = usePresenceStore((s) => s.timeline);

  if (timeline.length === 0) return null;

  return (
    <div style={{ marginBottom: 16 }}>
      <SectionHeader title="Recent Activity" />
      {timeline.slice(0, 10).map((t) => (
        <div
          key={t.transition_id}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            padding: "4px 0",
            borderBottom: "1px solid #1e293b",
          }}
        >
          <span style={{ fontSize: 11, color: "#64748b", minWidth: 100 }}>
            {t.transition_type.replace(/_/g, " ")}
          </span>
          <span style={{ fontSize: 12, color: "#94a3b8" }}>
            {t.from_value} → {t.to_value}
          </span>
          {t.detail && (
            <span style={{ fontSize: 11, color: "#475569" }}>{t.detail}</span>
          )}
        </div>
      ))}
    </div>
  );
}

export default function OperatorContinuityPanel() {
  const { fetchPresence, fetchTimeline, fetchResume, loading, error } =
    usePresenceStore();

  useEffect(() => {
    fetchPresence();
    fetchTimeline();
    fetchResume();

    const interval = setInterval(() => {
      fetchPresence();
      fetchTimeline();
    }, 10_000);

    return () => clearInterval(interval);
  }, [fetchPresence, fetchTimeline, fetchResume]);

  return (
    <div
      style={{
        padding: 16,
        color: "#e2e8f0",
        fontFamily: "monospace",
        maxWidth: 800,
      }}
    >
      <h2
        style={{
          fontSize: 18,
          fontWeight: 700,
          color: "#f1f5f9",
          marginBottom: 4,
        }}
      >
        Presence & Continuity
      </h2>
      <p style={{ fontSize: 12, color: "#64748b", marginBottom: 16 }}>
        Operator presence across devices and sessions
      </p>

      {loading && (
        <div style={{ color: "#64748b", fontSize: 12 }}>Loading...</div>
      )}
      {error && (
        <div style={{ color: "#ef4444", fontSize: 12 }}>Error: {error}</div>
      )}

      <CurrentSection />
      <ResumeSection />
      <TimelineSection />
    </div>
  );
}
