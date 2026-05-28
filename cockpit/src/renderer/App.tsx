import { useEffect } from 'react'
import { SignedIn, SignedOut, SignIn, useAuth, ClerkLoaded, ClerkLoading } from '@clerk/clerk-react'
import { Shell } from './components/Shell'
import { useKeyboard } from './hooks/useKeyboard'
import { useWebSocket } from './hooks/useWebSocket'
import { useOrganismRealtime } from './hooks/useOrganismRealtime'
import { useChatStore } from './stores/chatStore'
import { setTokenGetter } from './api/client'

const hasClerk = !!import.meta.env.VITE_CLERK_PUBLISHABLE_KEY

function ClerkTokenBridge() {
  const { getToken } = useAuth()
  useEffect(() => {
    setTokenGetter(() => getToken())
  }, [getToken])
  return null
}

function AuthenticatedApp() {
  useKeyboard()
  useWebSocket()
  useOrganismRealtime()

  const loadHistory = useChatStore((s) => s.loadHistory)

  useEffect(() => {
    loadHistory()
  }, [loadHistory])

  return <Shell />
}

function LoadingScreen() {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100vh',
      background: '#0A0A0A',
    }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{
          fontFamily: '"JetBrains Mono", monospace',
          fontSize: 14,
          letterSpacing: '0.15em',
          textTransform: 'uppercase' as const,
          color: '#00E5FF',
        }}>UMH</div>
        <div style={{
          fontFamily: '"JetBrains Mono", monospace',
          fontSize: 11,
          color: '#555',
          marginTop: 8,
        }}>initializing...</div>
      </div>
    </div>
  )
}

function LoginScreen() {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100vh',
      background: '#0A0A0A',
    }}>
      <SignIn appearance={{
        elements: {
          rootBox: { width: '100%', maxWidth: 420 },
        },
      }} />
    </div>
  )
}

export function App() {
  if (!hasClerk) return <AuthenticatedApp />

  return (
    <>
      <ClerkLoading>
        <LoadingScreen />
      </ClerkLoading>
      <ClerkLoaded>
        <SignedIn>
          <ClerkTokenBridge />
          <AuthenticatedApp />
        </SignedIn>
        <SignedOut>
          <LoginScreen />
        </SignedOut>
      </ClerkLoaded>
    </>
  )
}
