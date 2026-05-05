import type { PageSpecFull } from "@shared/spec-schema.js";

// ─── Constants ────────────────────────────────────────────────────────────────

/**
 * Pages at or below this count are never chunked (D-24).
 */
const CHUNK_THRESHOLD = 25;

/**
 * Hard cap: no single chunk may exceed this many pages (AI context budget).
 */
const MAX_CHUNK_SIZE = 20;

/**
 * Domain classification patterns.
 * Pages are matched against each domain in order — first match wins.
 * "core-features" is the catch-all domain.
 */
const DOMAIN_PATTERNS: Record<string, RegExp[]> = {
  "auth-onboarding": [/\/(auth|login|signup|register|verify|forgot|reset)/i],
  "admin-settings": [/\/(admin|settings|preferences|config|profile)/i],
  "core-features": [/./], // catch-all for everything else
};

// ─── Domain Classification ────────────────────────────────────────────────────

/**
 * Classifies a page route into a named domain.
 * Returns the first domain whose patterns match the route.
 */
function classifyPageDomain(route: string): string {
  for (const [domain, patterns] of Object.entries(DOMAIN_PATTERNS)) {
    if (patterns.some((pattern) => pattern.test(route))) {
      return domain;
    }
  }
  return "core-features";
}

// ─── chunkSpecByDomain ────────────────────────────────────────────────────────

/**
 * Splits a large page spec array into domain-based chunks for sequential AI processing.
 *
 * D-24: If pages.length <= 25, returns [pages] (no chunking).
 * D-25: For 26+ pages, groups pages by domain and splits each group to stay
 *       under the MAX_CHUNK_SIZE hard cap (20 pages per chunk).
 *
 * Domain grouping ensures related pages (auth, admin, core features) stay together
 * for better AI context when processing each chunk.
 *
 * @param pages - Full array of parsed page specs
 * @param chunkSize - Target max pages per chunk (default 15, hard cap 20)
 * @returns Array of page chunks — each is a PageSpecFull[]
 */
export function chunkSpecByDomain(
  pages: PageSpecFull[],
  chunkSize: number = 15
): PageSpecFull[][] {
  // D-24: No chunking for specs at or below threshold
  if (pages.length <= CHUNK_THRESHOLD) {
    return [pages];
  }

  // Enforce hard cap
  const effectiveChunkSize = Math.min(chunkSize, MAX_CHUNK_SIZE);

  // Group pages by domain
  const domainGroups = new Map<string, PageSpecFull[]>();
  for (const domain of Object.keys(DOMAIN_PATTERNS)) {
    domainGroups.set(domain, []);
  }

  for (const page of pages) {
    const domain = classifyPageDomain(page.route);
    const group = domainGroups.get(domain) ?? [];
    group.push(page);
    domainGroups.set(domain, group);
  }

  // Split each domain group into chunks respecting effectiveChunkSize
  const chunks: PageSpecFull[][] = [];
  for (const group of domainGroups.values()) {
    if (group.length === 0) continue;

    if (group.length <= effectiveChunkSize) {
      chunks.push(group);
    } else {
      // Split large domain group into sub-chunks by priority order
      const sorted = [...group].sort((a, b) => a.priority - b.priority);
      for (let i = 0; i < sorted.length; i += effectiveChunkSize) {
        chunks.push(sorted.slice(i, i + effectiveChunkSize));
      }
    }
  }

  // Edge case: if all pages ended up in a single chunk larger than MAX_CHUNK_SIZE,
  // force-split it (shouldn't happen with proper domain classification, but safety net)
  const safeguardedChunks: PageSpecFull[][] = [];
  for (const chunk of chunks) {
    if (chunk.length > MAX_CHUNK_SIZE) {
      for (let i = 0; i < chunk.length; i += MAX_CHUNK_SIZE) {
        safeguardedChunks.push(chunk.slice(i, i + MAX_CHUNK_SIZE));
      }
    } else {
      safeguardedChunks.push(chunk);
    }
  }

  return safeguardedChunks;
}

// ─── chunkRawText ─────────────────────────────────────────────────────────────

/**
 * Pre-chunks raw text input at markdown heading boundaries before any AI call.
 *
 * Addresses the HIGH review concern: oversized raw input fails before chunking
 * helps. By splitting at heading boundaries first, we ensure the AI never
 * receives an input too large to process in a single pass.
 *
 * Split strategy:
 * 1. If text <= maxChunkSize, return [text] (no chunking needed)
 * 2. Split at heading boundaries (lines starting with # or ##)
 * 3. Group consecutive sections until adding another would exceed maxChunkSize
 * 4. If a single section exceeds maxChunkSize, split at paragraph boundaries
 *
 * @param rawText - Raw spec text in any markdown format
 * @param maxChunkSize - Maximum characters per chunk (default 15000)
 * @returns Array of text chunks, each under maxChunkSize
 */
export function chunkRawText(
  rawText: string,
  maxChunkSize: number = 15000
): string[] {
  // No chunking needed
  if (rawText.length <= maxChunkSize) {
    return [rawText];
  }

  // Split into sections at heading boundaries
  // We detect lines that start with # or ## (with optional leading whitespace)
  const lines = rawText.split("\n");
  const sections: string[] = [];
  let currentSection = "";

  for (const line of lines) {
    const isHeading = /^#{1,2}\s/.test(line);

    if (isHeading && currentSection.length > 0) {
      // Save current section and start a new one at this heading
      sections.push(currentSection);
      currentSection = line + "\n";
    } else {
      currentSection += line + "\n";
    }
  }

  // Push the last section
  if (currentSection.length > 0) {
    sections.push(currentSection);
  }

  // Group sections into chunks
  const chunks: string[] = [];
  let currentChunk = "";

  for (const section of sections) {
    if (section.length > maxChunkSize) {
      // Single section too large — split at paragraph boundaries, but only
      // at boundaries that are NOT inside a JSON object/array or fenced code
      // block. Splitting inside a structure would break JSON parsing in the
      // downstream restructure step.
      if (currentChunk.length > 0) {
        chunks.push(currentChunk);
        currentChunk = "";
      }
      const paragraphChunks = splitSafely(section, maxChunkSize);
      chunks.push(...paragraphChunks);
    } else if (currentChunk.length + section.length > maxChunkSize) {
      // Adding this section would exceed the limit — flush current chunk
      if (currentChunk.length > 0) {
        chunks.push(currentChunk);
      }
      currentChunk = section;
    } else {
      currentChunk += section;
    }
  }

  // Flush the last chunk
  if (currentChunk.length > 0) {
    chunks.push(currentChunk);
  }

  return chunks.filter((c) => c.trim().length > 0);
}

/**
 * Tracks whether the parser cursor is currently inside a JSON object/array or
 * a fenced code block. Used to refuse splits at unsafe boundaries.
 */
interface StructureDepth {
  brace: number;   // {
  bracket: number; // [
  fence: boolean;  // inside ```...```
}

function updateDepth(depth: StructureDepth, line: string): StructureDepth {
  let brace = depth.brace;
  let bracket = depth.bracket;
  let fence = depth.fence;

  // Toggle fenced code blocks first — content inside them is opaque to JSON
  // tracking (a stray { in prose-mode markdown should not lock the parser).
  if (/^\s*```/.test(line)) {
    fence = !fence;
    return { brace, bracket, fence };
  }
  if (fence) return { brace, bracket, fence };

  // Walk the line counting top-level structure tokens. Skip what's inside
  // string literals (rough heuristic: ignore everything between unescaped
  // double quotes on a single line).
  let inString = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '"' && line[i - 1] !== "\\") {
      inString = !inString;
      continue;
    }
    if (inString) continue;
    if (ch === "{") brace++;
    else if (ch === "}") brace = Math.max(0, brace - 1);
    else if (ch === "[") bracket++;
    else if (ch === "]") bracket = Math.max(0, bracket - 1);
  }
  return { brace, bracket, fence };
}

function isAtSafeBoundary(depth: StructureDepth): boolean {
  return depth.brace === 0 && depth.bracket === 0 && !depth.fence;
}

/**
 * JSON/markdown-aware splitter. Walks the input line-by-line, tracks structural
 * depth, and only flushes a chunk when the cursor is at a safe boundary (no
 * open braces/brackets, not inside a fenced code block) AND a paragraph break
 * has just been seen.
 *
 * If a single structural unit exceeds maxChunkSize, the entire input is
 * returned as one oversized chunk with a warning logged. Splitting mid-JSON
 * is never acceptable — better to send one oversized chunk than corrupt
 * structure that downstream Zod validation will reject anyway.
 */
function splitSafely(text: string, maxChunkSize: number): string[] {
  const lines = text.split("\n");
  const chunks: string[] = [];
  let currentChunk = "";
  let depth: StructureDepth = { brace: 0, bracket: 0, fence: false };
  let lastFlushIdx = 0;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    depth = updateDepth(depth, line);
    currentChunk += line + "\n";

    const overBudget = currentChunk.length >= maxChunkSize;
    const sawParagraphBreak =
      i + 1 < lines.length && lines[i + 1].trim() === "";
    const safeHere = isAtSafeBoundary(depth);

    if (overBudget && safeHere && sawParagraphBreak) {
      chunks.push(currentChunk);
      currentChunk = "";
      lastFlushIdx = i + 1;
    }
  }

  if (currentChunk.length > 0) chunks.push(currentChunk);

  // If we couldn't safely split at all (single oversized structural unit),
  // emit a warning and return the whole thing as one chunk. The downstream
  // LLM call will deal with the oversize — better than corrupting JSON.
  if (chunks.length === 1 && chunks[0].length > maxChunkSize) {
    console.warn(
      `[chunk-spec] Could not split a ${chunks[0].length}-char section without ` +
        `breaking JSON/code structure. Passing through whole. ` +
        `(maxChunkSize=${maxChunkSize}, lastSafeBoundary=line ${lastFlushIdx})`,
    );
  }

  return chunks;
}
