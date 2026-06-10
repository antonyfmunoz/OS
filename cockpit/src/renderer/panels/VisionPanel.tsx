import { useEffect } from 'react'
import { Camera } from 'lucide-react'
import { useViewContextStore } from '../stores/viewContextStore'
import { useVisionStore } from '../stores/visionStore'
import { CameraController } from '../components/CameraController'

export function VisionPanel() {
  const setViewContext = useViewContextStore((s) => s.setContext)
  const { cameraStatus, activePreset, streaming, connected, frameCount, qualityMode, hasPtzHardware } = useVisionStore()

  useEffect(() => {
    setViewContext({ active_route: 'vision', visible_context_summary: 'Vision — camera feed and controls' })
  }, [setViewContext])

  return (
    <div className="p-4 space-y-4 overflow-y-auto h-full text-xs font-mono">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Camera size={16} className="text-cyan-400" />
          <h2 className="text-sm font-bold text-cyan-400">Vision</h2>
        </div>
        <div className="flex items-center gap-3 text-[10px] text-gray-500">
          {streaming && <span className="text-green-400">{frameCount} frames</span>}
          {activePreset && <span>preset: <span className="text-cyan-400">{activePreset}</span></span>}
          <span className="text-gray-500">{qualityMode}</span>
          <span className={connected ? 'text-green-400' : 'text-red-400'}>
            {connected ? 'connected' : 'disconnected'}
          </span>
        </div>
      </div>

      <div className="max-w-3xl">
        <CameraController />
      </div>

      {/* Privacy rules */}
      <div className="border border-gray-800 rounded p-3 max-w-3xl">
        <div className="text-[10px] text-gray-400 mb-2 uppercase tracking-wider">Privacy Governance</div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[10px] text-gray-500">
          <span>Camera off by default</span>
          <span>No face recognition</span>
          <span>No persistent storage</span>
          <span>No hidden recording</span>
          <span>AI analysis on-demand only</span>
          <span>Tailscale network only</span>
          <span>Auto-stop after 30m idle</span>
          <span>Operator kill anytime</span>
        </div>
      </div>

      {/* Voice commands reference */}
      <div className="border border-gray-800 rounded p-3 max-w-3xl">
        <div className="text-[10px] text-gray-400 mb-2 uppercase tracking-wider">Voice Commands</div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[10px]">
          <span className="text-gray-300">"turn on the camera"</span>
          <span className="text-gray-500">start live preview</span>
          <span className="text-gray-300">"turn off the camera"</span>
          <span className="text-gray-500">stop camera</span>
          <span className="text-gray-300">"look at me"</span>
          <span className="text-gray-500">operator preset</span>
          <span className="text-gray-300">"look at my keyboard"</span>
          <span className="text-gray-500">keyboard preset</span>
          <span className="text-gray-300">"look at the desk"</span>
          <span className="text-gray-500">desk preset</span>
          <span className="text-gray-300">"what do you see?"</span>
          <span className="text-gray-500">AI snapshot analysis</span>
          <span className="text-gray-300">"take a snapshot"</span>
          <span className="text-gray-500">capture frame</span>
          <span className="text-gray-300">"move camera left/right/up/down"</span>
          <span className="text-gray-500">manual PTZ</span>
          <span className="text-gray-300">"zoom in / zoom out"</span>
          <span className="text-gray-500">zoom control</span>
          <span className="text-gray-300">"center the camera"</span>
          <span className="text-gray-500">home position</span>
          <span className="text-gray-300">"save this as my keyboard preset"</span>
          <span className="text-gray-500">save PTZ preset</span>
          <span className="text-gray-300">"switch to smooth / sharp mode"</span>
          <span className="text-gray-500">quality mode</span>
        </div>
      </div>
    </div>
  )
}
