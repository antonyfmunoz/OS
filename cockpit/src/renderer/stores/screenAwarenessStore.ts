import { create } from "zustand";

interface FocusedApplication {
  app_name: string;
  category: string;
  pid: number;
  window_title: string;
  is_focused: boolean;
  detected_at: number;
}

interface ActiveWindow {
  window_id: string;
  title: string;
  application: string;
  is_active: boolean;
  workspace_id: string;
  detected_at: number;
}

interface RepositoryContext {
  repo_name: string;
  repo_path: string;
  workspace_id: string;
  branch: string;
  head_commit: string;
  dirty_files: number;
  active_file: string;
  detected_at: number;
}

interface FileContext {
  file_path: string;
  file_name: string;
  repo_name: string;
  language: string;
  line_number: number;
  detected_at: number;
}

interface BrowserContext {
  url: string;
  title: string;
  domain: string;
  detected_at: number;
}

interface ScreenSnapshot {
  source_type: string;
  status: string;
  device_type: string;
  device_id: string;
  source_node_id: string;
  source_device_id: string;
  source_device_role: string;
  source_confidence: number;
  active_application: FocusedApplication | null;
  active_window: ActiveWindow | null;
  repository_context: RepositoryContext | null;
  file_context: FileContext | null;
  browser_context: BrowserContext | null;
  applications: FocusedApplication[];
  generated_at: number;
}

interface ProviderStatus {
  available: boolean;
  source_type: string;
  node_id: string;
  device_id: string;
  confidence: number;
  last_update?: number;
}

interface VisualContext {
  depth: string;
  application: string;
  repository: string;
  branch: string;
  file_path: string;
  campaign: string;
  goals: string[];
  confidence: number;
}

interface VisualSignal {
  signal_type: string;
  severity: string;
  description: string;
  detected_from: string;
}

interface VisualOperationsSnapshot {
  health: string;
  screen_state: Record<string, unknown>;
  environment: Record<string, unknown>;
  context_binding: VisualContext | null;
  visual_signals: VisualSignal[];
  capabilities: Record<string, boolean>;
  critical_count: number;
  warning_count: number;
  surface_count: number;
}

interface ScreenAwarenessStoreState {
  snapshot: ScreenSnapshot | null;
  visualOps: VisualOperationsSnapshot | null;
  repositories: RepositoryContext[];
  providers: Record<string, ProviderStatus> | null;
  loading: boolean;
  error: string | null;
  fetchSnapshot: () => Promise<void>;
  fetchVisualOps: () => Promise<void>;
  fetchRepositories: () => Promise<void>;
  fetchProviders: () => Promise<void>;
}

const API_BASE = "/api/umh/screen";
const VISUAL_API = "/api/umh/visual/operations";

export const useScreenAwarenessStore = create<ScreenAwarenessStoreState>(
  (set) => ({
    snapshot: null,
    visualOps: null,
    repositories: [],
    providers: null,
    loading: false,
    error: null,

    fetchSnapshot: async () => {
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

    fetchVisualOps: async () => {
      try {
        const res = await fetch(`${VISUAL_API}/snapshot`);
        if (!res.ok) return;
        const data = await res.json();
        set({ visualOps: data });
      } catch {
        /* silent — visual ops may not be available yet */
      }
    },

    fetchRepositories: async () => {
      try {
        const res = await fetch(`${API_BASE}/repositories`);
        if (!res.ok) return;
        const data = await res.json();
        set({ repositories: data.repositories || [] });
      } catch {
        /* silent */
      }
    },

    fetchProviders: async () => {
      try {
        const res = await fetch(`${API_BASE}/providers`);
        if (!res.ok) return;
        const data = await res.json();
        set({ providers: data });
      } catch {
        /* silent */
      }
    },
  }),
);
