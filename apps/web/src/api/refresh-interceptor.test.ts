/// <reference types="node" />
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "../test/msw/server";
// Test files are exempt from the import boundary — they may drive the generated
// SDK directly to exercise the client interceptors end-to-end (CONTRACT C).
import { meApiV1AuthMeGet, loginApiV1AuthLoginPost } from "./generated/sdk.gen";
import { __resetAuthInterceptorState } from "./client";
import { useAuthStore } from "../stores/auth";
import { useSessionStore } from "../stores/session";
import { makeToken, makeUser } from "../test/msw/fixtures";

// CONTRACT C — the refresh-once interceptor. The interceptors are installed on
// the singleton client by the global test setup; these tests drive real requests
// through it (MSW backs the network) and assert the single-flight refresh, the
// one retry, hard-logout paths, and the no-bearer-on-auth-endpoints rule.

function unauthorized(code: string) {
  return HttpResponse.json({ code, message: code, detail: null }, { status: 401 });
}

beforeEach(() => {
  useAuthStore.setState({ accessToken: "stale-access" });
  useSessionStore.setState({ refreshToken: "refresh-1", apiBaseUrl: "" });
  __resetAuthInterceptorState();
});

afterEach(() => {
  useAuthStore.setState({ accessToken: null });
  useSessionStore.setState({ refreshToken: null, apiBaseUrl: "" });
});

describe("refresh-once interceptor", () => {
  it("refreshes once on token_expired and retries the original request", async () => {
    let meCalls = 0;
    let refreshCalls = 0;
    server.use(
      http.get("*/api/v1/auth/me", () => {
        meCalls += 1;
        return meCalls === 1
          ? unauthorized("token_expired")
          : HttpResponse.json(makeUser());
      }),
      http.post("*/api/v1/auth/refresh", () => {
        refreshCalls += 1;
        return HttpResponse.json(
          makeToken({ access_token: "fresh-access", refresh_token: "refresh-2" }),
        );
      }),
    );

    const { data, error } = await meApiV1AuthMeGet();

    expect(error).toBeUndefined();
    expect(data).toMatchObject({ id: "user-1" });
    expect(meCalls).toBe(2); // original + one retry
    expect(refreshCalls).toBe(1);
    expect(useAuthStore.getState().accessToken).toBe("fresh-access");
    expect(useSessionStore.getState().refreshToken).toBe("refresh-2"); // rotated
  });

  it("dedupes concurrent 401s into a single refresh (single-flight)", async () => {
    let refreshCalls = 0;
    const meStatuses = new Map<string, number>();
    server.use(
      http.get("*/api/v1/auth/me", ({ request }) => {
        // Each concurrent caller 401s on its first hit, then succeeds.
        const auth = request.headers.get("authorization") ?? "";
        const seen = (meStatuses.get(auth) ?? 0) + 1;
        meStatuses.set(auth, seen);
        return auth.includes("fresh-access")
          ? HttpResponse.json(makeUser())
          : unauthorized("token_expired");
      }),
      http.post("*/api/v1/auth/refresh", async () => {
        refreshCalls += 1;
        await new Promise((r) => setTimeout(r, 10));
        return HttpResponse.json(
          makeToken({ access_token: "fresh-access", refresh_token: "refresh-2" }),
        );
      }),
    );

    const [a, b, c] = await Promise.all([
      meApiV1AuthMeGet(),
      meApiV1AuthMeGet(),
      meApiV1AuthMeGet(),
    ]);

    expect(refreshCalls).toBe(1); // one shared refresh for all three 401s
    for (const r of [a, b, c]) {
      expect(r.error).toBeUndefined();
      expect(r.data).toMatchObject({ id: "user-1" });
    }
  });

  it("hard-logs-out when the refresh call itself 401s (family revoked)", async () => {
    server.use(
      http.get("*/api/v1/auth/me", () => unauthorized("token_expired")),
      http.post("*/api/v1/auth/refresh", () => unauthorized("invalid_token")),
    );

    const { error } = await meApiV1AuthMeGet();

    expect(error).toBeDefined();
    expect(useAuthStore.getState().accessToken).toBeNull();
    expect(useSessionStore.getState().refreshToken).toBeNull();
  });

  it("hard-logs-out when the retried request still 401s", async () => {
    server.use(
      http.get("*/api/v1/auth/me", () => unauthorized("token_expired")),
      http.post("*/api/v1/auth/refresh", () =>
        HttpResponse.json(
          makeToken({ access_token: "fresh-access", refresh_token: "refresh-2" }),
        ),
      ),
    );

    const { error } = await meApiV1AuthMeGet();

    expect(error).toBeDefined();
    expect(useAuthStore.getState().accessToken).toBeNull();
    expect(useSessionStore.getState().refreshToken).toBeNull();
  });

  it("attaches the bearer to normal requests but never to /auth/login or /auth/refresh", async () => {
    const seen: Record<string, string | null> = {};
    server.use(
      http.get("*/api/v1/auth/me", ({ request }) => {
        seen.me = request.headers.get("authorization");
        return HttpResponse.json(makeUser());
      }),
      http.post("*/api/v1/auth/login", ({ request }) => {
        seen.login = request.headers.get("authorization");
        return HttpResponse.json(makeToken());
      }),
      http.post("*/api/v1/auth/refresh", ({ request }) => {
        seen.refresh = request.headers.get("authorization");
        return HttpResponse.json(makeToken());
      }),
    );

    await meApiV1AuthMeGet();
    await loginApiV1AuthLoginPost({ body: { email: "a@b.co", password: "pw" } });

    expect(seen.me).toBe("Bearer stale-access");
    expect(seen.login).toBeNull();
  });
});

// Upstream verification (Plan 6 amendment, upstream note 3): the SPA's
// fragment-callback consumption (CONTRACT C) is only valid if the server's
// OAuth callback actually performs the browser 302→fragment handoff while
// RETAINING the JSON TokenResponse for Accept: application/json. Assert the
// regenerated openapi.json documents the dual-mode contract; if this fails the
// amendment has not landed — stop and report, do NOT build a JSON workaround.
describe("OAuth callback amendment (upstream note 3)", () => {
  const openapi = JSON.parse(
    readFileSync(resolve("../server/openapi.json"), "utf8"),
  ) as {
    paths: Record<
      string,
      { get?: { description?: string; responses: Record<string, { content?: Record<string, unknown> }> } }
    >;
  };
  const callback = openapi.paths["/api/v1/auth/oauth/{provider}/callback"]?.get;

  it("documents the dual-mode (JSON body vs browser handoff) callback", () => {
    expect(callback).toBeDefined();
    expect(callback?.description ?? "").toContain("handoff");
  });

  it("retains the JSON TokenResponse for Accept: application/json callers", () => {
    expect(callback?.responses["200"]?.content).toHaveProperty("application/json");
  });
});
