// lib/react-gen/live-preview-server.ts
// Ensures a Vite dev server is running for live preview during generation.
// Pages are written to disk and Vite hot-reloads automatically.

import { spawn, type ChildProcess } from "node:child_process";
import net from "node:net";

export interface LivePreviewServer {
  url: string;
  isNew: boolean;
  shutdown: () => Promise<void>;
}

function checkPort(port: number): Promise<boolean> {
  return new Promise((resolve) => {
    const sock = net.createConnection({ port, host: "localhost" });
    sock.setTimeout(2000);
    sock.on("connect", () => {
      sock.destroy();
      resolve(true);
    });
    sock.on("error", () => resolve(false));
    sock.on("timeout", () => {
      sock.destroy();
      resolve(false);
    });
  });
}

async function pollUntilReady(port: number, timeoutMs: number = 30000): Promise<void> {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    if (await checkPort(port)) return;
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error(`Vite dev server did not respond on port ${port} within ${timeoutMs / 1000}s`);
}

export async function ensureLivePreviewServer(
  projectRoot: string,
): Promise<LivePreviewServer> {
  // Check if already running on common ports
  for (const port of [5000, 5173, 5174]) {
    if (await checkPort(port)) {
      const url = `http://localhost:${port}`;
      console.log(`\u{1F680} Live preview already running: ${url}`);
      return {
        url,
        isNew: false,
        shutdown: async () => {},
      };
    }
  }

  // Start dev server
  const child: ChildProcess = spawn("npm", ["run", "dev"], {
    cwd: projectRoot,
    stdio: ["ignore", "pipe", "pipe"],
    detached: true,
    shell: true,
  });

  // Unref so the parent process can exit independently
  child.unref();

  // Capture port from stdout — matches "localhost:PORT" (Vite) or "port PORT" (Express)
  let detectedPort = 5000;
  const portPattern = /(?:localhost:|port\s+)(\d+)/i;
  child.stdout?.on("data", (data: Buffer) => {
    const match = data.toString().match(portPattern);
    if (match) detectedPort = parseInt(match[1], 10);
  });

  child.stderr?.on("data", (data: Buffer) => {
    const match = data.toString().match(portPattern);
    if (match) detectedPort = parseInt(match[1], 10);
  });

  // Give the process a moment to log its port, then poll
  await new Promise((r) => setTimeout(r, 3000));
  await pollUntilReady(detectedPort);
  const url = `http://localhost:${detectedPort}`;

  // Print clickable link (OSC 8 hyperlink)
  const osc = `\x1b]8;;${url}\x07${url}\x1b]8;;\x07`;
  console.log(`\u{1F680} Live preview ready: ${osc}`);

  return {
    url,
    isNew: true,
    shutdown: async () => {
      if (child.pid) {
        try {
          process.kill(-child.pid, "SIGTERM");
        } catch {
          child.kill("SIGTERM");
        }
      }
    },
  };
}
