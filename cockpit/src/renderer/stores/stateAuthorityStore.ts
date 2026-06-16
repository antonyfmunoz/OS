import { create } from 'zustand';

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
      const resp = await fetch('/api/umh/state-authority/domains');
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      set({ domains: data.domains || [], loading: false });
    } catch (err) {
      set({ error: String(err), loading: false });
    }
  },

  fetchCoherence: async () => {
    set({ loading: true, error: null });
    try {
      const resp = await fetch('/api/umh/state-authority/coherence');
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      set({ coherence: data, loading: false });
    } catch (err) {
      set({ error: String(err), loading: false });
    }
  },
}));
