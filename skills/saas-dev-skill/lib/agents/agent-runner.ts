// lib/agents/agent-runner.ts
// Spawns, coordinates, and manages agent lifecycle.
// Handles retries with exponential backoff, progress reporting, and logging.

import fs from "node:fs";
import path from "node:path";
import pLimit from "p-limit";
import type { AgentResult, AgentStatus } from "./types.js";

interface RunOptions {
  name: string;
  retries?: number;
  onProgress?: (msg: string) => void;
}

interface RunParallelItem<T> {
  name: string;
  fn: () => Promise<T>;
}

interface RunParallelOptions {
  concurrency: number;
  onProgress?: (name: string, msg: string) => void;
}

export class AgentRunner {
  private readonly logPath: string;

  constructor(projectRoot: string) {
    const artifactsDir = path.join(projectRoot, ".planning", "artifacts");
    if (!fs.existsSync(artifactsDir)) {
      fs.mkdirSync(artifactsDir, { recursive: true });
    }
    this.logPath = path.join(artifactsDir, "build-log.jsonl");
  }

  private log(entry: { agent: string; event: string; detail?: string }): void {
    const line = JSON.stringify({ ...entry, timestamp: Date.now() }) + "\n";
    fs.appendFileSync(this.logPath, line, "utf-8");
  }

  async run<T>(agentFn: () => Promise<T>, opts: RunOptions): Promise<AgentResult<T>> {
    const { name, retries = 2, onProgress } = opts;
    const startTime = Date.now();
    let lastError: string | null = null;
    let attempts = 0;

    this.log({ agent: name, event: "started" });
    onProgress?.(`Starting ${name}...`);

    while (attempts <= retries) {
      try {
        if (attempts > 0) {
          const backoffMs = Math.min(1000 * Math.pow(2, attempts - 1), 30000);
          this.log({ agent: name, event: "retry", detail: `attempt ${attempts + 1}, backoff ${backoffMs}ms` });
          onProgress?.(`Retrying ${name} (attempt ${attempts + 1})...`);
          await new Promise((r) => setTimeout(r, backoffMs));
        }

        const data = await agentFn();
        const durationMs = Date.now() - startTime;

        this.log({ agent: name, event: "completed", detail: `${durationMs}ms` });
        onProgress?.(`${name} completed in ${(durationMs / 1000).toFixed(1)}s`);

        return {
          agentName: name,
          status: "completed",
          data,
          error: null,
          durationMs,
          retries: attempts,
        };
      } catch (err) {
        lastError = err instanceof Error ? err.message : String(err);
        this.log({ agent: name, event: "error", detail: lastError });
        attempts++;
      }
    }

    const durationMs = Date.now() - startTime;
    onProgress?.(`${name} failed after ${attempts} attempts: ${lastError}`);

    return {
      agentName: name,
      status: "failed",
      data: null,
      error: lastError,
      durationMs,
      retries: attempts - 1,
    };
  }

  async runParallel<T>(
    items: RunParallelItem<T>[],
    opts: RunParallelOptions,
  ): Promise<AgentResult<T>[]> {
    const { concurrency, onProgress } = opts;
    const limit = pLimit(concurrency);

    const tasks = items.map((item) =>
      limit(() =>
        this.run<T>(item.fn, {
          name: item.name,
          onProgress: onProgress ? (msg) => onProgress(item.name, msg) : undefined,
        }),
      ),
    );

    return Promise.all(tasks);
  }
}
