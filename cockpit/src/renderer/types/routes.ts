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
  MessageSquare,
  Workflow,
  Target,
  Wrench,
  FlaskConical,
  Server,
  User,
  Brain,
  Lightbulb,
  Globe,
  Hammer,
  Mic,
  Play,
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
  { id: 'operator', label: 'Operator', icon: Mic, group: 'core', key: 'd' },
  { id: 'dashboard', label: 'Command Center', icon: LayoutDashboard, group: 'core', key: '1' },
  { id: 'agents', label: 'Agents', icon: Bot, group: 'core', key: '2' },
  { id: 'tasks', label: 'Tasks', icon: ListChecks, group: 'core', key: '3' },
  { id: 'workflows', label: 'Workflows', icon: Workflow, group: 'core', key: 'w' },
  { id: 'activity', label: 'Activity', icon: Activity, group: 'core', key: '9' },
  { id: 'approvals', label: 'Approvals', icon: ShieldCheck, group: 'operations', key: '4' },
  { id: 'organism', label: 'Organism', icon: Brain, group: 'operations', key: 'o' },
  { id: 'runtime', label: 'Runtime', icon: Play, group: 'operations', key: 'r' },
  { id: 'execution', label: 'Execution', icon: Layers, group: 'operations', key: '0' },
  { id: 'tracking', label: 'Tracking', icon: Target, group: 'operations', key: 't' },
  { id: 'infrastructure', label: 'Infrastructure', icon: Server, group: 'operations', key: 'i' },
  { id: 'portfolio', label: 'Portfolio', icon: Briefcase, group: 'operations', key: 'p' },
  { id: 'company', label: 'Company', icon: Building2, group: 'operations', key: 'c' },
  { id: 'worldmodel', label: 'World Model', icon: Globe, group: 'operations', key: 'g' },
  { id: 'selfbuild', label: 'Self-Build', icon: Hammer, group: 'operations', key: 'b' },
  { id: 'universalwork', label: 'Universal Work', icon: Layers, group: 'operations', key: 'w' },
  { id: 'intelligence', label: 'Intelligence', icon: Lightbulb, group: 'intelligence', key: 'n' },
  { id: 'knowledge', label: 'Knowledge', icon: BookOpen, group: 'intelligence', key: '5' },
  { id: 'analytics', label: 'Analytics', icon: BarChart3, group: 'intelligence', key: '6' },
  { id: 'skills', label: 'Skills', icon: Wrench, group: 'intelligence', key: 'k' },
  { id: 'editor', label: 'IDE', icon: Code2, group: 'intelligence', key: '7' },
  { id: 'experiments', label: 'Experiments', icon: FlaskConical, group: 'intelligence', key: 'x' },
  { id: 'comms', label: 'Messages', icon: MessageSquare, group: 'system', key: 'm' },
  { id: 'profile', label: 'Profile', icon: User, group: 'system', key: 'u' },
  { id: 'settings', label: 'Settings', icon: Settings, group: 'system', key: '8' },
]

export const ROUTE_GROUPS = [
  { key: 'core' as const, label: 'CORE' },
  { key: 'operations' as const, label: 'OPERATIONS' },
  { key: 'intelligence' as const, label: 'INTELLIGENCE' },
  { key: 'system' as const, label: 'SYSTEM' },
]
