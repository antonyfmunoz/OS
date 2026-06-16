import { create } from "zustand";

interface PresenceState {
  operator_state: string;
  device_type: string;
  device_id: string;
  node_id: string;
  updated_at: number;
}

interface ActiveContext {
  workspace_id: string;
  workspace_name: string;
  session_id: string;
  session_type: string;
  runtime_id: string;
  work_packet_id: string;
  description: string;
}

interface ContinuityCheckpoint {
  checkpoint_id: string;
  checkpoint_type: string;
  title: string;
  detail: string;
  device_type: string;
  status: string;
  created_at: number;
}

interface PresenceSnapshot {
  operator_state: string;
  active_device: string;
  active_device_id: string;
  active_node_id: string;
  active_context: ActiveContext;
  continuity_checkpoints: ContinuityCheckpoint[];
  generated_at: number;
}

interface PresenceTransition {
  transition_id: string;
  transition_type: string;
  from_value: string;
  to_value: string;
  device_type: string;
  detail: string;
  timestamp: number;
}

interface ResumeSuggestion {
  device: string;
  node: string;
  state: string;
  workspace?: string;
  session?: { id: string; type: string };
  resume_items?: Array<{
    type: string;
    title: string;
    detail: string;
    status: string;
  }>;
  pending_approvals: number;
}

interface PresenceStoreState {
  snapshot: PresenceSnapshot | null;
  timeline: PresenceTransition[];
  resume: ResumeSuggestion | null;
  loading: boolean;
  error: string | null;
  fetchPresence: () => Promise<void>;
  fetchTimeline: () => Promise<void>;
  fetchResume: () => Promise<void>;
}

const API_BASE = "/api/umh/presence";

export const usePresenceStore = create<PresenceStoreState>((set) => ({
  snapshot: null,
  timeline: [],
  resume: null,
  loading: false,
  error: null,

  fetchPresence: async () => {
    set({ loading: true, error: null });
    try {
      const res = await fetch(API_BASE);
      if (!res.ok) throw new Error(`${res.status}`);
      const data = await res.json();
      set({ snapshot: data, loading: false });
    } catch (e) {
      set({ error: String(e), loading: false });
    }
  },

  fetchTimeline: async () => {
    try {
      const res = await fetch(`${API_BASE}/timeline`);
      if (!res.ok) throw new Error(`${res.status}`);
      const data = await res.json();
      set({ timeline: data.transitions || [] });
    } catch (e) {
      set({ error: String(e) });
    }
  },

  fetchResume: async () => {
    try {
      const res = await fetch(`${API_BASE}/resume`);
      if (!res.ok) throw new Error(`${res.status}`);
      const data = await res.json();
      set({ resume: data });
    } catch (e) {
      set({ error: String(e) });
    }
  },
}));
