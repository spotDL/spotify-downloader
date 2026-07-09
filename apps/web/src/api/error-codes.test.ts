import { describe, expect, it } from "vitest";
import type { ErrorCode } from "./generated/types.gen";
// Raw-text import of the generated types module (Vite `?raw`) — `ErrorCode` is a
// pure type union with no runtime representation, so we assert against the
// artifact's text.
import typesRaw from "./generated/types.gen.ts?raw";

// Guards CONTRACT F's table completeness (the ERROR_MESSAGES map in Task 5 is a
// `Record<ErrorCode, ...>`, so the generated union is its source of truth). The
// union must be non-empty and every member must be a string literal.
function extractErrorCodeMembers(): string[] {
  const match = typesRaw.match(/export type ErrorCode =\s*([^;]+);/);
  if (!match) throw new Error("ErrorCode union not found in types.gen.ts");
  return match[1]
    .split("|")
    .map((part) => part.trim())
    .filter((part) => part.length > 0)
    .map((literal) => {
      const m = literal.match(/^'([^']*)'$/);
      if (!m) {
        throw new Error(`ErrorCode member is not a string literal: ${literal}`);
      }
      return m[1];
    });
}

describe("generated ErrorCode union", () => {
  it("is non-empty", () => {
    expect(extractErrorCodeMembers().length).toBeGreaterThan(0);
  });

  it("every member is a non-empty string", () => {
    for (const member of extractErrorCodeMembers()) {
      expect(typeof member).toBe("string");
      expect(member.length).toBeGreaterThan(0);
    }
  });

  it("includes the closed-vocabulary codes CONTRACT F depends on", () => {
    const members = extractErrorCodeMembers();
    // Spot-check a representative subset spanning Plans 5/6/7 so a regenerated
    // client that silently drops the vocabulary fails here.
    const expected: ErrorCode[] = [
      "not_found",
      "validation_error",
      "authentication_required",
      "token_expired",
      "download_failed",
    ];
    for (const code of expected) {
      expect(members).toContain(code);
    }
  });
});
