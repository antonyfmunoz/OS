import type { LucideIcon } from 'lucide-react'
import {
  LayoutDashboard,
  Bot,
  ListChecks,
  Activity,
  MessageSquare,
  ShieldCheck,
  Workflow,
  Eye,
  Crosshair,
  Factory,
  Layers,
  BookOpen,
  BarChart3,
  FlaskConical,
  Wrench,
  Server,
  User,
  Settings,
} from 'lucide-react'

export type RouteId =
  | 'command-center'
  | 'agents'
  | 'tasks'
  | 'activity'
  | 'comms'
  | 'approvals'
  | 'workflows'
  | 'awareness'
  | 'tracking'
  | 'production'
  | 'context'
  | 'knowledge'
  | 'analytics'
  | 'experiments'
  | 'skills'
  | 'infrastructure'
  | 'profile'
  | 'settings'

export interface RouteEntry {
  id: RouteId
  label: string
  icon: LucideIcon
  group: 'core' | 'operations' | 'intelligence' | 'system'
}

export const ROUTES: RouteEntry[] = [
  { id: 'command-center', label: 'Command Center', icon: LayoutDashboard, group: 'core' },
  { id: 'agents', label: 'Agents', icon: Bot, group: 'core' },
  { id: 'tasks', label: 'Tasks', icon: ListChecks, group: 'core' },
  { id: 'activity', label: 'Activity', icon: Activity, group: 'core' },
  { id: 'comms', label: 'Comms', icon: MessageSquare, group: 'core' },
  { id: 'approvals', label: 'Approvals', icon: ShieldCheck, group: 'operations' },
  { id: 'workflows', label: 'Workflows', icon: Workflow, group: 'operations' },
  { id: 'awareness', label: 'Awareness', icon: Eye, group: 'operations' },
  { id: 'tracking', label: 'Tracking', icon: Crosshair, group: 'operations' },
  { id: 'production', label: 'Production', icon: Factory, group: 'operations' },
  { id: 'context', label: 'Context', icon: Layers, group: 'intelligence' },
  { id: 'knowledge', label: 'Knowledge', icon: BookOpen, group: 'intelligence' },
  { id: 'analytics', label: 'Analytics', icon: BarChart3, group: 'intelligence' },
  { id: 'experiments', label: 'Experiments', icon: FlaskConical, group: 'intelligence' },
  { id: 'skills', label: 'Skills', icon: Wrench, group: 'intelligence' },
  { id: 'infrastructure', label: 'Infrastructure', icon: Server, group: 'system' },
  { id: 'profile', label: 'Profile', icon: User, group: 'system' },
  { id: 'settings', label: 'Settings', icon: Settings, group: 'system' },
]

export const ROUTE_GROUPS = [
  { key: 'core' as const, label: 'CORE' },
  { key: 'operations' as const, label: 'OPERATIONS' },
  { key: 'intelligence' as const, label: 'INTELLIGENCE' },
  { key: 'system' as const, label: 'SYSTEM' },
]
