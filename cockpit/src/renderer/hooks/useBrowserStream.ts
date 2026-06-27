import { useEffect, useRef, useCallback, useSyncExternalStore } from 'react'
import { BrowserWsClient } from '../api/browser-ws'

interface BrowserStreamState {
  connected: boolean
  currentUrl: string
  pageTitle: string
  loading: boolean
  frameUrl: string | null
  viewportWidth: number
  viewportHeight: number
}

const _state: BrowserStreamState = {
  connected: false,
  currentUrl: 'about:blank',
  pageTitle: '',
  loading: false,
  frameUrl: null,
  viewportWidth: 1280,
  viewportHeight: 720,
}

let _listeners: (() => void)[] = []
let _snapshot = { ..._state }

function _notify(): void {
  _snapshot = { ..._state }
  for (const l of _listeners) l()
}

function subscribe(listener: () => void): () => void {
  _listeners.push(listener)
  return () => {
    _listeners = _listeners.filter((l2) => l2 !== listener)
  }
}

function getSnapshot(): BrowserStreamState {
  return _snapshot
}

let _client: BrowserWsClient | null = null
let _refCount = 0

function _getOrCreateClient(): BrowserWsClient {
  if (!_client) {
    _client = new BrowserWsClient()

    _client.on('connected', () => {
      _state.connected = true
      _notify()
    })

    _client.on('disconnected', () => {
      _state.connected = false
      _notify()
    })

    _client.on('url_changed', (data) => {
      _state.currentUrl = (data.url as string) || ''
      _notify()
    })

    _client.on('title_changed', (data) => {
      _state.pageTitle = (data.title as string) || ''
      _notify()
    })

    _client.on('loading', (data) => {
      _state.loading = Boolean(data.loading)
      _notify()
    })

    _client.on('viewport', (data) => {
      _state.viewportWidth = (data.width as number) || 1280
      _state.viewportHeight = (data.height as number) || 720
      _notify()
    })

    _client.onFrame((event) => {
      _state.frameUrl = event.url
      _notify()
    })
  }
  return _client
}

export function useBrowserStream() {
  const clientRef = useRef<BrowserWsClient | null>(null)
  const state = useSyncExternalStore(subscribe, getSnapshot)

  useEffect(() => {
    const client = _getOrCreateClient()
    clientRef.current = client
    _refCount++
    if (_refCount === 1) {
      client.connect()
    }
    return () => {
      _refCount--
      if (_refCount <= 0) {
        _refCount = 0
        client.disconnect()
        _client = null
        _state.connected = false
        _state.frameUrl = null
        _notify()
      }
    }
  }, [])

  const navigate = useCallback((url: string) => clientRef.current?.navigate(url), [])
  const goBack = useCallback(() => clientRef.current?.goBack(), [])
  const goForward = useCallback(() => clientRef.current?.goForward(), [])
  const reload = useCallback(() => clientRef.current?.reload(), [])
  const reconnect = useCallback(() => clientRef.current?.reconnect(), [])
  const resize = useCallback((w: number, h: number) => clientRef.current?.resize(w, h), [])

  const sendMouse = useCallback(
    (
      action: string,
      x: number,
      y: number,
      opts?: { button?: string; clickCount?: number; deltaX?: number; deltaY?: number }
    ) => clientRef.current?.sendMouse(action, x, y, opts),
    []
  )

  const sendKey = useCallback(
    (action: string, key: string, code: string, opts?: { text?: string; modifiers?: number }) =>
      clientRef.current?.sendKey(action, key, code, opts),
    []
  )

  const insertText = useCallback((text: string) => clientRef.current?.insertText(text), [])

  return {
    ...state,
    navigate,
    goBack,
    goForward,
    reload,
    reconnect,
    resize,
    sendMouse,
    sendKey,
    insertText,
  }
}
