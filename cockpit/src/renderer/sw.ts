/// <reference lib="webworker" />
declare const self: ServiceWorkerGlobalScope

const CACHE_NAME = 'umh-shell-v2'
const SHELL_ASSETS = ['/', '/manifest.json', '/icon-192.png', '/icon-512.png', '/offline.html']

interface PushPayload {
  title: string
  body: string
  category: string
  url: string
  data: Record<string, unknown>
}

// --- Push notifications ---

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

// --- App shell caching ---

self.addEventListener('install', (event: ExtendableEvent) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_ASSETS))
  )
  self.skipWaiting()
})

self.addEventListener('activate', (event: ExtendableEvent) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  )
})

self.addEventListener('fetch', (event: FetchEvent) => {
  const { request } = event
  if (request.method !== 'GET') return

  const url = new URL(request.url)

  // Hashed assets (assets/*-[hash].js/css) — cache-first, immutable
  if (url.pathname.startsWith('/assets/')) {
    event.respondWith(
      caches.match(request).then(
        (cached) =>
          cached ||
          fetch(request).then((response) => {
            const clone = response.clone()
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone))
            return response
          })
      )
    )
    return
  }

  // Navigation requests (the HTML shell) — ALWAYS network-first with an explicit
  // no-cache reload so a new deploy is picked up immediately on the next visit,
  // even on iOS Safari which otherwise serves a stale shell from its own HTTP
  // cache. Refresh the cached copy on success; fall back to cache then offline.
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(new Request(request, { cache: 'reload' }))
        .then((response) => {
          const clone = response.clone()
          caches.open(CACHE_NAME).then((cache) => cache.put('/', clone))
          return response
        })
        .catch(() =>
          caches
            .match(request)
            .then((r) => r || caches.match('/offline.html').then((o) => o || new Response('Offline')))
        )
    )
    return
  }

  // Everything else — network-first, cache fallback
  event.respondWith(
    fetch(request)
      .then((response) => {
        const clone = response.clone()
        caches.open(CACHE_NAME).then((cache) => cache.put(request, clone))
        return response
      })
      .catch(() => caches.match(request).then((r) => r || new Response('', { status: 503 })))
  )
})
