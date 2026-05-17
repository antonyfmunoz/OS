/**
 * claude-subprocess.ts — Drop-in replacement for @anthropic-ai/sdk.
 *
 * Routes all LLM calls through `claude -p --output-format json` subprocess,
 * authenticated via CLAUDE_CODE_OAUTH_TOKEN (Max subscription).
 * No Anthropic API key required.
 *
 * Provides the same interface as the Anthropic SDK's messages.create()
 * and messages.stream() so existing code needs minimal changes.
 */

import { execFile } from "node:child_process";
import { readFileSync } from "node:fs";

const TIMEOUT_MS = Number(process.env.CC_SDK_TIMEOUT_SECONDS ?? 180) * 1000;

interface MessageParam {
  role: "user" | "assistant";
  content: string | Array<{ type: string; text?: string; source?: unknown }>;
}

interface CreateParams {
  model: string;
  max_tokens: number;
  system?: string;
  messages: MessageParam[];
  temperature?: number;
}

interface TextBlock {
  type: "text";
  text: string;
}

interface MessageResponse {
  id: string;
  content: TextBlock[];
  model: string;
  stop_reason: string;
  usage: { input_tokens: number; output_tokens: number };
}

interface StreamHandle {
  finalMessage(): Promise<MessageResponse>;
}

function findOAuthToken(): string {
  if (process.env.CLAUDE_CODE_OAUTH_TOKEN) {
    return process.env.CLAUDE_CODE_OAUTH_TOKEN;
  }

  // Walk ancestor /proc to find token (same strategy as Python cc_sdk)
  try {
    let pid = process.ppid;
    const visited = new Set<number>();
    while (pid > 1 && !visited.has(pid)) {
      visited.add(pid);
      try {
        const environ = readFileSync(`/proc/${pid}/environ`);
        const entries = environ.toString().split("\0");
        for (const entry of entries) {
          if (entry.startsWith("CLAUDE_CODE_OAUTH_TOKEN=")) {
            return entry.slice("CLAUDE_CODE_OAUTH_TOKEN=".length);
          }
        }
        const stat = readFileSync(`/proc/${pid}/stat`, "utf-8");
        const parts = stat.split(" ");
        pid = Number(parts[3]); // ppid field
      } catch {
        break;
      }
    }
  } catch {
    // /proc walk failed — not on Linux or permission denied
  }

  throw new Error(
    "[claude-subprocess] No CLAUDE_CODE_OAUTH_TOKEN found in env or ancestor processes. " +
    "Set it explicitly or run inside a Claude Code session."
  );
}

function buildPrompt(params: CreateParams): string {
  const parts: string[] = [];

  if (params.system) {
    parts.push(`<system>\n${params.system}\n</system>\n`);
  }

  for (const msg of params.messages) {
    const text = typeof msg.content === "string"
      ? msg.content
      : msg.content
          .filter((b) => b.type === "text" && b.text)
          .map((b) => b.text)
          .join("\n");
    parts.push(`<${msg.role}>\n${text}\n</${msg.role}>`);
  }

  return parts.join("\n");
}

const MODEL_MAP: Record<string, string> = {
  "claude-haiku-4-5-20251001": "haiku",
  "claude-sonnet-4-5": "sonnet",
  "claude-sonnet-4-5-20250514": "sonnet",
  "claude-sonnet-4-6": "sonnet",
  "claude-opus-4-6": "opus",
  "claude-opus-4-5-20250514": "opus",
};

function mapModel(requested: string): string {
  return MODEL_MAP[requested] ?? "sonnet";
}

function callClaude(params: CreateParams): Promise<MessageResponse> {
  return new Promise((resolve, reject) => {
    const token = findOAuthToken();
    const prompt = buildPrompt(params);
    const modelAlias = mapModel(params.model);

    const args = [
      "-p", prompt,
      "--output-format", "json",
      "--model", modelAlias,
      "--max-turns", "1",
    ];

    const env: Record<string, string> = { ...process.env as Record<string, string> };
    env.CLAUDE_CODE_OAUTH_TOKEN = token;
    delete env.ANTHROPIC_API_KEY;

    console.log(`[claude-subprocess] calling claude --model ${modelAlias} (requested: ${params.model})`);

    execFile("claude", args, {
      timeout: TIMEOUT_MS,
      maxBuffer: 10 * 1024 * 1024, // 10MB
      env,
    }, (err, stdout, stderr) => {
      if (err) {
        reject(new Error(`[claude-subprocess] CLI failed: ${err.message}\nstderr: ${stderr}`));
        return;
      }

      try {
        const parsed = JSON.parse(stdout);

        if (parsed.is_error) {
          reject(new Error(
            `[claude-subprocess] CLI error: ${parsed.result ?? "unknown"} (status: ${parsed.api_error_status ?? "none"})`
          ));
          return;
        }

        const text = parsed.result ?? "";
        const usage = parsed.usage ?? {};

        resolve({
          id: parsed.session_id ?? `cli-${Date.now()}`,
          content: [{ type: "text", text }],
          model: params.model,
          stop_reason: parsed.stop_reason ?? "end_turn",
          usage: {
            input_tokens: usage.input_tokens ?? 0,
            output_tokens: usage.output_tokens ?? 0,
          },
        });
      } catch (parseErr) {
        reject(new Error(
          `[claude-subprocess] Failed to parse CLI output: ${parseErr}\nraw: ${stdout.slice(0, 500)}`
        ));
      }
    });
  });
}

class Messages {
  async create(params: CreateParams): Promise<MessageResponse> {
    return callClaude(params);
  }

  stream(params: CreateParams): StreamHandle {
    const promise = callClaude(params);
    return {
      finalMessage: () => promise,
    };
  }
}

/**
 * Drop-in replacement for `new Anthropic()`.
 *
 * Usage:
 *   import { ClaudeSubprocess as Anthropic } from "../claude-subprocess.js";
 *   const client = new Anthropic();
 *   const response = await client.messages.create({ ... });
 */
export class ClaudeSubprocess {
  readonly messages = new Messages();

  constructor(_opts?: { apiKey?: string; baseURL?: string }) {
    // Options ignored — auth is via OAuth token
  }
}

// Namespace for Anthropic.MessageParam, Anthropic.ImageBlockParam etc.
// Allows `const msgs: Anthropic.MessageParam[]` to keep working
export namespace ClaudeSubprocess {
  export type MessageParam = {
    role: "user" | "assistant";
    content: string | Array<{ type: string; text?: string; source?: unknown }>;
  };
  export type ImageBlockParam = {
    type: "image";
    source: { type: "base64"; media_type: string; data: string };
  };
  export type TextBlock = { type: "text"; text: string };
}

// Default export for drop-in compatibility with `import Anthropic from "@anthropic-ai/sdk"`
export default ClaudeSubprocess;
