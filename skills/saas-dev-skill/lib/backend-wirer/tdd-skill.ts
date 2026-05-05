import Anthropic from "@anthropic-ai/sdk";
import type { BackendSpec } from "./types.js";
import { getAnthropicApiKey, getAnthropicBaseUrl } from "../env.js";

/**
 * superpowers:test-driven-development skill wrapper (Plan 05-05).
 *
 * Asks Claude to generate integration test scaffolding for a BackendSpec
 * BEFORE the implementation is generated. Fail-open: returns "" on error so
 * the pipeline can continue with its existing test generator.
 */

const MODEL = "claude-sonnet-4-5";

function getClient(): Anthropic {
  return new Anthropic({
    apiKey: getAnthropicApiKey(),
    baseURL: getAnthropicBaseUrl(),
  });
}

export async function queryTDDSkill(spec: BackendSpec): Promise<string> {
  try {
    const client = getClient();
    const response = await client.messages.create({
      model: MODEL,
      max_tokens: 2048,
      messages: [
        {
          role: "user",
          content: `Apply the superpowers:test-driven-development skill. Generate vitest integration tests for this backend spec BEFORE implementation exists. Cover happy path, auth failure, validation failure, and at least one edge case per endpoint.

${JSON.stringify(spec, null, 2)}

Output only the test file contents — no preamble.`,
        },
      ],
    });
    const block = response.content[0];
    return block && block.type === "text" ? block.text : "";
  } catch (err) {
    console.warn("[tdd-skill] unavailable:", (err as Error).message);
    return "";
  }
}
