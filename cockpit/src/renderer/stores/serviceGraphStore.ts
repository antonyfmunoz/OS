import { create } from 'zustand';
import { fetchApi } from '../api/client';

interface ServiceNode {
  service_role: string;
  description: string;
  criticality: string;
  owner_node: string;
  state_domains: string[];
}

interface FailureImpact {
  failed_service: string;
  directly_affected: string[];
  transitively_affected: string[];
  affected_state_domains: string[];
  blast_radius: number;
  severity: string;
}

interface CriticalPathEntry {
  service_role: string;
  criticality: string;
  blast_radius: number;
  direct_dependents: number;
  transitive_dependents: number;
}

interface ServiceGraphState {
  services: ServiceNode[];
  impact: FailureImpact | null;
  criticalPath: CriticalPathEntry[];
  loading: boolean;
  error: string | null;
  fetchServices: () => Promise<void>;
  fetchImpact: (serviceRole: string) => Promise<void>;
  fetchCriticalPath: () => Promise<void>;
}

export const useServiceGraphStore = create<ServiceGraphState>((set) => ({
  services: [],
  impact: null,
  criticalPath: [],
  loading: false,
  error: null,

  fetchServices: async () => {
    set({ loading: true, error: null });
    try {
      const data = await fetchApi<{ services?: ServiceNode[] }>('/service-graph/services');
      set({ services: data.services || [], loading: false });
    } catch (err) {
      set({ error: String(err), loading: false });
    }
  },

  fetchImpact: async (serviceRole: string) => {
    set({ loading: true, error: null });
    try {
      const data = await fetchApi<FailureImpact>(`/service-graph/impact/${serviceRole}`);
      set({ impact: data, loading: false });
    } catch (err) {
      set({ error: String(err), loading: false });
    }
  },

  fetchCriticalPath: async () => {
    set({ loading: true, error: null });
    try {
      const data = await fetchApi<{ services?: CriticalPathEntry[] }>('/service-graph/critical-path');
      set({ criticalPath: data.services || [], loading: false });
    } catch (err) {
      set({ error: String(err), loading: false });
    }
  },
}));
