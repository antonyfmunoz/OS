import { spawn } from 'child_process'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const AGENT_BRIDGE    = resolve(__dirname, '../../agent_bridge.py')
const ORGANISM_BRIDGE = resolve(__dirname, '../../organism_bridge.py')

export interface BridgeResult {
  success: boolean
  data?:   unknown
  error?:  string
}

function _callPython(bridgePath: string, payload: Record<string, unknown>): Promise<BridgeResult> {
  return new Promise((res) => {
    const proc = spawn('python3', [bridgePath], {
      env: { ...process.env },
      cwd: process.env.UMH_ROOT ?? '/opt/OS',
    })

    let out = ''
    let err = ''

    proc.stdout.on('data', (d: Buffer) => { out += d.toString() })
    proc.stderr.on('data', (d: Buffer) => { err += d.toString() })

    proc.on('close', (code) => {
      if (code !== 0) {
        res({ success: false, error: err || `bridge exited ${code}` })
        return
      }
      try {
        const parsed = JSON.parse(out)
        res({ success: parsed.success ?? true, data: parsed.data ?? parsed, error: parsed.error })
      } catch {
        res({ success: false, error: `invalid JSON from bridge: ${out.slice(0, 200)}` })
      }
    })

    proc.on('error', (e) => res({ success: false, error: e.message }))

    proc.stdin.write(JSON.stringify(payload))
    proc.stdin.end()
  })
}

export async function callBridge(payload: Record<string, unknown>): Promise<BridgeResult> {
  return _callPython(AGENT_BRIDGE, payload)
}

export async function callOrganism(action: string, payload: Record<string, unknown> = {}): Promise<BridgeResult> {
  return _callPython(ORGANISM_BRIDGE, { action, payload })
}
