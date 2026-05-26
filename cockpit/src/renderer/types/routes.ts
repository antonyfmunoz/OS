import type { LucideIcon } from 'lucide-react'
import {
  LayoutDashboard,
  Bot,
  ListChecks,
  ShieldCheck,
  Activity,
  BookOpen,
  BarChart3,
  Code2,
  Settings,
  Layers,
  Briefcase,
  Building2,
} from 'lucide-react'
import type { Panel } from '../stores/cockpitStore'

export interface RouteEntry {
  id: Panel
  label: string
  icon: LucideIcon
  group: 'core' | 'operations' | 'intelligence' | 'system'
  key: string
}

export const ROUTES: RouteEntry[] = [
  { id: 'dashboard', label: 'Command Center', icon: LayoutDashboard, group: 'core', key: '1' },
  { id: 'agents', label: 'Agents', icon: Bot, group: 'core', key: '2' },
  { id: 'tasks', label: 'Tasks', icon: ListChecks, group: 'core', key: '3' },
  { id: 'activity', label: 'Activity', icon: Activity, group: 'core', key: '9' },
  { id: 'approvals', label: 'Approvals', icon: ShieldCheck, group: 'operations', key: '4' },
  { id: 'execution', label: 'Execution', icon: Layers, group: 'operations', key: '0' },
  { id: 'portfolio', label: 'Portfolio', icon: Briefcase, group: 'operations', key: 'p' },
  { id: 'company', label: 'Company', icon: Building2, group: 'operations', key: 'c' },
  { id: 'knowledge', label: 'Knowledge', icon: BookOpen, group: 'intelligence', key: '5' },
  { id: 'analytics', label: 'Analytics', icon: BarChart3, group: 'intelligence', key: '6' },
  { id: 'editor', label: 'IDE', icon: Code2, group: 'intelligence', key: '7' },
  { id: 'settings', label: 'Settings', icon: Settings, group: 'system', key: '8' },
]

export const ROUTE_GROUPS = [
  { key: 'core' as const, label: 'CORE' },
  { key: 'operations' as const, label: 'OPERATIONS' },
  { key: 'intelligence' as const, label: 'INTELLIGENCE' },
  { key: 'system' as const, label: 'SYSTEM' },
]
