import { create } from 'zustand';
import { fetchApi } from '../api/client';

interface StateAuthority {
  domain: string;
  node_id: string;
  authority_level: string;
  storage_location: string;
  service_owner: string;
}

interface DomainCoherenceReport {
  domain: string;
  authority_node: string;
  status: string;
  storage_location: string;
  service_owner: string;
  last_updated: number;
}

interface CoherenceReport {
  overall_health: string;
  domain_count: number;
  domains: DomainCoherenceReport[];
}

interface StateAuthorityState {
  domains: StateAuthority[];
  coherence: CoherenceReport | null;
  loading: boolean;
  error: string | null;
  fetchDomains: () => Promise<void>;
  fetchCoherence: () => Promise<void>;
}

export const useStateAuthorityStore = create<StateAuthorityState>((set) => ({
  domains: [],
  coherence: null,
  loading: false,
  error: null,

  fetchDomains: async () => {
    set({ loading: true, error: null });
    try {
      const data = await fetchApi<{ domains?: StateAuthority[] }>('/state-authority/domains');
      set({ domains: data.domains || [], loading: false });
    } catch (err) {
      set({ error: String(err), loading: false });
    }
  },

  fetchCoherence: async () => {
    set({ loading: true, error: null });
    try {
      const data = await fetchApi<CoherenceReport>('/state-authority/coherence');
      set({ coherence: data, loading: false });
    } catch (err) {
      set({ error: String(err), loading: false });
    }
  },
}));
