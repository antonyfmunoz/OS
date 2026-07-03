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
  navigator.serviceWorker.register('/sw.js').catch(() => {})
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
