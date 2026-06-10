import { useEffect, useRef, useCallback } from 'react'
import { useVisionStore } from '../stores/visionStore'

const POPOUT_WIDTH = 480
const POPOUT_HEIGHT = 360

function getVisionWsUrl(): string {
  if (import.meta.env.VITE_VISION_URL) return import.meta.env.VITE_VISION_URL as string
  const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  const isElectron = Boolean((window as Record<string, unknown>).cockpit)
  if (isElectron || isLocal) return 'ws://localhost:8097/vision'
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}/api/umh/vision/ws`
}

function buildPopoutDom(doc: Document): void {
  const wsUrl = getVisionWsUrl()
  const token = (import.meta.env.VITE_VISION_TOKEN as string) || ''

  doc.title = 'Vision'

  const style = doc.createElement('style')
  style.textContent = `
*{margin:0;padding:0;box-sizing:border-box}
html,body{height:100%;overflow:hidden;background:#111;color:#E0E0E0;
font-family:"JetBrains Mono","Fira Code",monospace;font-size:12px}
#wrap{display:flex;flex-direction:column;height:100%;user-select:none}
#bar{display:flex;align-items:center;justify-content:space-between;
padding:6px 10px;background:#0A0A0A;border-bottom:1px solid #2A2A2A}
#preview{flex:1;position:relative;overflow:hidden;background:#000;
display:flex;align-items:center;justify-content:center}
#preview img{width:100%;height:100%;object-fit:contain}
#ctrls{display:flex;align-items:center;gap:6px;padding:6px 10px;
background:#0A0A0A;border-top:1px solid #2A2A2A}
.btn{display:flex;align-items:center;gap:4px;padding:4px 8px;
border-radius:4px;border:none;font-family:inherit;font-size:10px;
text-transform:uppercase;letter-spacing:.05em;cursor:pointer}
.btn-go{background:rgba(0,255,136,.1);color:#00FF88}
.btn-go:hover{background:rgba(0,255,136,.2)}
.btn-stop{background:rgba(255,61,61,.1);color:#FF3D3D}
.btn-stop:hover{background:rgba(255,61,61,.2)}
.btn-snap{background:rgba(0,229,255,.1);color:#00E5FF}
.btn-snap:hover{background:rgba(0,229,255,.2)}
.btn-x{background:none;border:none;color:#555;cursor:pointer;padding:2px}
.btn-x:hover{color:#FF3D3D}
#status{font-size:9px;color:#555;margin-left:auto;display:flex;align-items:center;gap:4px}
.dot{width:6px;height:6px;border-radius:50%;display:inline-block}
.dot-on{background:#00FF88}.dot-off{background:#FF3D3D}
#rec{position:absolute;top:4px;left:4px;display:none;align-items:center;gap:4px;
padding:2px 6px;border-radius:3px;background:rgba(255,61,61,.15);
font-size:9px;color:#FF3D3D;text-transform:uppercase;letter-spacing:.1em}
#rec .dot{background:#FF3D3D;animation:pulse 1.5s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
#fcount{position:absolute;top:4px;right:4px;padding:2px 6px;border-radius:3px;
background:rgba(0,0,0,.6);font-size:9px;color:#888;display:none}
.placeholder{color:#555;opacity:.3}`
  doc.head.appendChild(style)

  doc.body.innerHTML = ''

  const wrap = el(doc, 'div', { id: 'wrap' })
  const bar = el(doc, 'div', { id: 'bar' })
  const title = el(doc, 'span')
  title.style.cssText = 'font-size:10px;color:#00E5FF;letter-spacing:.1em;text-transform:uppercase'
  title.textContent = 'Vision'
  bar.appendChild(title)
  const closeBtn = el(doc, 'button', { className: 'btn-x', title: 'Close' })
  closeBtn.appendChild(svgIcon(doc, 14, ['M18 6 6 18', 'm6 6 12 12']))
  closeBtn.addEventListener('click', () => doc.defaultView?.close())
  bar.appendChild(closeBtn)
  wrap.appendChild(bar)

  const preview = el(doc, 'div', { id: 'preview' })
  const ph = svgIcon(doc, 24, ['M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z'], [{ cx: '12', cy: '13', r: '3' }])
  ph.setAttribute('id', 'ph')
  ph.setAttribute('class', 'placeholder')
  preview.appendChild(ph)
  const frame = doc.createElement('img')
  frame.id = 'frame'
  frame.alt = 'Camera'
  frame.style.display = 'none'
  preview.appendChild(frame)
  const rec = el(doc, 'div', { id: 'rec' })
  const recDot = el(doc, 'span', { className: 'dot' })
  rec.appendChild(recDot)
  rec.appendChild(doc.createTextNode('camera active'))
  preview.appendChild(rec)
  const fcount = el(doc, 'div', { id: 'fcount' })
  fcount.textContent = '0 frames'
  preview.appendChild(fcount)
  wrap.appendChild(preview)

  const ctrls = el(doc, 'div', { id: 'ctrls' })
  const startBtn = el(doc, 'button', { id: 'startBtn', className: 'btn btn-go' })
  startBtn.textContent = 'Start'
  const stopBtn = el(doc, 'button', { id: 'stopBtn', className: 'btn btn-stop' })
  stopBtn.textContent = 'Stop'
  stopBtn.style.display = 'none'
  const snapBtn = el(doc, 'button', { className: 'btn btn-snap' })
  snapBtn.textContent = 'Snap'
  const statusDiv = el(doc, 'div', { id: 'status' })
  const dotSpan = el(doc, 'span', { id: 'dot', className: 'dot dot-off' })
  const stxt = el(doc, 'span', { id: 'stxt' })
  stxt.textContent = 'disconnected'
  statusDiv.appendChild(dotSpan)
  statusDiv.appendChild(stxt)
  ctrls.appendChild(startBtn)
  ctrls.appendChild(stopBtn)
  ctrls.appendChild(snapBtn)
  ctrls.appendChild(statusDiv)
  wrap.appendChild(ctrls)
  doc.body.appendChild(wrap)

  // --- WebSocket logic ---
  let ws: WebSocket | null = null
  let prevUrl: string | null = null
  let frames = 0
  let streaming = false

  function send(type: string, params?: Record<string, unknown>) {
    if (ws?.readyState === 1) ws.send(JSON.stringify({ type, ...params }))
  }

  function updateUi() {
    startBtn.style.display = streaming ? 'none' : 'flex'
    stopBtn.style.display = streaming ? 'flex' : 'none'
    rec.style.display = streaming ? 'flex' : 'none'
    fcount.style.display = streaming ? 'block' : 'none'
  }

  function connect() {
    const protocols = token ? [`auth.${token}`] : []
    ws = new WebSocket(wsUrl, protocols)
    ws.binaryType = 'arraybuffer'
    ws.onopen = () => {
      dotSpan.className = 'dot dot-on'
      stxt.textContent = 'connected'
      send('camera_status')
    }
    ws.onclose = () => {
      dotSpan.className = 'dot dot-off'
      stxt.textContent = 'disconnected'
      streaming = false
      updateUi()
      setTimeout(connect, 3000)
    }
    ws.onmessage = (e) => {
      if (e.data instanceof ArrayBuffer) {
        if (prevUrl) URL.revokeObjectURL(prevUrl)
        const blob = new Blob([e.data], { type: 'image/jpeg' })
        prevUrl = URL.createObjectURL(blob)
        frame.src = prevUrl
        frame.style.display = 'block'
        ph.style.display = 'none'
        frames++
        fcount.textContent = `${frames} frames`
        return
      }
      try {
        const m = JSON.parse(e.data as string)
        if (m.type === 'vision_status') { streaming = m.streaming; updateUi() }
      } catch { /* non-JSON message */ }
    }
  }

  startBtn.addEventListener('click', () => {
    send('camera_start', { fps: 2, width: 640, height: 480, quality: 60 })
    send('vision_subscribe', { fps: 2, quality: 60 })
    streaming = true
    updateUi()
  })
  stopBtn.addEventListener('click', () => {
    send('camera_stop')
    send('vision_unsubscribe')
    streaming = false
    updateUi()
  })
  snapBtn.addEventListener('click', () => {
    send('camera_snapshot', { width: 1280, height: 720, quality: 75 })
  })

  connect()
}

function el(doc: Document, tag: string, attrs?: Record<string, string>): HTMLElement {
  const node = doc.createElement(tag)
  if (attrs) {
    for (const [k, v] of Object.entries(attrs)) {
      if (k === 'className') node.className = v
      else if (k === 'id') node.id = v
      else node.setAttribute(k, v)
    }
  }
  return node
}

function svgIcon(
  doc: Document,
  size: number,
  paths: string[],
  circles?: { cx: string; cy: string; r: string }[],
): SVGSVGElement {
  const NS = 'http://www.w3.org/2000/svg'
  const svg = doc.createElementNS(NS, 'svg')
  svg.setAttribute('width', String(size))
  svg.setAttribute('height', String(size))
  svg.setAttribute('viewBox', '0 0 24 24')
  svg.setAttribute('fill', 'none')
  svg.setAttribute('stroke', 'currentColor')
  svg.setAttribute('stroke-width', '2')
  svg.setAttribute('stroke-linecap', 'round')
  svg.setAttribute('stroke-linejoin', 'round')
  for (const d of paths) {
    const p = doc.createElementNS(NS, 'path')
    p.setAttribute('d', d)
    svg.appendChild(p)
  }
  if (circles) {
    for (const c of circles) {
      const ci = doc.createElementNS(NS, 'circle')
      ci.setAttribute('cx', c.cx)
      ci.setAttribute('cy', c.cy)
      ci.setAttribute('r', c.r)
      svg.appendChild(ci)
    }
  }
  return svg
}

export function useVisionPopout() {
  const popoutRef = useRef<Window | null>(null)
  const setPoppedOut = useVisionStore((s) => s.setPoppedOut)

  const openPopout = useCallback(() => {
    if (popoutRef.current && !popoutRef.current.closed) {
      popoutRef.current.focus()
      return
    }

    const left = window.screenX + window.outerWidth - POPOUT_WIDTH - 20
    const top = window.screenY + 60
    const features = `width=${POPOUT_WIDTH},height=${POPOUT_HEIGHT},left=${left},top=${top},resizable=yes,scrollbars=no,toolbar=no,menubar=no,location=no,status=no`

    const win = window.open('about:blank', 'umh-vision-popout', features)
    if (!win) return

    buildPopoutDom(win.document)

    popoutRef.current = win
    setPoppedOut(true, win)

    const checkClosed = setInterval(() => {
      if (win.closed) {
        clearInterval(checkClosed)
        popoutRef.current = null
        setPoppedOut(false)
      }
    }, 500)

    win.addEventListener('beforeunload', () => {
      clearInterval(checkClosed)
      popoutRef.current = null
      setPoppedOut(false)
    })
  }, [setPoppedOut])

  const closePopout = useCallback(() => {
    if (popoutRef.current && !popoutRef.current.closed) {
      popoutRef.current.close()
    }
    popoutRef.current = null
    setPoppedOut(false)
  }, [setPoppedOut])

  useEffect(() => {
    return () => {
      if (popoutRef.current && !popoutRef.current.closed) {
        popoutRef.current.close()
      }
    }
  }, [])

  return { openPopout, closePopout }
}
