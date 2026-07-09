import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { TanStackRouterVite } from "@tanstack/router-plugin/vite";

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    // Router codegen must run before the React plugin. Colocated *.test.tsx
    // files (e.g. routes/app-shell.test.tsx) are excluded from the route tree.
    TanStackRouterVite({
      target: "react",
      routeFileIgnorePattern: "\\.(test|spec)\\.",
    }),
    react(),
    tailwindcss(),
  ],
});
