import { create } from 'zustand';
import { fetchApi } from '../api/client';

interface UMHNodeService {
  service_id: string;
  node_id: string;
  service_role: string;
  active: boolean;
  status: string;
  endpoint: string;
  health: string;
}

interface UMHNodeVersion {
  umh_version: string;
  git_commit: string;
  branch: string;
  schema_version: string;
  migration_version: string;
  build_timestamp: number;
}

interface UMHNode {
  node_id: string;
  device_id: string;
  hostname: string;
  purpose: string;
  roles: string[];
  status: string;
  version: UMHNodeVersion;
  active_services: UMHNodeService[];
  capability_ids: string[];
  workspace_ids: string[];
  primary: boolean;
  last_seen: number;
}

interface UMHNodeTopology {
  topology_id: string;
  organism_id: string;
  nodes: UMHNode[];
  node_count: number;
  generated_at: number;
  version_status: string;
  canonical_version: UMHNodeVersion | null;
}

interface UMHNodeState {
  topology: UMHNodeTopology | null;
  versionStatus: string;
  loading: boolean;
  error: string | null;
  fetchTopology: () => Promise<void>;
  fetchVersionStatus: () => Promise<void>;
}

export const useUMHNodeStore = create<UMHNodeState>((set) => ({
  topology: null,
  versionStatus: 'unknown',
  loading: false,
  error: null,

  fetchTopology: async () => {
    set({ loading: true, error: null });
    try {
      const data = await fetchApi<UMHNodeTopology>('/umh-nodes');
      set({ topology: data, loading: false });
    } catch (err) {
      set({ error: String(err), loading: false });
    }
  },

  fetchVersionStatus: async () => {
    try {
      const data = await fetchApi<{ status: string }>('/umh-nodes/version/status');
      set({ versionStatus: data.status });
    } catch (err) {
      set({ error: String(err) });
    }
  },
}));
