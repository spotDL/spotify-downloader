import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { TanStackRouterVite } from "@tanstack/router-plugin/vite";

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    // Router codegen must run before the React plugin.
    TanStackRouterVite({ target: "react" }),
    react(),
    tailwindcss(),
  ],
});
