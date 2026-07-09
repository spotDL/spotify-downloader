import "@testing-library/jest-dom/vitest";
import { afterAll, afterEach, beforeAll } from "vitest";
import { cleanup } from "@testing-library/react";
import { server } from "./msw/server";
import { client } from "../api/generated/client.gen";

// In a real browser the client's same-origin base ("") yields relative request
// URLs the browser resolves against `document`. Under jsdom the runtime `fetch`
// is node/undici, which rejects relative URLs ("Failed to parse URL"). Point the
// generated client at the jsdom origin so requests are absolute; MSW's
// `*/api/v1/...` patterns still match. This does NOT touch resolveHttpBase (the
// CONTRACT B logic is unit-tested directly in base-url.test.ts).
client.setConfig({ baseUrl: location.origin });

// jsdom does not implement matchMedia; ThemeProvider (and other components)
// depend on it. Provide a no-op stub so `"system"` theme resolution works.
if (typeof window !== "undefined" && !window.matchMedia) {
  window.matchMedia = (query: string): MediaQueryList => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  });
}

// MSW: the default test suite is fully offline (no real network).
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  cleanup();
  server.resetHandlers();
});
afterAll(() => server.close());
