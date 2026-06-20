import { useEffect } from "react";
import { useScreenAwarenessStore } from "../stores/screenAwarenessStore";

const sourceColor = (source: string): string => {
  switch (source) {
    case "observed":
      return "#22c55e";
    case "reported":
      return "#eab308";
    case "inferred":
      return "#94a3b8";
    default:
      return "#64748b";
  }
};

const statusColor = (status: string): string => {
  switch (status) {
    case "active":
      return "#22c55e";
    case "stale":
      return "#eab308";
    case "unknown":
      return "#64748b";
    default:
      return "#64748b";
  }
};

const confidenceLabel = (c: number): string => {
  if (c >= 0.8) return "high";
  if (c >= 0.5) return "medium";
  if (c > 0) return "low";
  return "none";
};

function SectionHeader({ title }: { title: string }) {
  return (
    <h3
      style={{
        fontSize: 13,
        fontWeight: 600,
        color: "#94a3b8",
        textTransform: "uppercase",
        letterSpacing: 1,
        marginTop: 20,
        marginBottom: 8,
        borderBottom: "1px solid #334155",
        paddingBottom: 4,
      }}
    >
      {title}
    </h3>
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
        display: "inline-block",
        background: "#1e293b",
        borderRadius: 6,
        padding: "8px 12px",
        marginRight: 8,
        marginBottom: 8,
        minWidth: 120,
      }}
    >
      <div style={{ fontSize: 10, color: "#64748b", marginBottom: 2 }}>
        {label}
      </div>
      <div style={{ fontSize: 14, color: color || "#e2e8f0", fontWeight: 500 }}>
        {value || "—"}
      </div>
    </div>
  );
}

function SourceSection() {
  const snapshot = useScreenAwarenessStore((s) => s.snapshot);
  if (!snapshot) return null;

  return (
    <div>
      <SectionHeader title="Source & Provenance" />
      <InfoCard
        label="Source"
        value={snapshot.source_type.toUpperCase()}
        color={sourceColor(snapshot.source_type)}
      />
      <InfoCard
        label="Status"
        value={snapshot.status}
        color={statusColor(snapshot.status)}
      />
      <InfoCard label="Node" value={snapshot.source_node_id} />
      <InfoCard label="Device" value={snapshot.source_device_id} />
      <InfoCard label="Role" value={snapshot.source_device_role} />
      <InfoCard
        label="Confidence"
        value={`${confidenceLabel(snapshot.source_confidence)} (${snapshot.source_confidence})`}
      />
    </div>
  );
}

function ApplicationSection() {
  const snapshot = useScreenAwarenessStore((s) => s.snapshot);
  const app = snapshot?.active_application;
  if (!app) return null;

  return (
    <div>
      <SectionHeader title="Current Application" />
      <InfoCard label="Application" value={app.app_name} />
      <InfoCard label="Category" value={app.category} />
      {app.window_title && (
        <InfoCard label="Window" value={app.window_title} />
      )}
    </div>
  );
}

function RepositorySection() {
  const snapshot = useScreenAwarenessStore((s) => s.snapshot);
  const repo = snapshot?.repository_context;
  if (!repo) return null;

  return (
    <div>
      <SectionHeader title="Active Repository" />
      <InfoCard label="Repository" value={repo.repo_name} />
      <InfoCard label="Branch" value={repo.branch} />
      <InfoCard label="Dirty Files" value={String(repo.dirty_files)} />
      {repo.active_file && (
        <InfoCard label="Active File" value={repo.active_file} />
      )}
    </div>
  );
}

function FileSection() {
  const snapshot = useScreenAwarenessStore((s) => s.snapshot);
  const fc = snapshot?.file_context;
  if (!fc) return null;

  return (
    <div>
      <SectionHeader title="File Context" />
      <InfoCard label="File" value={fc.file_name} />
      <InfoCard label="Path" value={fc.file_path} />
      {fc.language && <InfoCard label="Language" value={fc.language} />}
      {fc.line_number > 0 && (
        <InfoCard label="Line" value={String(fc.line_number)} />
      )}
    </div>
  );
}

function BrowserSection() {
  const snapshot = useScreenAwarenessStore((s) => s.snapshot);
  const bc = snapshot?.browser_context;
  if (!bc || (!bc.url && !bc.title)) return null;

  return (
    <div>
      <SectionHeader title="Browser Context" />
      {bc.title && <InfoCard label="Tab" value={bc.title} />}
      {bc.domain && <InfoCard label="Domain" value={bc.domain} />}
    </div>
  );
}

function ProvidersSection() {
  const providers = useScreenAwarenessStore((s) => s.providers);
  if (!providers) return null;

  return (
    <div>
      <SectionHeader title="Provider Status" />
      {Object.entries(providers).map(([key, prov]) => (
        <div
          key={key}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            marginBottom: 4,
          }}
        >
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: prov.available ? "#22c55e" : "#64748b",
              display: "inline-block",
            }}
          />
          <span style={{ fontSize: 13, color: "#e2e8f0", minWidth: 80 }}>
            {key.toUpperCase()}
          </span>
          <span style={{ fontSize: 12, color: "#94a3b8" }}>
            {prov.available ? "available" : "unavailable"}
          </span>
          <span style={{ fontSize: 12, color: "#64748b" }}>
            {prov.node_id}
          </span>
        </div>
      ))}
    </div>
  );
}

function VisualContextSection() {
  const visualOps = useScreenAwarenessStore((s) => s.visualOps);
  const binding = visualOps?.context_binding;
  if (!binding || !binding.depth) return null;

  return (
    <div>
      <SectionHeader title="Visual Context" />
      <InfoCard label="Depth" value={binding.depth.toUpperCase()} color="#a78bfa" />
      {binding.campaign && (
        <InfoCard label="Campaign" value={binding.campaign} color="#f472b6" />
      )}
      {binding.goals && binding.goals.length > 0 && (
        <div style={{ marginTop: 4 }}>
          <div style={{ fontSize: 10, color: "#64748b", marginBottom: 4 }}>
            Goals
          </div>
          {binding.goals.slice(0, 3).map((goal, i) => (
            <div
              key={i}
              style={{
                fontSize: 12,
                color: "#94a3b8",
                paddingLeft: 8,
                borderLeft: "2px solid #334155",
                marginBottom: 2,
              }}
            >
              {String(goal)}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function VisualAttentionSection() {
  const visualOps = useScreenAwarenessStore((s) => s.visualOps);
  if (!visualOps || (!visualOps.critical_count && !visualOps.warning_count))
    return null;

  const severityColor = (s: string) => {
    switch (s) {
      case "critical":
        return "#ef4444";
      case "warning":
        return "#eab308";
      default:
        return "#94a3b8";
    }
  };

  return (
    <div>
      <SectionHeader title="Visual Attention" />
      {visualOps.critical_count > 0 && (
        <InfoCard
          label="Critical"
          value={String(visualOps.critical_count)}
          color="#ef4444"
        />
      )}
      {visualOps.warning_count > 0 && (
        <InfoCard
          label="Warnings"
          value={String(visualOps.warning_count)}
          color="#eab308"
        />
      )}
      {visualOps.visual_signals.slice(0, 5).map((sig, i) => (
        <div
          key={i}
          style={{
            fontSize: 12,
            color: severityColor(sig.severity),
            paddingLeft: 8,
            borderLeft: `2px solid ${severityColor(sig.severity)}`,
            marginBottom: 4,
          }}
        >
          {sig.signal_type}: {sig.description || sig.detected_from || "—"}
        </div>
      ))}
    </div>
  );
}

function VisualHealthBar() {
  const visualOps = useScreenAwarenessStore((s) => s.visualOps);
  if (!visualOps) return null;

  const healthColor = (h: string) => {
    switch (h) {
      case "optimal":
        return "#22c55e";
      case "active":
        return "#3b82f6";
      case "degraded":
        return "#eab308";
      case "offline":
        return "#64748b";
      default:
        return "#64748b";
    }
  };

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        marginBottom: 12,
        padding: "6px 10px",
        background: "#0f172a",
        borderRadius: 6,
        border: "1px solid #1e293b",
      }}
    >
      <span
        style={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          background: healthColor(visualOps.health),
        }}
      />
      <span style={{ fontSize: 12, color: "#94a3b8" }}>Visual Brain</span>
      <span
        style={{
          fontSize: 12,
          color: healthColor(visualOps.health),
          fontWeight: 600,
        }}
      >
        {visualOps.health.toUpperCase()}
      </span>
      {visualOps.surface_count > 0 && (
        <span style={{ fontSize: 11, color: "#64748b", marginLeft: "auto" }}>
          {visualOps.surface_count} surface
          {visualOps.surface_count !== 1 ? "s" : ""}
        </span>
      )}
    </div>
  );
}

export default function ScreenAwarenessPanel() {
  const {
    fetchSnapshot,
    fetchVisualOps,
    fetchRepositories,
    fetchProviders,
    loading,
    error,
  } = useScreenAwarenessStore();

  useEffect(() => {
    fetchSnapshot();
    fetchVisualOps();
    fetchRepositories();
    fetchProviders();

    const interval = setInterval(() => {
      fetchSnapshot();
      fetchVisualOps();
      fetchProviders();
    }, 10_000);

    return () => clearInterval(interval);
  }, [fetchSnapshot, fetchVisualOps, fetchRepositories, fetchProviders]);

  return (
    <div style={{ padding: 16, color: "#e2e8f0", fontFamily: "monospace" }}>
      <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 4 }}>
        Screen Awareness
      </h2>
      <p style={{ fontSize: 12, color: "#64748b", marginBottom: 16 }}>
        Operator visual workspace context across nodes
      </p>
      <VisualHealthBar />
      {loading && (
        <div style={{ color: "#94a3b8", fontSize: 12 }}>—</div>
      )}
      {error && (
        <div style={{ color: "#ef4444", fontSize: 12 }}>Error: {error}</div>
      )}
      <VisualAttentionSection />
      <VisualContextSection />
      <SourceSection />
      <ApplicationSection />
      <RepositorySection />
      <FileSection />
      <BrowserSection />
      <ProvidersSection />
    </div>
  );
}
