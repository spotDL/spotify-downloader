import { describe, it, expect } from "vitest";
import { resolveApiBaseUrl } from "../../src/api/client";

describe("resolveApiBaseUrl", () => {
  it("uses proxy base when empty", () => {
    expect(resolveApiBaseUrl("")).toBe("/api/v1");
  });

  it("handles absolute http url", () => {
    expect(resolveApiBaseUrl("http://localhost:8000")).toBe(
      "http://localhost:8000/api/v1"
    );
  });

  it("handles absolute https url with trailing slash", () => {
    expect(resolveApiBaseUrl("https://example.com/")).toBe(
      "https://example.com/api/v1"
    );
  });

  it("handles relative path", () => {
    expect(resolveApiBaseUrl("backend")).toBe("/backend/api/v1");
  });
});
