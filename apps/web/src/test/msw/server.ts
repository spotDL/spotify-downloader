import { setupServer } from "msw/node";
import { handlers } from "./handlers";

// The single MSW server for the node/jsdom test suite. Lifecycle
// (listen/resetHandlers/close) is driven from src/test/setup.ts.
export const server = setupServer(...handlers);
