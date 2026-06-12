import { Component, type ReactNode, type ErrorInfo } from 'react'

interface Props {
  fallback?: ReactNode
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[ErrorBoundary]', error, info.componentStack)
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback

      return (
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="text-center max-w-md">
            <p className="text-xs font-mono font-semibold mb-2" style={{ color: 'var(--color-danger)' }}>
              RENDER ERROR
            </p>
            <p className="text-[10px] font-mono mb-3" style={{ color: 'var(--color-text-secondary)' }}>
              {this.state.error?.message || 'An unexpected error occurred'}
            </p>
            <button
              onClick={() => this.setState({ hasError: false, error: null })}
              className="text-[10px] font-mono px-3 py-1.5 rounded border"
              style={{ borderColor: 'var(--color-cyan)', color: 'var(--color-cyan)' }}
            >
              Retry
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
