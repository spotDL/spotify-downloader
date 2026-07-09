import { defineConfig } from "@hey-api/openapi-ts";

// CONTRACT A2 — deterministic generation of the checked-in TS client from the
// server's exported openapi.json. `postProcess: []` disables all formatting /
// linting post-passes (the non-deprecated form of the CONTRACT's `format:false`
// / `lint:false`) so the output stays byte-stable — formatting is delegated to
// the oxlint-ignore, and `make web-clients` twice yields an empty git diff.
export default defineConfig({
  input: "../server/openapi.json",
  output: { path: "src/api/generated", postProcess: [] },
  plugins: [
    "@hey-api/typescript",
    "@hey-api/sdk",
    { name: "@hey-api/client-fetch", runtimeConfigPath: "./src/api/client.ts" },
    "@tanstack/react-query",
  ],
});
