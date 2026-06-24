import { create } from 'zustand'
import { fetchApi } from '../api/client'

export interface RegisteredDevice {
  id: string
  tailscale_name: string
  device_type: string
  display_name: string
  os: string
  role: string
  tailscale_ip?: string
  compute?: boolean
  always_online?: boolean
  mesh_node_id?: string
  gpu?: string
  vram_mb?: number
  ram_mb?: number
}

export interface TailscalePeer {
  hostname: string
  dns_name: string
  os: string
  tailscale_ips: string[]
  online: boolean
  registered: boolean
}

export interface DeviceDiagnosis {
  hostname: string
  dns_name: string
  os: string
  cpu_cores: number
  ram_mb: number
  gpu: string
  vram_mb: number
  disk_gb: number
  ssh_reachable: boolean
  recommended_role: string
  recommended_type: string
  confidence: string
  tailscale_ip?: string
}

export interface ScanResult {
  peers: TailscalePeer[]
  total: number
  unregistered: number
}

interface DeviceState {
  devices: RegisteredDevice[]
  scanResult: ScanResult | null
  scanning: boolean
  provisioning: string | null

  fetchDevices: () => Promise<void>
  scanPeers: () => Promise<void>
  diagnoseDevice: (hostname: string, tailscale_ip: string, os?: string, dns_name?: string) => Promise<DeviceDiagnosis | null>
  registerDevice: (entry: Partial<RegisteredDevice>) => Promise<boolean>
  removeDevice: (deviceId: string) => Promise<boolean>
  provisionDevice: (deviceId: string, role?: string) => Promise<boolean>
  inviteDevice: (opts?: { reusable?: boolean; ephemeral?: boolean; preauthorized?: boolean; expiry_seconds?: number }) => Promise<string | null>
}

export const useDeviceStore = create<DeviceState>((set, get) => ({
  devices: [],
  scanResult: null,
  scanning: false,
  provisioning: null,

  fetchDevices: async () => {
    try {
      const data = await fetchApi<RegisteredDevice[]>('/devices/list')
      set({ devices: data })
    } catch {
      set({ devices: [] })
    }
  },

  scanPeers: async () => {
    set({ scanning: true })
    try {
      const data = await fetchApi<ScanResult>('/devices/scan')
      set({ scanResult: data, scanning: false })
    } catch {
      set({ scanResult: null, scanning: false })
    }
  },

  diagnoseDevice: async (hostname, tailscale_ip, os, dns_name) => {
    try {
      const resp = await fetchApi<{ success: boolean; diagnosis?: DeviceDiagnosis; error?: string }>('/devices/diagnose', {
        method: 'POST',
        body: JSON.stringify({ hostname, tailscale_ip, os, dns_name }),
      })
      return resp.success ? (resp.diagnosis ?? null) : null
    } catch {
      return null
    }
  },

  registerDevice: async (entry) => {
    try {
      const resp = await fetchApi<{ success: boolean }>('/devices/register', {
        method: 'POST',
        body: JSON.stringify({ entry }),
      })
      if (resp.success) get().fetchDevices()
      return resp.success
    } catch {
      return false
    }
  },

  removeDevice: async (deviceId) => {
    try {
      const resp = await fetchApi<{ success: boolean }>('/devices/remove', {
        method: 'POST',
        body: JSON.stringify({ device_id: deviceId }),
      })
      if (resp.success) get().fetchDevices()
      return resp.success
    } catch {
      return false
    }
  },

  provisionDevice: async (deviceId, role) => {
    set({ provisioning: deviceId })
    try {
      const resp = await fetchApi<{ success: boolean }>('/devices/provision', {
        method: 'POST',
        body: JSON.stringify({ device_id: deviceId, role }),
      })
      set({ provisioning: null })
      return resp.success
    } catch {
      set({ provisioning: null })
      return false
    }
  },

  inviteDevice: async (opts) => {
    try {
      const resp = await fetchApi<{ success: boolean; auth_key?: { key: string } }>('/devices/invite', {
        method: 'POST',
        body: JSON.stringify(opts ?? {}),
      })
      return resp.success ? (resp.auth_key?.key ?? null) : null
    } catch {
      return null
    }
  },
}))
