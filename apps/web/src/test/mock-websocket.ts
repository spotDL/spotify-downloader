// A minimal WebSocket double for the download-progress hook tests. It never
// touches the network; a test drives the connection by grabbing the created
// instance and calling `emitOpen` / `emitMessage` / `emitClose`. The plan's WS
// tests mock the socket per the CONTRACT — there is no real server.
export class MockWebSocket {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;

  static instances: MockWebSocket[] = [];

  readonly url: string;
  readyState = MockWebSocket.CONNECTING;
  sent: string[] = [];
  closedWith: number | undefined;

  onopen: ((ev: unknown) => void) | null = null;
  onmessage: ((ev: { data: string }) => void) | null = null;
  onclose: ((ev: { code: number }) => void) | null = null;
  onerror: ((ev: unknown) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  send(data: string): void {
    this.sent.push(data);
  }

  // The hook calls close() during teardown / protocol mismatch. Mirror a real
  // socket: fire onclose unless the hook already detached the handler.
  close(code?: number): void {
    this.readyState = MockWebSocket.CLOSED;
    this.closedWith = code;
    this.onclose?.({ code: code ?? 1000 });
  }

  // ---- test drivers ----
  emitOpen(): void {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.({});
  }

  emitMessage(data: unknown): void {
    this.onmessage?.({
      data: typeof data === "string" ? data : JSON.stringify(data),
    });
  }

  emitClose(code = 1006): void {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.({ code });
  }
}

/**
 * Swap `globalThis.WebSocket` for {@link MockWebSocket} and reset the instance
 * registry. Returns a restore function for `afterEach`.
 */
export function installMockWebSocket(): () => void {
  // jsdom defines `WebSocket` as a read-only global, so swap it via a property
  // descriptor rather than assignment.
  const original = Object.getOwnPropertyDescriptor(globalThis, "WebSocket");
  MockWebSocket.instances = [];
  Object.defineProperty(globalThis, "WebSocket", {
    value: MockWebSocket as unknown as typeof WebSocket,
    writable: true,
    configurable: true,
  });
  return () => {
    if (original) {
      Object.defineProperty(globalThis, "WebSocket", original);
    } else {
      delete (globalThis as { WebSocket?: unknown }).WebSocket;
    }
    MockWebSocket.instances = [];
  };
}
