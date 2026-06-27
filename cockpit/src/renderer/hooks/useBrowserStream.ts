import { useEffect, useRef, useState, useCallback } from 'react'
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

export function useBrowserStream(paneId: string) {
  const [state, setState] = useState<BrowserStreamState>({
    connected: false,
    currentUrl: 'about:blank',
    pageTitle: '',
    loading: false,
    frameUrl: null,
    viewportWidth: 1280,
    viewportHeight: 720,
  })
  const clientRef = useRef<BrowserWsClient | null>(null)

  useEffect(() => {
    const client = new BrowserWsClient(paneId)
    clientRef.current = client

    const unsubs: (() => void)[] = []

    unsubs.push(client.on('connected', () => {
      setState((s) => ({ ...s, connected: true }))
    }))

    unsubs.push(client.on('disconnected', () => {
      setState((s) => ({ ...s, connected: false }))
    }))

    unsubs.push(client.on('url_changed', (data) => {
      setState((s) => ({ ...s, currentUrl: (data.url as string) || '' }))
    }))

    unsubs.push(client.on('title_changed', (data) => {
      setState((s) => ({ ...s, pageTitle: (data.title as string) || '' }))
    }))

    unsubs.push(client.on('loading', (data) => {
      setState((s) => ({ ...s, loading: Boolean(data.loading) }))
    }))

    unsubs.push(client.on('viewport', (data) => {
      setState((s) => ({
        ...s,
        viewportWidth: (data.width as number) || 1280,
        viewportHeight: (data.height as number) || 720,
      }))
    }))

    unsubs.push(client.onFrame((event) => {
      setState((s) => ({ ...s, frameUrl: event.url }))
    }))

    client.connect()

    return () => {
      for (const u of unsubs) u()
      client.disconnect()
      clientRef.current = null
    }
  }, [paneId])

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
