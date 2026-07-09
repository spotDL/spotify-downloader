import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { resolveWsBase } from "./client";
import { useAuthStore } from "../stores/auth";
import { toast } from "../components/Toasts";
import { WS_PROTOCOL_VERSION } from "./ws-protocol";
import type { WsMessage } from "./ws-types.gen";
import { applyWsMessage } from "./ws-reducer";

// The sanctioned single WebSocket (spec §3): all other server-state flows
// through generated Query hooks. The server mounts the fan-out at `/ws/progress`
// (no `/api/v1` prefix) and authenticates it with a `?token=` query param
// (Plan 7 browser-WS auth). Missing/invalid token → the server closes 4401.
export const WS_PATH = "/ws/progress";
export const BACKOFF_BASE_MS = 500;
export const BACKOFF_CAP_MS = 30_000;
const WS_AUTH_FAILED = 4401;

/**
 * Reconnect backoff (CONTRACT E): exponential in the attempt count with equal
 * jitter (½..1× of the exponential term), capped at 30s. The attempt counter is
 * reset to 0 on a compatible `hello`, so a healthy reconnect starts fresh.
 */
export function backoffDelay(
  attempt: number,
  random: () => number = Math.random,
): number {
  const exponential = BACKOFF_BASE_MS * 2 ** attempt;
  const jittered = exponential * (0.5 + 0.5 * random());
  return Math.min(BACKOFF_CAP_MS, Math.round(jittered));
}

/** The progress socket URL for the current API base + access token (if any). */
export function progressSocketUrl(): string {
  const token = useAuthStore.getState().accessToken;
  const query = token ? `?token=${encodeURIComponent(token)}` : "";
  return `${resolveWsBase()}${WS_PATH}${query}`;
}

/**
 * Mount-once live-progress socket: opens the WS, folds every frame through the
 * pure {@link applyWsMessage} cache reducer, verifies the `hello` protocol
 * version, reconnects with jittered backoff, and tears down on unmount. A
 * protocol mismatch or a 4401 (auth) close stops reconnecting and toasts.
 */
export function useProgressSocket(): void {
  const queryClient = useQueryClient();
  const stateRef = useRef({
    socket: null as WebSocket | null,
    timer: null as ReturnType<typeof setTimeout> | null,
    attempt: 0,
    stopped: false,
  });

  useEffect(() => {
    const state = stateRef.current;
    state.stopped = false;
    state.attempt = 0;

    function stop(): void {
      state.stopped = true;
      if (state.timer) {
        clearTimeout(state.timer);
        state.timer = null;
      }
      const socket = state.socket;
      state.socket = null;
      if (socket) {
        socket.onclose = null;
        socket.onmessage = null;
        socket.onerror = null;
        socket.onopen = null;
        try {
          socket.close();
        } catch {
          /* already closing/closed */
        }
      }
    }

    function scheduleReconnect(): void {
      if (state.stopped) return;
      const delay = backoffDelay(state.attempt);
      state.attempt += 1;
      state.timer = setTimeout(connect, delay);
    }

    function connect(): void {
      if (state.stopped) return;
      let socket: WebSocket;
      try {
        socket = new WebSocket(progressSocketUrl());
      } catch {
        scheduleReconnect();
        return;
      }
      state.socket = socket;

      socket.onmessage = (event: MessageEvent) => {
        let msg: WsMessage;
        try {
          msg = JSON.parse(String(event.data)) as WsMessage;
        } catch {
          return; // ignore non-JSON frames
        }
        const result = applyWsMessage(queryClient, msg);
        if (result.type === "hello") {
          if (result.compatible) {
            state.attempt = 0; // healthy connection → reset backoff
          } else {
            toast.error(
              `This app speaks live-progress protocol v${WS_PROTOCOL_VERSION}, but the server sent v${result.version ?? "?"}. Reload after updating.`,
            );
            stop();
          }
        }
      };

      socket.onclose = (event: CloseEvent) => {
        state.socket = null;
        if (state.stopped) return;
        if (event.code === WS_AUTH_FAILED) {
          toast.warn("Sign in to see live download progress.");
          stop();
          return;
        }
        scheduleReconnect();
      };

      socket.onerror = () => {
        // A failed connection also fires `onclose`, where reconnection is
        // handled — nothing to do here beyond swallowing the error event.
      };
    }

    connect();
    return stop;
    // Mount-once: the socket lifecycle is self-managed through `stateRef`, and
    // `queryClient` is stable for the app's lifetime.
  }, [queryClient]);
}
