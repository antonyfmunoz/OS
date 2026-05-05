import { restructureSpec } from "./restructure-spec.js";
import type { SpecOutput } from "@shared/spec-schema.js";

/**
 * Maximum raw input size in characters (100KB).
 * Oversized input is rejected before any AI call to prevent excessive token usage
 * and ensure reliable parsing. For specs in the 26-100KB range, Plan 02-02's
 * chunkSpecByDomain handles domain-aware splitting.
 */
export const MAX_RAW_INPUT_SIZE = 100_000;

/**
 * Parse raw spec text into a validated SpecOutput.
 *
 * This is the public entry point for the spec parsing pipeline:
 * 1. Validates input is non-empty
 * 2. Enforces size guard (rejects > 100KB before any AI call)
 * 3. Delegates to restructureSpec for AI restructuring and validation
 *
 * @param rawInput - Raw spec text in any format (markdown, plain text, Notion export, etc.)
 * @returns Validated SpecOutput with all pages, shared components, and suggested order
 * @throws Error if input is empty, exceeds MAX_RAW_INPUT_SIZE, or AI restructuring fails
 */
export async function parseSpec(rawInput: string): Promise<SpecOutput> {
  if (!rawInput || rawInput.trim().length === 0) {
    throw new Error("Input spec cannot be empty. Please provide a spec document.");
  }

  if (rawInput.length > MAX_RAW_INPUT_SIZE) {
    throw new Error(
      `Input exceeds maximum size of ${MAX_RAW_INPUT_SIZE} characters. For very large specs, consider breaking into sections.`
    );
  }

  return restructureSpec(rawInput);
}
