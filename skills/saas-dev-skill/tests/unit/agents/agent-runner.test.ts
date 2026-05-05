import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { AgentRunner } from "../../../lib/agents/agent-runner.js";

// ─── Setup / Teardown ───────────────────────────────────────────────────────

let tmpDir: string;
let runner: AgentRunner;

beforeEach(() => {
  tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "agent-runner-test-"));
  runner = new AgentRunner(tmpDir);
});

afterEach(() => {
  fs.rmSync(tmpDir, { recursive: true, force: true });
});

// ─── Tests ──────────────────────────────────────────────────────────────────

describe("AgentRunner", () => {
  describe("run()", () => {
    it("returns completed result on success", async () => {
      const result = await runner.run(
        async () => ({ answer: 42 }),
        { name: "test-agent" },
      );

      expect(result.agentName).toBe("test-agent");
      expect(result.status).toBe("completed");
      expect(result.data).toEqual({ answer: 42 });
      expect(result.error).toBeNull();
      expect(result.durationMs).toBeGreaterThanOrEqual(0);
      expect(result.retries).toBe(0);
    });

    it("retries on failure and returns failed after exhausting retries", async () => {
      let callCount = 0;
      const result = await runner.run(
        async () => {
          callCount++;
          throw new Error("always fails");
        },
        { name: "failing-agent", retries: 2 },
      );

      expect(result.status).toBe("failed");
      expect(result.data).toBeNull();
      expect(result.error).toBe("always fails");
      // 1 initial + 2 retries = 3 total calls
      expect(callCount).toBe(3);
      expect(result.retries).toBe(2);
    });

    it("succeeds after retrying a transient failure", async () => {
      let callCount = 0;
      const result = await runner.run(
        async () => {
          callCount++;
          if (callCount < 2) throw new Error("transient");
          return "recovered";
        },
        { name: "transient-agent", retries: 2 },
      );

      expect(result.status).toBe("completed");
      expect(result.data).toBe("recovered");
      expect(result.retries).toBe(1);
    });

    it("calls onProgress callback", async () => {
      const messages: string[] = [];
      await runner.run(
        async () => "done",
        {
          name: "progress-agent",
          onProgress: (msg) => messages.push(msg),
        },
      );

      expect(messages.length).toBeGreaterThanOrEqual(2);
      expect(messages[0]).toContain("Starting progress-agent");
      expect(messages[messages.length - 1]).toContain("progress-agent completed");
    });

    it("calls onProgress with failure message after exhausting retries", async () => {
      const messages: string[] = [];
      await runner.run(
        async () => { throw new Error("boom"); },
        {
          name: "fail-agent",
          retries: 0,
          onProgress: (msg) => messages.push(msg),
        },
      );

      const lastMsg = messages[messages.length - 1];
      expect(lastMsg).toContain("fail-agent failed");
      expect(lastMsg).toContain("boom");
    });

    it("logs to build-log.jsonl", async () => {
      await runner.run(
        async () => "ok",
        { name: "log-agent" },
      );

      const logPath = path.join(tmpDir, ".planning", "artifacts", "build-log.jsonl");
      expect(fs.existsSync(logPath)).toBe(true);

      const lines = fs.readFileSync(logPath, "utf-8").trim().split("\n");
      expect(lines.length).toBeGreaterThanOrEqual(2);

      const firstEntry = JSON.parse(lines[0]);
      expect(firstEntry.agent).toBe("log-agent");
      expect(firstEntry.event).toBe("started");

      const lastEntry = JSON.parse(lines[lines.length - 1]);
      expect(lastEntry.event).toBe("completed");
    });
  });

  describe("runParallel()", () => {
    it("runs items concurrently respecting concurrency limit", async () => {
      let maxConcurrent = 0;
      let currentConcurrent = 0;

      const items = Array.from({ length: 6 }, (_, i) => ({
        name: `agent-${i}`,
        fn: async () => {
          currentConcurrent++;
          maxConcurrent = Math.max(maxConcurrent, currentConcurrent);
          await new Promise((r) => setTimeout(r, 50));
          currentConcurrent--;
          return i;
        },
      }));

      const results = await runner.runParallel(items, { concurrency: 3 });

      expect(results).toHaveLength(6);
      expect(maxConcurrent).toBeLessThanOrEqual(3);
      for (const r of results) {
        expect(r.status).toBe("completed");
      }
    });

    it("handles mixed success and failure", async () => {
      const items = [
        { name: "ok-1", fn: async () => "success-1" },
        { name: "fail-1", fn: async () => { throw new Error("fail"); } },
        { name: "ok-2", fn: async () => "success-2" },
      ];

      const results = await runner.runParallel(items, { concurrency: 3 });

      expect(results).toHaveLength(3);

      const okResults = results.filter((r) => r.status === "completed");
      const failResults = results.filter((r) => r.status === "failed");

      expect(okResults).toHaveLength(2);
      expect(failResults).toHaveLength(1);
      expect(failResults[0].agentName).toBe("fail-1");
      expect(failResults[0].error).toBe("fail");
    });

    it("calls onProgress for each item", async () => {
      const progressCalls: Array<{ name: string; msg: string }> = [];

      const items = [
        { name: "a", fn: async () => 1 },
        { name: "b", fn: async () => 2 },
      ];

      await runner.runParallel(items, {
        concurrency: 2,
        onProgress: (name, msg) => progressCalls.push({ name, msg }),
      });

      const aMessages = progressCalls.filter((c) => c.name === "a");
      const bMessages = progressCalls.filter((c) => c.name === "b");
      expect(aMessages.length).toBeGreaterThan(0);
      expect(bMessages.length).toBeGreaterThan(0);
    });
  });
});
