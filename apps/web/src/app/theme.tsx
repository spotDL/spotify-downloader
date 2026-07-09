import { useEffect } from "react";
import type { ReactNode } from "react";
import { useUiStore, type Theme } from "../stores/ui";

function resolveTheme(theme: Theme): "light" | "dark" {
  if (theme !== "system") return theme;
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

/**
 * Reads `useUiStore.theme` and stamps `document.documentElement.dataset.theme`
 * with the resolved concrete theme, re-resolving `"system"` live via matchMedia.
 * All components style light/dark through the `dark:` variant (CONTRACT H).
 */
export function ThemeProvider({ children }: { children: ReactNode }) {
  const theme = useUiStore((state) => state.theme);

  useEffect(() => {
    const apply = () => {
      document.documentElement.dataset.theme = resolveTheme(theme);
    };
    apply();

    if (theme !== "system") return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, [theme]);

  return <>{children}</>;
}
