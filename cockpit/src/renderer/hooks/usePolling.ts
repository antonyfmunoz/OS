import { useEffect, useRef } from 'react'

export function usePolling(
  callback: () => void,
  intervalMs: number,
  enabled = true,
  initialDelayMs = 0,
): void {
  const savedCallback = useRef(callback)
  savedCallback.current = callback

  useEffect(() => {
    if (!enabled) return
    const timers: ReturnType<typeof setTimeout>[] = []

    const start = () => {
      savedCallback.current()
      const id = setInterval(() => savedCallback.current(), intervalMs)
      timers.push(id as unknown as ReturnType<typeof setTimeout>)
    }

    if (initialDelayMs > 0) {
      timers.push(setTimeout(start, initialDelayMs))
    } else {
      start()
    }

    return () => timers.forEach(t => clearTimeout(t))
  }, [intervalMs, enabled, initialDelayMs])
}
