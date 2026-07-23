import { useEffect, useRef, type ReactNode } from 'react'
import { SignedIn, SignedOut, SignIn, useAuth, ClerkLoaded, ClerkLoading } from '@clerk/clerk-react'
import { Shell } from './components/Shell'
import { GuestJoinPage } from './components/rooms/GuestJoinPage'
import { useKeyboard } from './hooks/useKeyboard'
import { useOrganismRealtime } from './hooks/useOrganismRealtime'
import { useVisionConnection } from './hooks/useVisionConnection'
import { useBootstrapStore, waitForHydration } from './stores/bootstrapStore'
import { useChatStore } from './stores/chatStore'
import type { Panel } from './stores/cockpitStore'
import { setTokenGetter } from './api/client'

const hasClerk = !!import.meta.env.VITE_CLERK_PUBLISHABLE_KEY

function TokenGate({ children }: { children: ReactNode }) {
  const { getToken } = useAuth()
  const ref = useRef(getToken)
  ref.current = getToken

  setTokenGetter(() => ref.current())

  return <>{children}</>
}

function AuthenticatedApp() {
  useKeyboard()
  useOrganismRealtime()
  useVisionConnection()

  // Panel deep-link: ?panel=<id> opens that surface on load. Bookmarkable and
  // projection-general; also the navigation hook automated browser verification
  // uses. Delegate to cockpitStore.setPanel — the SINGLE navigation authority —
  // so every surface class resolves correctly: retired ids alias to their
  // canonical panel, 'chat' opens the right rail (not a stray panel window),
  // 'canvas' aliases (agents/workflows) open the workspace without a window,
  // and every other panel renders as a canvas window. Duplicating setPanel's
  // special-cases here previously turned ?panel=commands into a bogus "chat"
  // panel window and ?panel=agents into a canvas panel window.
  useEffect(() => {
    const requested = new URLSearchParams(window.location.search).get('panel')
    if (requested) {
      import('./stores/cockpitStore').then(({ useCockpitStore }) => {
        // setPanel resolves aliases internally (resolvePanelId accepts any
        // string); the query value is a panel id or a registered alias.
        useCockpitStore.getState().setPanel(requested as Panel)
      })
    }
  }, [])

  const boot = useBootstrapStore((s) => s.boot)
  const loadHistory = useChatStore((s) => s.loadHistory)
  const startPolling = useChatStore((s) => s.startPolling)
  const stopPolling = useChatStore((s) => s.stopPolling)

  const bootSlow = useBootstrapStore((s) => s.bootSlow)

  useEffect(() => {
    waitForHydration().then(() => {
      boot().then(() => {
        bootSlow()
        loadHistory()
        startPolling()
      })
    })
    return () => { stopPolling() }
  }, [boot, bootSlow, loadHistory, startPolling, stopPolling])

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
      // 100dvh tracks the *visible* viewport on mobile Safari (100vh is taller
      // than the screen because of the URL bar, which shoved the card off-center
      // upward). Horizontal padding keeps the card off the screen edges on narrow
      // phones and respects the notch/safe-area insets.
      minHeight: '100dvh',
      width: '100%',
      padding: 'max(16px, env(safe-area-inset-top)) max(16px, env(safe-area-inset-right)) max(16px, env(safe-area-inset-bottom)) max(16px, env(safe-area-inset-left))',
      boxSizing: 'border-box',
      background: '#0A0A0A',
    }}>
      <SignIn appearance={{
        elements: {
          // Center the Clerk card itself within the rootBox — otherwise it
          // left-aligns inside the 420px box on wide screens and reads off-center.
          rootBox: { width: '100%', maxWidth: 420, display: 'flex', justifyContent: 'center' },
          cardBox: { width: '100%' },
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
