import { describe, expect, it } from "vitest";
// Raw-text imports (Vite `?raw`) keep this in the browser/vite typing surface —
// no node:fs, so the file typechecks under tsconfig.app.json.
import indexRaw from "./generated/index.ts?raw";
import wsTypesRaw from "./ws-types.gen.ts?raw";

// Cheap tamper/existence check for the checked-in generated artifacts
// (CONTRACT A3). `make web-clients-check` is the authoritative git-diff guard;
// this test is the local backstop for runs where git-diff isn't available.
const cases: ReadonlyArray<readonly [string, string]> = [
  ["generated/index.ts", indexRaw],
  ["ws-types.gen.ts", wsTypesRaw],
];

describe("generated artifacts", () => {
  for (const [name, text] of cases) {
    it(`${name} is non-empty and carries the @generated banner`, () => {
      expect(text.length).toBeGreaterThan(0);
      expect(text).toContain("// @generated");
    });
  }
});
