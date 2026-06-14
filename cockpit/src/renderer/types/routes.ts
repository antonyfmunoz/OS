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
  FlaskConical,
  Server,
  User,
  Brain,
  Lightbulb,
  Globe,
  Hammer,
  Mic,
  Play,
  Terminal,
  Camera,
  Radio,
  Cast,
  Crosshair,
  TrendingUp,
  RefreshCw,
  Eye,
  Zap,
  Monitor,
  MonitorSmartphone,
  Cog,
} from 'lucide-react'
import type { Panel } from '../stores/cockpitStore'

export interface RouteEntry {
  id: Panel
  label: string
  icon: LucideIcon
  group: 'primary' | 'system'
  visibility: 'primary' | 'system' | 'dev' | 'planned' | 'stub'
  key: string
}

export const ROUTES: RouteEntry[] = [
  // Primary (10)
  { id: 'commandcenter', label: 'Command Center', icon: Target, group: 'primary', visibility: 'primary', key: 'q' },
  { id: 'work', label: 'Work', icon: ListChecks, group: 'primary', visibility: 'primary', key: '3' },
  { id: 'agents', label: 'Agents', icon: Bot, group: 'primary', visibility: 'primary', key: '2' },
  { id: 'approvals', label: 'Approvals', icon: ShieldCheck, group: 'primary', visibility: 'primary', key: '4' },
  { id: 'activity', label: 'Activity', icon: Activity, group: 'primary', visibility: 'primary', key: '9' },
  { id: 'editor', label: 'Meta IDE', icon: Code2, group: 'primary', visibility: 'primary', key: '7' },
  { id: 'execution', label: 'Execution', icon: Layers, group: 'primary', visibility: 'primary', key: '0' },
  { id: 'infrastructure', label: 'Infrastructure', icon: Server, group: 'primary', visibility: 'primary', key: 'i' },
  { id: 'rooms', label: 'Conference Rooms', icon: Radio, group: 'primary', visibility: 'primary', key: 'j' },
  { id: 'comms', label: 'Comms', icon: MessageSquare, group: 'primary', visibility: 'primary', key: 'm' },
  { id: 'vision', label: 'Vision', icon: Camera, group: 'primary', visibility: 'primary', key: 'v' },
  { id: 'broadcast', label: 'Broadcast', icon: Cast, group: 'primary', visibility: 'primary', key: 'b' },
  { id: 'strategy', label: 'Strategy', icon: Crosshair, group: 'primary', visibility: 'primary', key: 's' },
  { id: 'tickloop', label: 'Tick Loop', icon: Activity, group: 'primary', visibility: 'primary', key: 'l' },
  { id: 'projections', label: 'Projections', icon: TrendingUp, group: 'primary', visibility: 'primary', key: 'f' },
  { id: 'continuity', label: 'Continuity', icon: RefreshCw, group: 'primary', visibility: 'primary', key: 'y' },
  { id: 'presence', label: 'Presence', icon: Eye, group: 'primary', visibility: 'primary', key: 'e' },
  { id: 'commands', label: 'Commands', icon: Zap, group: 'primary', visibility: 'primary', key: 'z' },
  { id: 'workstation', label: 'Workstation', icon: Monitor, group: 'primary', visibility: 'primary', key: 'k' },
  { id: 'knowledge', label: 'Knowledge', icon: BookOpen, group: 'primary', visibility: 'primary', key: '5' },

  // System (1)
  { id: 'settings', label: 'Settings', icon: Settings, group: 'system', visibility: 'system', key: '8' },

  // Dev (searchable with [DEV] badge)
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, group: 'primary', visibility: 'dev', key: '1' },
  { id: 'organism', label: 'Organism', icon: Brain, group: 'primary', visibility: 'dev', key: 'o' },
  { id: 'intelligence', label: 'Intelligence', icon: Lightbulb, group: 'primary', visibility: 'dev', key: 'n' },
  { id: 'propagation', label: 'Propagation', icon: Workflow, group: 'primary', visibility: 'dev', key: 'g' },
  { id: 'operator', label: 'Operator', icon: Mic, group: 'primary', visibility: 'dev', key: 'd' },
  { id: 'tmux', label: 'Tmux', icon: Terminal, group: 'primary', visibility: 'dev', key: 't' },
  { id: 'runtime', label: 'Runtime', icon: Play, group: 'primary', visibility: 'dev', key: 'r' },
  { id: 'selfbuild', label: 'Self-Build', icon: Hammer, group: 'primary', visibility: 'dev', key: 'b' },
  { id: 'universalwork', label: 'Universal Work', icon: Layers, group: 'primary', visibility: 'dev', key: 'w' },
  { id: 'worldmodel', label: 'World Model', icon: Globe, group: 'primary', visibility: 'dev', key: 'g' },
  { id: 'portfolio', label: 'Portfolio', icon: Briefcase, group: 'primary', visibility: 'dev', key: 'p' },
  { id: 'company', label: 'Company', icon: Building2, group: 'primary', visibility: 'dev', key: 'c' },

  // Planned (searchable with [PLANNED] badge)
  { id: 'analytics', label: 'Analytics', icon: BarChart3, group: 'primary', visibility: 'planned', key: '6' },

  // Stub (NOT searchable)
  { id: 'tracking', label: 'Tracking', icon: Target, group: 'primary', visibility: 'stub', key: 't' },
  { id: 'experiments', label: 'Experiments', icon: FlaskConical, group: 'primary', visibility: 'stub', key: 'x' },
  { id: 'sessions', label: 'Sessions', icon: MonitorSmartphone, group: 'primary', visibility: 'primary', key: 'n' },
  { id: 'execcoord', label: 'Exec Coordinator', icon: Cog, group: 'primary', visibility: 'primary', key: 'h' },
  { id: 'profile', label: 'Profile', icon: User, group: 'primary', visibility: 'primary', key: 'u' },
]

export const ROUTE_GROUPS = [
  { key: 'primary' as const, label: 'PRIMARY' },
  { key: 'system' as const, label: 'SYSTEM' },
]
