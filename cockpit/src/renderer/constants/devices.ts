/**
 * Device Naming Protocol — single source of truth for all device labels.
 *
 * Format: tailscale-hostname (device-type)
 * Source: /infra/device_registry.json
 *
 * NEVER hardcode "VPS", "Beast", "Beast PC", "Windows", "Server", etc.
 * Import from here or read from the /workspace/mesh-nodes API.
 */

export interface DeviceInfo {
  id: string
  tailscaleName: string
  deviceType: string
  displayName: string
  os: 'linux' | 'windows'
  nodeParam?: string
}

export const DEVICES: Record<string, DeviceInfo> = {
  vps: {
    id: 'vps',
    tailscaleName: 'srv1500858',
    deviceType: 'vps',
    displayName: 'srv1500858 (VPS)',
    os: 'linux',
  },
  beast: {
    id: 'beast',
    tailscaleName: 'desktop-lvguiq9',
    deviceType: 'pc',
    displayName: 'desktop-lvguiq9 (PC)',
    os: 'windows',
    nodeParam: 'windows',
  },
} as const

export const VPS = DEVICES.vps
export const BEAST = DEVICES.beast

export function getDeviceDisplayName(nodeId: string): string {
  return DEVICES[nodeId]?.displayName ?? nodeId
}

export function isWindows(nodeParam?: string): boolean {
  return nodeParam === 'windows'
}
