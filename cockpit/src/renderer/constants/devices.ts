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
  os: 'linux' | 'windows' | 'ios' | 'macos'
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
  ipad: {
    id: 'ipad',
    tailscaleName: 'ipad-pro-12-9-gen-5',
    deviceType: 'tablet',
    displayName: 'ipad-pro-12-9-gen-5 (Tablet)',
    os: 'ios',
  },
  iphone: {
    id: 'iphone',
    tailscaleName: 'iphone-15-pro-max',
    deviceType: 'mobile',
    displayName: 'iphone-15-pro-max (Mobile)',
    os: 'ios',
  },
  macbook: {
    id: 'macbook',
    tailscaleName: 'antonys-macbook-pro',
    deviceType: 'laptop',
    displayName: 'antonys-macbook-pro (Laptop)',
    os: 'macos',
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
