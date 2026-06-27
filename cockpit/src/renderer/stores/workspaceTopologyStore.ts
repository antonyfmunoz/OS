/**
 * Workspace Topology Store — Phase 27
 *
 * Read-only topology data: workspaces, health, runtimes, repositories.
 */

import { create } from 'zustand';
import { fetchApi } from '../api/client';

interface WorkspaceTopology {
  graph_id: string;
  workspaces: WorkspaceEntry[];
  workspace_count: number;
  generated_at: number;
}

interface WorkspaceEntry {
  workspace_id: string;
  name: string;
  workspace_type: string;
  repositories: Repository[];
  runtimes: Runtime[];
  build_targets: BuildTarget[];
  device_ids: string[];
  health: string;
}

interface Repository {
  repository_id: string;
  name: string;
  path: string;
  branch: string;
  workspace_id: string;
}

interface Runtime {
  runtime_id: string;
  workspace_id: string;
  runtime_type: string;
  host_device_id: string;
  ports: number[];
  status: string;
}

interface BuildTarget {
  target_id: string;
  workspace_id: string;
  build_type: string;
  device_id: string;
  preferred: boolean;
}

interface WorkspaceTopologyState {
  topology: WorkspaceTopology | null;
  loading: boolean;
  error: string | null;
  fetchTopology: () => Promise<void>;
  fetchWorkspace: (id: string) => Promise<WorkspaceEntry | null>;
}

export const useWorkspaceTopologyStore = create<WorkspaceTopologyState>((set) => ({
  topology: null,
  loading: false,
  error: null,

  fetchTopology: async () => {
    set({ loading: true, error: null });
    try {
      const data = await fetchApi<WorkspaceTopology>('/workspace-topology');
      set({ topology: data, loading: false });
    } catch (err) {
      set({ error: String(err), loading: false });
    }
  },

  fetchWorkspace: async (id: string) => {
    try {
      return await fetchApi<WorkspaceEntry>(`/workspace-topology/${id}`);
    } catch {
      return null;
    }
  },
}));

export type { WorkspaceTopology, WorkspaceEntry, Repository, Runtime, BuildTarget };
