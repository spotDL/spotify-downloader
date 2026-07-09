import { describe, expect, it } from "vitest";
import type { ErrorCode } from "./generated/types.gen";
// `ErrorCode` is a pure type union (no runtime value), so — as in
// error-codes.test.ts — we read the members from the generated artifact's text
// and assert the CONTRACT F table covers every one.
import typesRaw from "./generated/types.gen.ts?raw";
import {
  ApiError,
  ERROR_MESSAGES,
  ERROR_SEVERITY,
  messageForApiError,
  severityForApiError,
} from "./errors";

function errorCodeMembers(): string[] {
  const match = typesRaw.match(/export type ErrorCode =\s*([^;]+);/);
  if (!match) throw new Error("ErrorCode union not found in types.gen.ts");
  return match[1]
    .split("|")
    .map((part) => part.trim().replace(/^'|'$/g, ""))
    .filter((part) => part.length > 0);
}

describe("CONTRACT F error table", () => {
  const codes = errorCodeMembers();

  it("covers every generated ErrorCode with a message", () => {
    expect(codes.length).toBeGreaterThan(0);
    for (const code of codes) {
      expect(ERROR_MESSAGES).toHaveProperty(code);
    }
  });

  it("covers every generated ErrorCode with a severity", () => {
    for (const code of codes) {
      expect(ERROR_SEVERITY).toHaveProperty(code);
    }
  });

  it("renders a non-empty user-facing message for each code", () => {
    for (const code of codes) {
      const e = new ApiError(code as ErrorCode, "boom", null, 400);
      expect(messageForApiError(e)).not.toBe("");
      expect(severityForApiError(e)).toMatch(/^(error|warn|info)$/);
    }
  });

  it("interpolates detail into the rate_limited / download_failed copy", () => {
    const rate = new ApiError("rate_limited", "", { retry_after: 12 }, 429);
    expect(messageForApiError(rate)).toContain("12s");

    const failed = new ApiError("download_failed", "", { step: "convert" }, 500);
    expect(messageForApiError(failed)).toContain("convert");
  });

  it("degrades gracefully for an unknown (future-server) code", () => {
    // A server ahead of the app can emit a code the table doesn't know; the
    // renderer must not throw and must still say something.
    const unknown = new ApiError("some_new_code" as ErrorCode, "detail", null, 400);
    expect(messageForApiError(unknown)).toContain("some_new_code");
    expect(severityForApiError(unknown)).toBe("error");
  });
});
