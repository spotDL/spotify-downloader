import { afterEach, describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";
import { renderHook } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BACKOFF_CAP_MS, backoffDelay, useProgressSocket } from "./ws";
import { WS_PROTOCOL_VERSION } from "./ws-protocol";
import { MockWebSocket, installMockWebSocket } from "../test/mock-websocket";
import { toast } from "../components/Toasts";
import { useAuthStore } from "../stores/auth";

// The WS tests mock the socket per the CONTRACT — no real server. Each test
// drives the captured MockWebSocket instance and uses fake timers to observe the
// reconnect schedule.

function makeWrapper() {
  const queryClient = new QueryClient();
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

let restoreSocket: (() => void) | null = null;

afterEach(() => {
  restoreSocket?.();
  restoreSocket = null;
  vi.useRealTimers();
  vi.restoreAllMocks();
  useAuthStore.getState().reset();
});

describe("backoffDelay", () => {
  it("grows exponentially with equal jitter and caps at 30s", () => {
    expect(backoffDelay(0, () => 0)).toBe(250); // ½ × 500
    expect(backoffDelay(0, () => 1)).toBe(500); // 1 × 500
    expect(backoffDelay(1, () => 0)).toBe(500); // ½ × 1000
    expect(backoffDelay(1, () => 1)).toBe(1000); // 1 × 1000
    // A large attempt is clamped to the 30s cap for any jitter value.
    expect(backoffDelay(20, () => 0)).toBe(BACKOFF_CAP_MS);
    expect(backoffDelay(20, () => 1)).toBe(BACKOFF_CAP_MS);
  });
});

describe("useProgressSocket", () => {
  it("stops reconnecting and toasts on a protocol-version mismatch", () => {
    restoreSocket = installMockWebSocket();
    const errorSpy = vi.spyOn(toast, "error").mockReturnValue("t");
    vi.useFakeTimers();

    renderHook(() => useProgressSocket(), { wrapper: makeWrapper() });
    const socket = MockWebSocket.instances[0];
    socket.emitMessage({ type: "hello", protocol_version: WS_PROTOCOL_VERSION + 1 });

    expect(errorSpy).toHaveBeenCalledTimes(1);
    // No reconnect is ever scheduled after a fatal protocol mismatch.
    vi.advanceTimersByTime(BACKOFF_CAP_MS * 2);
    expect(MockWebSocket.instances).toHaveLength(1);
  });

  it("reconnects with backoff after an unexpected close", () => {
    restoreSocket = installMockWebSocket();
    vi.useFakeTimers();

    renderHook(() => useProgressSocket(), { wrapper: makeWrapper() });
    expect(MockWebSocket.instances).toHaveLength(1);

    MockWebSocket.instances[0].emitClose(1006); // abnormal close
    expect(MockWebSocket.instances).toHaveLength(1); // scheduled, not immediate
    vi.advanceTimersByTime(BACKOFF_CAP_MS); // past the first backoff window
    expect(MockWebSocket.instances.length).toBeGreaterThanOrEqual(2);
  });

  it("resets backoff after a compatible hello", () => {
    restoreSocket = installMockWebSocket();
    vi.useFakeTimers();

    renderHook(() => useProgressSocket(), { wrapper: makeWrapper() });
    // Drop several times to grow the backoff, then a good hello resets it so the
    // next reconnect is fast again.
    MockWebSocket.instances[0].emitClose(1006);
    vi.advanceTimersByTime(BACKOFF_CAP_MS);
    const second = MockWebSocket.instances[1];
    second.emitMessage({ type: "hello", protocol_version: WS_PROTOCOL_VERSION });
    second.emitClose(1006);
    vi.advanceTimersByTime(BACKOFF_CAP_MS);
    expect(MockWebSocket.instances.length).toBeGreaterThanOrEqual(3);
  });

  it("surfaces sign-in and stops on a tokenless 4401 auth close", () => {
    useAuthStore.getState().reset(); // no access token → tokenless URL
    restoreSocket = installMockWebSocket();
    const warnSpy = vi.spyOn(toast, "warn").mockReturnValue("t");
    vi.useFakeTimers();

    renderHook(() => useProgressSocket(), { wrapper: makeWrapper() });
    const socket = MockWebSocket.instances[0];
    expect(socket.url).not.toContain("token=");

    socket.emitClose(4401);
    expect(warnSpy).toHaveBeenCalledWith(expect.stringMatching(/sign in/i));
    // A 4401 won't fix itself by retrying — no reconnect.
    vi.advanceTimersByTime(BACKOFF_CAP_MS * 2);
    expect(MockWebSocket.instances).toHaveLength(1);
  });

  it("includes the access token in the URL when signed in", () => {
    useAuthStore.getState().setAccessToken("secret-access");
    restoreSocket = installMockWebSocket();

    renderHook(() => useProgressSocket(), { wrapper: makeWrapper() });
    expect(MockWebSocket.instances[0].url).toContain("token=secret-access");
  });
});
