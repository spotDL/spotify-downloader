import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.tsx";
import { ThemeProvider } from "./app/theme.tsx";

// Task 3 recomposes this with the full provider stack (QueryClient, ConfigGate,
// RouterProvider). For now ThemeProvider makes the data-theme stamp live.
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider>
      <App />
    </ThemeProvider>
  </StrictMode>,
);
