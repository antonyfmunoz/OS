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
  RotateCcw,
  Wrench,
  FileText,
  Map,
  Merge,
  Puzzle,
  CheckCircle2,
  Compass,
  Home,
  Network,
  GitBranch,
  Shield,
  MonitorDot,
  LayoutPanelTop,
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
  // ── 6 Primary Nav Items (in display order) ──────────────────────
  { id: 'commandcenter', label: 'Command Center', icon: Target, group: 'primary', visibility: 'primary', key: 'q' },
  { id: 'canvas', label: 'Canvas', icon: LayoutPanelTop, group: 'primary', visibility: 'primary', key: '`' },
  { id: 'work', label: 'Work', icon: ListChecks, group: 'primary', visibility: 'primary', key: '3' },
  { id: 'editor', label: 'Meta IDE', icon: Code2, group: 'primary', visibility: 'primary', key: '7' },
  { id: 'rooms', label: 'Conference Rooms', icon: Radio, group: 'primary', visibility: 'primary', key: 'j' },
  { id: 'vision', label: 'Vision', icon: Camera, group: 'primary', visibility: 'primary', key: 'v' },

  // ── Demoted from nav → accessible via CommandPalette + Canvas Instruments ──
  { id: 'approvals', label: 'Approvals', icon: ShieldCheck, group: 'primary', visibility: 'dev', key: '4' },
  { id: 'activity', label: 'Activity', icon: Activity, group: 'primary', visibility: 'dev', key: '9' },
  { id: 'execution', label: 'Execution', icon: Layers, group: 'primary', visibility: 'dev', key: '0' },
  { id: 'organismmap', label: 'Organism Map', icon: Brain, group: 'primary', visibility: 'dev', key: 'i' },
  { id: 'broadcast', label: 'Broadcast', icon: Cast, group: 'primary', visibility: 'dev', key: 'b' },
  { id: 'knowledge', label: 'Knowledge', icon: BookOpen, group: 'primary', visibility: 'dev', key: '5' },
  { id: 'browser', label: 'Browser', icon: Globe, group: 'primary', visibility: 'dev', key: '6' },

  // System (1)
  { id: 'settings', label: 'Settings', icon: Settings, group: 'system', visibility: 'system', key: '8' },

  // ── Dev (searchable with [DEV] badge) ────────────────────────────
  // Campaign 3 — Cockpit Convergence & Projection Integration
  { id: 'capabilitymap', label: 'Capability Map', icon: Map, group: 'primary', visibility: 'dev', key: 'C' },
  { id: 'unifiedexecution', label: 'Unified Execution', icon: Merge, group: 'primary', visibility: 'dev', key: 'U' },
  { id: 'buildloop', label: 'Build Loop', icon: Hammer, group: 'primary', visibility: 'dev', key: 'L' },
  { id: 'projectionintegration', label: 'Projection Integration', icon: Puzzle, group: 'primary', visibility: 'dev', key: 'P' },
  // P4S-30 — LyfeOS + CreatorOS projection mirror panels (read-surface only)
  { id: 'projectionmirrors', label: 'Projection Mirrors', icon: Network, group: 'primary', visibility: 'dev', key: 'X' },
  // P4S-31 — MVP operating-loop mirror (intent -> draft -> governed proof, read-only)
  { id: 'intentloop', label: 'Intent Loop', icon: GitBranch, group: 'primary', visibility: 'dev', key: 'A' },
  // MVP Wave 1 — Objective plans (versioned work-graph plan records, chat-originated)
  { id: 'objectiveplan', label: 'Objective Plans', icon: Workflow, group: 'primary', visibility: 'dev', key: 'A' },
  // Campaign 4 — Operator-Orchestrator Convergence
  { id: 'orchestratorawareness', label: 'Orchestrator', icon: Brain, group: 'primary', visibility: 'dev', key: 'a' },
  { id: 'operatingloopview', label: 'Operating Loop', icon: RotateCcw, group: 'primary', visibility: 'dev', key: 'D' },
  { id: 'sessionresume', label: 'Session Resume', icon: MonitorSmartphone, group: 'primary', visibility: 'dev', key: 'S' },
  { id: 'mvpreadiness', label: 'MVP Readiness', icon: CheckCircle2, group: 'primary', visibility: 'dev', key: 'V' },
  // Campaign 4.7 — Cockpit Delegation
  { id: 'delegation', label: 'Delegation', icon: Workflow, group: 'primary', visibility: 'dev', key: 'Y' },
  // Campaign 19 — Execution Fabric & Agent Operations
  { id: 'operations', label: 'Operations', icon: Monitor, group: 'primary', visibility: 'dev', key: 'Z' },
  // Gate 4: Intent Runtime (access via Command Center, dev-visible for direct debugging)
  { id: 'intent', label: 'Intent', icon: FileText, group: 'primary', visibility: 'dev', key: 'F' },
  // Absorbed into Command Center
  { id: 'strategy', label: 'Strategy', icon: Crosshair, group: 'primary', visibility: 'dev', key: 's' },
  { id: 'tickloop', label: 'Tick Loop', icon: Activity, group: 'primary', visibility: 'dev', key: 'l' },
  { id: 'projections', label: 'Projections', icon: TrendingUp, group: 'primary', visibility: 'dev', key: 'f' },
  { id: 'continuity', label: 'Continuity', icon: RefreshCw, group: 'primary', visibility: 'dev', key: 'y' },
  { id: 'presence', label: 'Presence', icon: Eye, group: 'primary', visibility: 'dev', key: 'e' },
  { id: 'commands', label: 'Commands', icon: Zap, group: 'primary', visibility: 'dev', key: 'z' },
  { id: 'comms', label: 'Comms', icon: MessageSquare, group: 'primary', visibility: 'dev', key: 'm' },
  // Absorbed into Meta IDE
  { id: 'workstation', label: 'Workstation', icon: Monitor, group: 'primary', visibility: 'dev', key: 'k' },
  // Absorbed into Organism Map
  { id: 'infrastructure', label: 'Infrastructure', icon: Server, group: 'primary', visibility: 'dev', key: 'h' },
  // Absorbed into Execution
  { id: 'sessions', label: 'Sessions', icon: MonitorSmartphone, group: 'primary', visibility: 'dev', key: 'n' },
  { id: 'execcoord', label: 'Exec Coordinator', icon: Cog, group: 'primary', visibility: 'dev', key: 'H' },
  { id: 'executor', label: 'Executor', icon: Play, group: 'primary', visibility: 'dev', key: 'x' },
  { id: 'organismloop', label: 'Organism Loop', icon: RotateCcw, group: 'primary', visibility: 'dev', key: 'O' },
  { id: 'operatortimeline', label: 'Operator Timeline', icon: Activity, group: 'primary', visibility: 'dev', key: 'T' },
  // Absorbed into Activity
  { id: 'realitytimeline', label: 'Reality Timeline', icon: Eye, group: 'primary', visibility: 'dev', key: 'R' },
  // Absorbed into Meta IDE
  { id: 'realityintelligence', label: 'Reality Intelligence', icon: Brain, group: 'primary', visibility: 'dev', key: 'I' },
  { id: 'engineering', label: 'Engineering', icon: Wrench, group: 'primary', visibility: 'dev', key: 'E' },
  // Redirected to Canvas modes (searchable in CommandPalette)
  { id: 'agents', label: 'Agents', icon: Bot, group: 'primary', visibility: 'dev', key: '2' },
  { id: 'workflows', label: 'Workflows', icon: Workflow, group: 'primary', visibility: 'dev', key: 'W' },
  // Standalone dev panels
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, group: 'primary', visibility: 'dev', key: '1' },
  { id: 'organism', label: 'Organism', icon: Brain, group: 'primary', visibility: 'dev', key: 'o' },
  { id: 'intelligence', label: 'Intelligence', icon: Lightbulb, group: 'primary', visibility: 'dev', key: 'N' },
  { id: 'propagation', label: 'Propagation', icon: Workflow, group: 'primary', visibility: 'dev', key: 'g' },
  { id: 'operator', label: 'Operator', icon: Mic, group: 'primary', visibility: 'dev', key: 'd' },
  { id: 'tmux', label: 'Tmux', icon: Terminal, group: 'primary', visibility: 'dev', key: 't' },
  { id: 'runtime', label: 'Runtime', icon: Play, group: 'primary', visibility: 'dev', key: 'r' },
  { id: 'selfbuild', label: 'Self-Build', icon: Hammer, group: 'primary', visibility: 'dev', key: 'B' },
  { id: 'universalwork', label: 'Universal Work', icon: Layers, group: 'primary', visibility: 'dev', key: 'w' },
  { id: 'worldmodel', label: 'World Model', icon: Globe, group: 'primary', visibility: 'dev', key: 'G' },
  { id: 'realitygraph', label: 'Reality Graph', icon: Map, group: 'primary', visibility: 'dev', key: 'g' },
  // Campaign 7 — Strategic Context & Executive Reasoning
  { id: 'strategic', label: 'Strategic', icon: Compass, group: 'primary', visibility: 'dev', key: '/' },
  // Campaign 8 — Goal Systems & Strategic Planning
  { id: 'goals', label: 'Goals', icon: Target, group: 'primary', visibility: 'dev', key: 'J' },
  // Campaign 9 — Decision Intelligence & Strategic Memory
  { id: 'memory', label: 'Memory', icon: Brain, group: 'primary', visibility: 'dev', key: 'K' },
  // Campaign 10 — Capability Intelligence
  { id: 'capabilities', label: 'Capabilities', icon: Layers, group: 'primary', visibility: 'dev', key: 'Q' },
  { id: 'portfolio', label: 'Portfolio', icon: Briefcase, group: 'primary', visibility: 'dev', key: 'p' },
  { id: 'company', label: 'Company', icon: Building2, group: 'primary', visibility: 'dev', key: 'c' },
  { id: 'profile', label: 'Profile', icon: User, group: 'primary', visibility: 'dev', key: 'u' },

  // C28 Phase 1.3 — Previously orphaned panels, now reachable via CommandPalette
  { id: 'actions', label: 'Actions', icon: Zap, group: 'primary', visibility: 'dev', key: 'M' },
  { id: 'distributedruntime', label: 'Distributed Runtime', icon: Network, group: 'primary', visibility: 'dev', key: ',' },
  { id: 'operatorcontinuity', label: 'Operator Continuity', icon: RefreshCw, group: 'primary', visibility: 'dev', key: '.' },
  { id: 'operatorhome', label: 'Operator Home', icon: Home, group: 'primary', visibility: 'dev', key: ';' },
  { id: 'screenawareness', label: 'Screen Awareness', icon: MonitorDot, group: 'primary', visibility: 'dev', key: '[' },
  { id: 'servicegraph', label: 'Service Graph', icon: GitBranch, group: 'primary', visibility: 'dev', key: ']' },
  { id: 'stateauthority', label: 'State Authority', icon: Shield, group: 'primary', visibility: 'dev', key: '-' },
  { id: 'umhnode', label: 'UMH Node', icon: Server, group: 'primary', visibility: 'dev', key: '=' },
  { id: 'workspacetopology', label: 'Workspace Topology', icon: Map, group: 'primary', visibility: 'dev', key: '\\' },

  // M1 — Operator MVP Closure (G10 + G11)
  { id: 'proofinspector', label: 'Proof Inspector', icon: ShieldCheck, group: 'primary', visibility: 'dev', key: '#' },
  { id: 'recoverydashboard', label: 'Recovery Dashboard', icon: RotateCcw, group: 'primary', visibility: 'dev', key: '$' },

  // Planned (searchable with [PLANNED] badge)
  { id: 'analytics', label: 'Analytics', icon: BarChart3, group: 'primary', visibility: 'planned', key: '6' },

  // Stub (NOT searchable)
]

export const ROUTE_GROUPS = [
  { key: 'primary' as const, label: 'PRIMARY' },
  { key: 'system' as const, label: 'SYSTEM' },
]
