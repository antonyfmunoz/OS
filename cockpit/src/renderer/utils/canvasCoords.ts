export function screenToCanvas(
  screenX: number,
  screenY: number,
  panX: number,
  panY: number,
  zoom: number,
): { x: number; y: number } {
  return {
    x: (screenX - panX) / zoom,
    y: (screenY - panY) / zoom,
  }
}

export function canvasToScreen(
  canvasX: number,
  canvasY: number,
  panX: number,
  panY: number,
  zoom: number,
): { x: number; y: number } {
  return {
    x: canvasX * zoom + panX,
    y: canvasY * zoom + panY,
  }
}

export function clampZoom(zoom: number): number {
  return Math.min(2.0, Math.max(0.25, zoom))
}

export function zoomAtPoint(
  currentZoom: number,
  newZoom: number,
  pointX: number,
  pointY: number,
  panX: number,
  panY: number,
): { panX: number; panY: number; zoom: number } {
  const clamped = clampZoom(newZoom)
  const scale = clamped / currentZoom
  return {
    zoom: clamped,
    panX: pointX - (pointX - panX) * scale,
    panY: pointY - (pointY - panY) * scale,
  }
}
