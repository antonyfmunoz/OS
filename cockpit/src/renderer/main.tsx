import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { ClerkProvider } from '@clerk/clerk-react'
import { App } from './App'
import './styles/globals.css'

const clerkKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY as string

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
      <ClerkProvider publishableKey={clerkKey}>
        <App />
      </ClerkProvider>
    ) : (
      <App />
    )}
  </StrictMode>
)
