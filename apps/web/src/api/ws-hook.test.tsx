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
    // CONTRACT E: base 1000ms → delays 1s, 2s, 4s… with ½..1× equal jitter.
    expect(backoffDelay(0, () => 0)).toBe(500); // ½ × 1000
    expect(backoffDelay(0, () => 1)).toBe(1000); // 1 × 1000
    expect(backoffDelay(1, () => 0)).toBe(1000); // ½ × 2000
    expect(backoffDelay(1, () => 1)).toBe(2000); // 1 × 2000
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

  it("resumes a parked socket once a token appears after a tokenless 4401", () => {
    useAuthStore.getState().reset(); // no token → tokenless URL
    restoreSocket = installMockWebSocket();
    vi.useFakeTimers();

    renderHook(() => useProgressSocket(), { wrapper: makeWrapper() });
    expect(MockWebSocket.instances[0].url).not.toContain("token=");

    MockWebSocket.instances[0].emitClose(4401); // parked awaiting sign-in
    vi.advanceTimersByTime(BACKOFF_CAP_MS * 2);
    expect(MockWebSocket.instances).toHaveLength(1); // no blind reconnect

    // Signing in (null→token) resumes the socket, now carrying the token.
    useAuthStore.getState().setAccessToken("fresh-token");
    expect(MockWebSocket.instances).toHaveLength(2);
    expect(MockWebSocket.instances[1].url).toContain("token=fresh-token");
  });

  it("tears down and toasts when the first frame isn't a hello", () => {
    restoreSocket = installMockWebSocket();
    const errorSpy = vi.spyOn(toast, "error").mockReturnValue("t");
    vi.useFakeTimers();

    renderHook(() => useProgressSocket(), { wrapper: makeWrapper() });
    const socket = MockWebSocket.instances[0];
    // A progress frame with no preceding hello is a protocol violation.
    socket.emitMessage({
      type: "progress",
      job_id: "job-1",
      batch_id: "batch-1",
      overall: 0.1,
      percent: 10,
      phase: "fetch",
    });

    expect(errorSpy).toHaveBeenCalledTimes(1);
    // A protocol violation is fatal — mirror the version-mismatch path (no reconnect).
    vi.advanceTimersByTime(BACKOFF_CAP_MS * 2);
    expect(MockWebSocket.instances).toHaveLength(1);
  });

  it("raises the batch-complete toast from the reducer signal", () => {
    restoreSocket = installMockWebSocket();
    const pushSpy = vi.spyOn(toast, "push").mockReturnValue("t");

    renderHook(() => useProgressSocket(), { wrapper: makeWrapper() });
    const socket = MockWebSocket.instances[0];
    socket.emitMessage({ type: "hello", protocol_version: WS_PROTOCOL_VERSION });
    socket.emitMessage({
      type: "batch_finished",
      batch_id: "batch-1",
      completed: 2,
      failed: 0,
      skipped: 1,
      cancelled: 0,
      m3u_paths: ["/library/mix.m3u8"],
      save_file_path: "/library/mix.spotdl",
    });

    expect(pushSpy).toHaveBeenCalledWith(
      expect.stringContaining("Batch complete: 2 done, 0 failed, 1 skipped"),
      "info",
    );
  });
});
