import { lazy, Suspense, Component, type ReactNode, type ErrorInfo } from 'react'

const BrowserWindowContent = lazy(() =>
  import('./windows/BrowserWindowContent').then((m) => ({ default: m.BrowserWindowContent })),
)
const DesktopWindowContent = lazy(() =>
  import('./windows/DesktopWindowContent').then((m) => ({ default: m.DesktopWindowContent })),
)
const VisionWindowContent = lazy(() =>
  import('./windows/VisionWindowContent').then((m) => ({ default: m.VisionWindowContent })),
)
const TerminalWindowContent = lazy(() =>
  import('./windows/TerminalWindowContent').then((m) => ({ default: m.TerminalWindowContent })),
)
const PreviewWindowContent = lazy(() =>
  import('./windows/PreviewWindowContent').then((m) => ({ default: m.PreviewWindowContent })),
)
const AgentWindowContent = lazy(() =>
  import('./windows/AgentWindowContent').then((m) => ({ default: m.AgentWindowContent })),
)
const PanelWindowContent = lazy(() =>
  import('./windows/PanelWindowContent').then((m) => ({ default: m.PanelWindowContent })),
)

interface WindowContentProps {
  type: string
  config: Record<string, string | undefined>
  paused: boolean
  onResizeHint?: (width: number, height: number) => void
}

function LoadingFallback() {
  return (
    <div
      className="flex items-center justify-center h-full"
      style={{ color: 'var(--color-text-tertiary)' }}
    >
      <span className="text-[12px]">Loading...</span>
    </div>
  )
}

interface EBState { hasError: boolean; error: Error | null }

class WindowErrorBoundary extends Component<{ type: string; children: ReactNode }, EBState> {
  state: EBState = { hasError: false, error: null }
  static getDerivedStateFromError(error: Error) { return { hasError: true, error } }
  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error(`[WindowContent:${this.props.type}]`, error, info.componentStack)
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center h-full gap-2"
          style={{ color: 'var(--color-text-tertiary)' }}>
          <span className="text-[12px]">Window crashed</span>
          <span className="text-[10px]" style={{ color: 'var(--color-warn)' }}>
            {this.state.error?.message ?? 'Unknown error'}
          </span>
          <button className="text-[11px] px-2 py-1 rounded mt-1"
            style={{ border: '1px solid var(--color-border)', color: 'var(--color-text-secondary)' }}
            onClick={() => this.setState({ hasError: false, error: null })}>
            Retry
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

export function WindowContent({ type, config, paused, onResizeHint }: WindowContentProps) {
  let content: React.ReactNode

  switch (type) {
    case 'browser':
      content = <BrowserWindowContent paneId={config.paneId ?? '0'} paused={paused} />
      break
    case 'desktop':
      content = <DesktopWindowContent monitorId={config.monitorId ?? 'M0'} paused={paused} onResizeHint={onResizeHint} />
      break
    case 'vision':
      content = <VisionWindowContent paused={paused} />
      break
    case 'terminal':
      content = (
        <TerminalWindowContent
          session={config.session ?? 'assistant_main'}
          pane={config.pane ?? '0'}
          paused={paused}
          node={config.node}
          shell={config.shell}
        />
      )
      break
    case 'preview':
      content = <PreviewWindowContent url={config.url ?? ''} />
      break
    case 'agent':
      content = <AgentWindowContent agentId={config.agentId ?? ''} />
      break
    case 'panel':
      content = <PanelWindowContent panelId={config.panelId ?? 'dashboard'} />
      break
    default:
      return (
        <div
          className="flex items-center justify-center h-full"
          style={{ color: 'var(--color-text-tertiary)' }}
        >
          <span className="text-[12px]">Unknown window type: {type}</span>
        </div>
      )
  }

  return (
    <WindowErrorBoundary type={type}>
      <Suspense fallback={<LoadingFallback />}>{content}</Suspense>
    </WindowErrorBoundary>
  )
}
