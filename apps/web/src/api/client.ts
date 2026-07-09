// Hand-written client-fetch runtime configuration (CONTRACT B / CONTRACT C).
//
// This module is imported by the GENERATED client (`generated/client.gen.ts`)
// via `openapi-ts.config.ts`'s `runtimeConfigPath`, so it must have no import
// cycle back into the generated SDK. It exports:
//   - `resolveHttpBase()` / `resolveWsBase()` — the runtime API-base-URL
//     resolution (one build → any self-hosted server, spec §8).
//   - `createClientConfig` — hey-api's runtime config hook; sets the initial
//     `baseUrl` to `resolveHttpBase() + "/api/v1"`.
//
// The refresh-once auth interceptors (CONTRACT C) and the per-request baseUrl
// re-read land in Task 4; this is the skeleton that lets generation resolve.
// @hey-api/openapi-ts v0.99 bundles the client-fetch runtime into
// `generated/client/`, so the runtime-config type comes from there (a type-only
// import — no runtime cycle with the generated client that imports us back).
import type { CreateClientConfig } from "./generated/client";
import { useSessionStore } from "../stores/session";

/**
 * Resolve the HTTP origin the API lives at.
 *
 * Default (`apiBaseUrl === ""`) ⇒ `""` (same-origin — the SPA is served BY the
 * server it talks to). A non-empty override is normalized (trailing slashes
 * stripped) and points every request at that origin.
 */
export function resolveHttpBase(): string {
  const override = useSessionStore.getState().apiBaseUrl.trim();
  return override === "" ? "" : override.replace(/\/+$/, "");
}

/**
 * Resolve the WebSocket origin, mapped from the HTTP base:
 *   same-origin  ⇒ ws(s)://<location.host> per the page protocol
 *   http override ⇒ ws://…, https override ⇒ wss://…
 */
export function resolveWsBase(): string {
  const http = resolveHttpBase();
  if (http === "") {
    const scheme = location.protocol === "https:" ? "wss" : "ws";
    return `${scheme}://${location.host}`;
  }
  return http.replace(/^http/, "ws");
}

// The client's `baseUrl` is the ORIGIN only. The server's exported openapi.json
// already carries the `/api/v1` prefix in every operation path (e.g.
// `/api/v1/config`), so the generated SDK urls include it — appending `/api/v1`
// here would double-prefix. Effective request URL = resolveHttpBase() +
// "/api/v1/<op>", i.e. same-origin `/api/v1/...` by default (CONTRACT B intent).
export const createClientConfig: CreateClientConfig = (config) => ({
  ...config,
  baseUrl: resolveHttpBase(),
});
