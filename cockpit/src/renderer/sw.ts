/// <reference lib="webworker" />
declare const self: ServiceWorkerGlobalScope

interface PushPayload {
  title: string
  body: string
  category: string
  url: string
  data: Record<string, unknown>
}

self.addEventListener('push', (event: PushEvent) => {
  if (!event.data) return

  const payload: PushPayload = event.data.json()
  const icon = payload.category === 'action_required' ? '⚠️' : 'ℹ️'

  event.waitUntil(
    self.registration.showNotification(payload.title, {
      body: `${icon} ${payload.body}`,
      data: { url: payload.url, ...payload.data },
      tag: payload.category,
      renotify: payload.category === 'action_required',
    })
  )
})

self.addEventListener('notificationclick', (event: NotificationEvent) => {
  event.notification.close()
  const url = (event.notification.data as { url?: string })?.url || '/'

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
      const existing = clients.find((c) => c.url.includes('universalmetaharness.tech'))
      if (existing) {
        existing.focus()
        existing.navigate(url)
      } else {
        self.clients.openWindow(url)
      }
    })
  )
})

self.addEventListener('install', () => {
  self.skipWaiting()
})

self.addEventListener('activate', (event: ExtendableEvent) => {
  event.waitUntil(self.clients.claim())
})
