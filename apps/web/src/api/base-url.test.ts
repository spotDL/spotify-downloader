import { afterEach, describe, expect, it } from "vitest";
import { createClientConfig, resolveHttpBase, resolveWsBase } from "./client";
import { useSessionStore } from "../stores/session";

// CONTRACT B — runtime API base-URL resolution (one build → any self-hosted
// server). `resolveHttpBase`/`resolveWsBase` are re-read per request; the
// Settings field (Task 10) writes `useSessionStore.apiBaseUrl`.

afterEach(() => {
  useSessionStore.getState().setApiBaseUrl("");
});

describe("resolveHttpBase / createClientConfig", () => {
  it("defaults to same-origin (empty base → server-relative /api/v1)", () => {
    // "" means the SPA talks to the origin that served it; the generated op
    // paths already carry the /api/v1 prefix, so requests hit /api/v1/... .
    expect(resolveHttpBase()).toBe("");
    expect(createClientConfig({}).baseUrl).toBe("");
  });

  it("normalizes an override by stripping trailing slashes", () => {
    useSessionStore.getState().setApiBaseUrl("https://nas.local:7070/");
    expect(resolveHttpBase()).toBe("https://nas.local:7070");

    useSessionStore.getState().setApiBaseUrl("https://nas.local:7070///");
    expect(resolveHttpBase()).toBe("https://nas.local:7070");
  });

  it("trims surrounding whitespace from an override", () => {
    useSessionStore.getState().setApiBaseUrl("  https://nas.local:7070  ");
    expect(resolveHttpBase()).toBe("https://nas.local:7070");
  });
});

describe("resolveWsBase (scheme mapping)", () => {
  it("maps same-origin to ws(s) from the page protocol", () => {
    // jsdom serves the suite over http, so the same-origin WS base is ws://.
    expect(resolveWsBase()).toBe(`ws://${location.host}`);
  });

  it("maps an https override to wss://", () => {
    useSessionStore.getState().setApiBaseUrl("https://nas.local:7070");
    expect(resolveWsBase()).toBe("wss://nas.local:7070");
  });

  it("maps an http override to ws://", () => {
    useSessionStore.getState().setApiBaseUrl("http://nas.local:7070");
    expect(resolveWsBase()).toBe("ws://nas.local:7070");
  });
});
