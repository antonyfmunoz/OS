import { useEffect, useRef, useState, type ReactNode } from 'react'
import { SignedIn, SignedOut, SignIn, useAuth, ClerkLoaded, ClerkLoading } from '@clerk/clerk-react'
import { Shell } from './components/Shell'
import { GuestJoinPage } from './components/rooms/GuestJoinPage'
import { useKeyboard } from './hooks/useKeyboard'
import { useOrganismRealtime } from './hooks/useOrganismRealtime'
import { useVisionConnection } from './hooks/useVisionConnection'
import { useBootstrapStore } from './stores/bootstrapStore'
import { useChatStore } from './stores/chatStore'
import { setTokenGetter } from './api/client'

const hasClerk = !!import.meta.env.VITE_CLERK_PUBLISHABLE_KEY

function TokenGate({ children }: { children: ReactNode }) {
  const { getToken } = useAuth()
  const ref = useRef(getToken)
  ref.current = getToken
  const [ready, setReady] = useState(false)

  useEffect(() => {
    setTokenGetter(async () => ref.current())
    let cancelled = false
    const poll = async () => {
      for (let i = 0; i < 20; i++) {
        if (cancelled) return
        const t = await ref.current()
        if (t) { setReady(true); return }
        await new Promise<void>((r) => setTimeout(r, 250))
      }
      setReady(true)
    }
    poll()
    return () => { cancelled = true }
  }, [])

  if (!ready) return null
  return <>{children}</>
}

function AuthenticatedApp() {
  useKeyboard()
  useOrganismRealtime()
  useVisionConnection()

  const boot = useBootstrapStore((s) => s.boot)
  const loadHistory = useChatStore((s) => s.loadHistory)
  const startPolling = useChatStore((s) => s.startPolling)
  const stopPolling = useChatStore((s) => s.stopPolling)

  useEffect(() => {
    boot().then(() => {
      loadHistory()
      startPolling()
    })
    return () => { stopPolling() }
  }, [boot, loadHistory, startPolling, stopPolling])

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
          marginTop: 6,
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

function getGuestInviteCode(): string | null {
  const match = window.location.pathname.match(/^\/join\/([a-zA-Z0-9_-]+)$/)
  return match ? match[1] : null
}

export function App() {
  const guestCode = getGuestInviteCode()
  if (guestCode) return <GuestJoinPage inviteCode={guestCode} />

  if (!hasClerk) return <AuthenticatedApp />

  return (
    <>
      <ClerkLoading>
        <LoadingScreen />
      </ClerkLoading>
      <ClerkLoaded>
        <SignedIn>
          <TokenGate>
            <AuthenticatedApp />
          </TokenGate>
        </SignedIn>
        <SignedOut>
          <LoginScreen />
        </SignedOut>
      </ClerkLoaded>
    </>
  )
}
