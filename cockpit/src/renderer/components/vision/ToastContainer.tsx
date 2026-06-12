import { useEffect } from 'react'
import { clsx } from 'clsx'
import { useVisionStore } from '../../stores/visionStore'

const VARIANT_STYLES: Record<string, string> = {
  ok: 'bg-ok/20 text-ok border-ok/30',
  danger: 'bg-danger/20 text-danger border-danger/30',
  warning: 'bg-warning/20 text-warning border-warning/30',
  cyan: 'bg-cyan/20 text-cyan border-cyan/30',
}

export function ToastContainer() {
  const toasts = useVisionStore((s) => s.toasts)
  const removeToast = useVisionStore((s) => s.removeToast)

  useEffect(() => {
    if (toasts.length === 0) return
    const timer = setInterval(() => {
      const now = Date.now()
      for (const t of toasts) {
        if (t.expiresAt <= now) removeToast(t.id)
      }
    }, 500)
    return () => clearInterval(timer)
  }, [toasts, removeToast])

  if (toasts.length === 0) return null

  return (
    <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 max-w-sm pointer-events-none">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={clsx(
            'pointer-events-auto px-4 py-3 rounded-lg border text-xs font-mono shadow-lg',
            'animate-[fadeIn_150ms_ease-out]',
            VARIANT_STYLES[t.variant] || VARIANT_STYLES.cyan,
          )}
          onClick={() => removeToast(t.id)}
        >
          {t.message}
        </div>
      ))}
    </div>
  )
}
