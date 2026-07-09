import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["src/test/setup.ts"],
    // Unit tests live under src/. The Playwright e2e specs (e2e/) run separately
    // via `make web-e2e` and must not be collected by vitest.
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
  },
});
