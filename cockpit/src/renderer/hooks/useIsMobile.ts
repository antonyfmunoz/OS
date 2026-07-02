import { useSyncExternalStore } from 'react'

const MOBILE_BREAKPOINT = 640

function subscribe(cb: () => void) {
  const mql = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT}px)`)
  mql.addEventListener('change', cb)
  return () => mql.removeEventListener('change', cb)
}

function getSnapshot() {
  return window.innerWidth <= MOBILE_BREAKPOINT
}

export function useIsMobile() {
  return useSyncExternalStore(subscribe, getSnapshot, () => false)
}
