import { useEffect, useState } from "react";
import { type AnyRouter, RouterProvider } from "@tanstack/react-router";
import type { FeatureFlags } from "../api/generated/types.gen";
import { useConfig } from "../api/queries";
import { useSessionStore } from "../stores/session";
import { Button } from "../components/Button";
import { Input } from "../components/Input";
import { Spinner } from "../components/Spinner";

// Re-exported so config-related consumers have one import site (CONTRACT G).
export { useConfig };

export type FeatureFlag = keyof FeatureFlags;

/**
 * Read a single `/config` feature flag (CONTRACT G). Returns `false` until
 * config has loaded, so gated UI stays hidden during the (brief) boot fetch.
 */
export function useFeature(flag: FeatureFlag): boolean {
  const { data } = useConfig();
  return data?.features[flag] ?? false;
}

/**
 * Boot-time auth bootstrap (CONTRACT C): if a refresh token exists but there is
 * no access token, mint one via `POST /auth/refresh` before authed UI renders.
 * Task 4 implements the refresh; this stub resolves immediately so the boot flow
 * and the ConfigGate `await` seam already exist.
 */
export async function bootstrapAuth(): Promise<void> {
  return;
}

function FullPageSpinner() {
  return (
    <div className="flex min-h-svh items-center justify-center bg-bg">
      <Spinner label="Loading spotDL" className="size-8" />
    </div>
  );
}

function ConfigErrorScreen({ onRetry }: { onRetry: () => void }) {
  const apiBaseUrl = useSessionStore((s) => s.apiBaseUrl);
  const setApiBaseUrl = useSessionStore((s) => s.setApiBaseUrl);
  const [value, setValue] = useState(apiBaseUrl);

  return (
    <div className="flex min-h-svh items-center justify-center bg-bg p-6">
      <form
        className="w-full max-w-md rounded-card border border-black/10 bg-surface p-6 shadow-card dark:border-white/10"
        onSubmit={(e) => {
          e.preventDefault();
          setApiBaseUrl(value.trim());
          onRetry();
        }}
      >
        <h1 className="text-lg font-semibold text-fg">Can&apos;t reach the server</h1>
        <p className="mt-2 text-sm text-muted">
          spotDL couldn&apos;t load its configuration. If the server lives at a
          different address, set its URL below. Leave it blank to use the server
          that served this page.
        </p>
        <label className="mt-4 block text-sm font-medium text-fg" htmlFor="api-base-url">
          API base URL
        </label>
        <Input
          id="api-base-url"
          name="apiBaseUrl"
          type="url"
          placeholder="https://nas.local:7070"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="mt-1"
        />
        <div className="mt-4 flex justify-end">
          <Button type="submit">Retry connection</Button>
        </div>
      </form>
    </div>
  );
}

/**
 * ConfigGate wraps the router (CONTRACT G): it suspends on `useConfig()`, shows
 * a recoverable "can't reach server" screen on error (with the base-URL field),
 * awaits `bootstrapAuth()`, and only then renders the RouterProvider — injecting
 * the resolved config into the router context so `beforeLoad` guards read it
 * synchronously.
 */
export function ConfigGate({ router }: { router: AnyRouter }) {
  const config = useConfig();
  const [authReady, setAuthReady] = useState(false);

  useEffect(() => {
    let alive = true;
    void bootstrapAuth().finally(() => {
      if (alive) setAuthReady(true);
    });
    return () => {
      alive = false;
    };
  }, []);

  if (config.isPending || !authReady) return <FullPageSpinner />;
  if (config.isError) return <ConfigErrorScreen onRetry={() => void config.refetch()} />;

  return <RouterProvider router={router} context={{ config: config.data }} />;
}
