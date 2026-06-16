import { create } from 'zustand';

interface StatusCard {
  label: string;
  value: number | string;
  status: string;
  detail: string;
}

interface HealthSummary {
  overall_status: string;
  cards: StatusCard[];
  generated_at: number;
}

interface AttentionItem {
  attention_id: string;
  attention_type: string;
  severity: string;
  title: string;
  detail: string;
  source: string;
  timestamp: number;
}

interface TimelineEvent {
  event_id: string;
  domain: string;
  event_type: string;
  source: string;
  summary: string;
  timestamp: number;
  priority: string;
}

interface OperatorSnapshot {
  health_summary: HealthSummary;
  attention_items: AttentionItem[];
  active_workspaces: Record<string, unknown>[];
  pending_approvals: number;
  service_alerts: Record<string, unknown>[];
  node_status: Record<string, unknown>[];
  timeline: TimelineEvent[];
  generated_at: number;
}

interface OperatorHomeState {
  snapshot: OperatorSnapshot | null;
  attention: AttentionItem[];
  timeline: TimelineEvent[];
  loading: boolean;
  error: string | null;
  fetchHome: () => Promise<void>;
  fetchAttention: () => Promise<void>;
  fetchTimeline: () => Promise<void>;
}

export const useOperatorHomeStore = create<OperatorHomeState>((set) => ({
  snapshot: null,
  attention: [],
  timeline: [],
  loading: false,
  error: null,

  fetchHome: async () => {
    set({ loading: true, error: null });
    try {
      const resp = await fetch('/api/umh/operator/home');
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      set({
        snapshot: data,
        attention: data.attention_items || [],
        timeline: data.timeline || [],
        loading: false,
      });
    } catch (err) {
      set({ error: String(err), loading: false });
    }
  },

  fetchAttention: async () => {
    set({ loading: true, error: null });
    try {
      const resp = await fetch('/api/umh/operator/attention');
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      set({ attention: data.items || [], loading: false });
    } catch (err) {
      set({ error: String(err), loading: false });
    }
  },

  fetchTimeline: async () => {
    set({ loading: true, error: null });
    try {
      const resp = await fetch('/api/umh/operator/timeline');
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      set({ timeline: data.events || [], loading: false });
    } catch (err) {
      set({ error: String(err), loading: false });
    }
  },
}));
