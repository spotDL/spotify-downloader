/// <reference types="node" />
import { readFileSync, readdirSync } from "node:fs";
import { join, resolve } from "node:path";
import { describe, expect, it } from "vitest";

// CONTRACT A2 / spec §3 — the machine backstop for "server state only via
// TanStack Query over the generated client". Statically scans src/** (excluding
// src/api/**, generated code, and test files) and fails on:
//   • a raw `fetch(` or `new WebSocket(` (the sanctioned WS lives in src/api/ws.ts)
//   • a VALUE import from src/api/generated (components consume src/api/{queries,
//     mutations,ws} hooks; only `import type … from …/generated/types.gen` is
//     allowed anywhere, per CONTRACT A2)
//   • any import of ws-types.gen.ts outside src/api/**
// This is the authoritative enforcement; the oxlint rule is best-effort.

const SRC = resolve("src");

function walk(dir: string): string[] {
  const out: string[] = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) {
      out.push(...walk(full));
    } else if (entry.isFile()) {
      out.push(full);
    }
  }
  return out;
}

function isExempt(path: string): boolean {
  const rel = path.slice(SRC.length + 1);
  return (
    // The API layer legitimately owns fetch/WebSocket and the generated imports.
    rel.startsWith("api/") ||
    // Test support + test files legitimately drive the generated SDK directly.
    rel.startsWith("test/") ||
    rel.endsWith(".test.ts") ||
    rel.endsWith(".test.tsx") ||
    // Generated router tree (git-ignored, regenerated) is not hand-authored.
    rel.endsWith(".gen.ts") ||
    rel.endsWith(".gen.tsx")
  );
}

const IMPORT_RE = /import\s+(type\s+)?[\s\S]*?from\s*["']([^"']+)["']/g;
const FETCH_RE = /\bfetch\s*\(/;
const WEBSOCKET_RE = /new\s+WebSocket\s*\(/;

function importViolations(source: string): string[] {
  const violations: string[] = [];
  for (const match of source.matchAll(IMPORT_RE)) {
    const isTypeOnly = match[1] !== undefined;
    const spec = match[2];
    if (spec.includes("ws-types.gen")) {
      violations.push(`imports ws-types.gen (${spec})`);
      continue;
    }
    if (spec.includes("api/generated") || /(^|\/)generated\//.test(spec)) {
      const typesOnly = isTypeOnly && /types\.gen(\.ts)?$/.test(spec);
      if (!typesOnly) violations.push(`imports generated code (${spec})`);
    }
  }
  return violations;
}

const files = walk(SRC).filter(
  (f) => (f.endsWith(".ts") || f.endsWith(".tsx")) && !isExempt(f),
);

describe("api import boundary", () => {
  it("scans a non-trivial set of app files", () => {
    // Guard against a broken walk/exempt that silently passes by scanning nothing.
    expect(files.length).toBeGreaterThan(5);
  });

  it.each(files)("%s stays within the API boundary", (file) => {
    const source = readFileSync(file, "utf8");
    const problems: string[] = [];
    if (FETCH_RE.test(source)) problems.push("uses raw fetch(");
    if (WEBSOCKET_RE.test(source)) problems.push("constructs a WebSocket");
    problems.push(...importViolations(source));
    expect(problems, `${file}: ${problems.join("; ")}`).toEqual([]);
  });
});
