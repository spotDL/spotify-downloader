// Hand-written 3-line shim (CONTRACT A2): re-exports the generated WS protocol
// version so app code imports a stable path, not the .gen artifact directly.
export { WS_PROTOCOL_VERSION } from "./ws-protocol.gen";
