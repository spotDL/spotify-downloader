import { fileURLToPath } from "node:url";
import path from "node:path";
import { defineConfig, devices } from "@playwright/test";

// The e2e suite drives the REAL serving path: a seeded selfhost server
// (apps/server/scripts/serve_e2e.py) that also serves the embedded SPA (Task 12),
// so the browser talks to one origin, same as a self-hosted deploy. Fully offline
// — every provider is faked server-side. `make web-e2e` builds + embeds the SPA
// before Playwright starts this server.
const port = Number(process.env.SPOTDL_E2E_PORT ?? 8811);
const baseURL = `http://127.0.0.1:${port}`;
const repoRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../..",
);

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI
    ? [["list"], ["html", { open: "never" }]]
    : [["list"]],
  use: {
    baseURL,
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "uv run python apps/server/scripts/serve_e2e.py",
    cwd: repoRoot,
    url: `${baseURL}/api/v1/health`,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: { SPOTDL_E2E_PORT: String(port) },
  },
});
