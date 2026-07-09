import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import "./index.css";
import { queryClient } from "./app/query-client";
import { router } from "./app/router";
import { ConfigGate } from "./app/config";
import { ThemeProvider } from "./app/theme";
import { client } from "./api/generated/client.gen";
import { installAuthInterceptors } from "./api/client";

// Wire the CONTRACT C refresh-once auth interceptors onto the generated client
// before the first request (the config fetch) goes out.
installAuthInterceptors(client);

// Provider composition (CONTRACT — structure diagram): QueryClient wraps the
// theme + config gate; ConfigGate fetches /config, awaits bootstrapAuth, then
// renders the RouterProvider with the resolved config injected into context.
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <ConfigGate router={router} />
      </ThemeProvider>
    </QueryClientProvider>
  </StrictMode>,
);
