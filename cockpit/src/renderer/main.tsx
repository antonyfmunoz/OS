import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { ClerkProvider } from '@clerk/clerk-react'
import { App } from './App'
import './styles/globals.css'

const clerkKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY as string

// Pin the exact clerk-js version so the runtime loader requests a concrete
// /npm/@clerk/clerk-js@<x.y.z>/ URL. The unpinned major-only URL (@5) 307s to
// the pinned one, and the browser rejects that redirect on the preflighted
// script fetch — which breaks EVERY cold-start (fresh profile, no cache).
// Production only survives via cached clerk-js; the Wave-1 Session-1 field
// run (fresh Chrome profile each pass) exposed it on 2026-07-22. Upgrade
// deliberately: bump this pin together with @clerk/clerk-react.
const CLERK_JS_VERSION = '5.127.1'

import { Capacitor } from '@capacitor/core'
import { initCapacitor } from './capacitor-init'

if (Capacitor.isNativePlatform()) {
  initCapacitor()
} else if ('serviceWorker' in navigator) {
  navigator.serviceWorker
    .register('/sw.js')
    .then((reg) => {
      // Actively check for a newer SW on every load so a fresh deploy is picked
      // up without the user manually clearing Safari's cache. When a new SW
      // takes control (the old one is replaced), reload once so the new HTML +
      // assets are shown. The `refreshing` guard prevents a reload loop.
      reg.update().catch(() => {})
      let refreshing = false
      navigator.serviceWorker.addEventListener('controllerchange', () => {
        if (refreshing) return
        refreshing = true
        window.location.reload()
      })
    })
    .catch(() => {})
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {clerkKey ? (
      <ClerkProvider publishableKey={clerkKey} clerkJSVersion={CLERK_JS_VERSION}>
        <App />
      </ClerkProvider>
    ) : (
      <App />
    )}
  </StrictMode>
)
