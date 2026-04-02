import { spawn } from 'child_process'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const BRIDGE   = resolve(__dirname, '../../bridge/agent_bridge.py')

export interface BridgeResult {
  success: boolean
  data?:   unknown
  error?:  string
}

export async function callBridge(payload: Record<string, unknown>): Promise<BridgeResult> {
  return new Promise((res) => {
    const proc = spawn('python3', [BRIDGE], {
      env: { ...process.env },
      cwd: '/opt/OS',
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
        res({ success: true, data: JSON.parse(out) })
      } catch {
        res({ success: false, error: `invalid JSON from bridge: ${out.slice(0, 200)}` })
      }
    })

    proc.on('error', (e) => res({ success: false, error: e.message }))

    proc.stdin.write(JSON.stringify(payload))
    proc.stdin.end()
  })
}
