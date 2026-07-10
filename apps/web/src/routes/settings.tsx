import { useState } from "react";
import type { ReactNode } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQueryClient } from "@tanstack/react-query";
import type { DownloadDefaults, FeatureFlags } from "../api/generated/types.gen";
import { checkHealth, useConfig, useMe } from "../api/queries";
import { useSessionStore } from "../stores/session";
import { useUiStore, type Theme } from "../stores/ui";
import { useAuthStore } from "../stores/auth";
import { Feature } from "../components/Feature";
import { Button } from "../components/Button";
import { Input } from "../components/Input";
import { Badge } from "../components/Badge";
import { Spinner } from "../components/Spinner";
import { ErrorState } from "../components/ErrorState";

// Settings is entirely a client/prefs surface plus a READ-ONLY window onto the
// server's startup config (spec §4/§8). There is deliberately no `PUT /config`
// operation — server config is immutable at runtime, so nothing here mutates it.
export const Route = createFileRoute("/settings")({
  component: SettingsPage,
});

// MERGE: replace the section shell / definition rows / segmented control below
// with the design-system <SettingsSection>, <DefinitionRow>, and <SegmentedControl>.
function Section({
  title,
  description,
  children,
}: {
  title: string;
  description?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="rounded-card border border-black/10 bg-surface p-5 dark:border-white/10">
      <h2 className="text-base font-semibold text-fg">{title}</h2>
      {description ? <p className="mt-1 text-sm text-muted">{description}</p> : null}
      <div className="mt-4">{children}</div>
    </section>
  );
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 border-t border-black/5 py-2 first:border-t-0 dark:border-white/5">
      <dt className="text-sm text-muted">{label}</dt>
      <dd className="text-sm font-medium text-fg">{children}</dd>
    </div>
  );
}

const FLAG_LABELS: Record<keyof FeatureFlags, string> = {
  auth: "Accounts",
  downloads: "Downloads",
  library: "Library",
  voting: "Community voting",
};

function ServerConfigPanel() {
  const config = useConfig();

  if (config.isPending) return <Spinner label="Loading server configuration" />;
  if (config.isError || !config.data)
    return <ErrorState description="Couldn't load the server configuration." />;

  const { mode, features, matcher_version, download_defaults } = config.data;

  return (
    <div className="flex flex-col gap-6">
      <Section
        title="Server"
        description="These values are fixed by the server at startup and can't be changed from here."
      >
        <dl>
          <Row label="Deployment mode">
            <Badge tone="brand">{mode}</Badge>
          </Row>
          <Row label="Matcher version">
            <span className="font-mono">{matcher_version}</span>
          </Row>
        </dl>
      </Section>

      <Section title="Features" description="Which capabilities this server exposes.">
        <dl>
          {(Object.keys(FLAG_LABELS) as (keyof FeatureFlags)[]).map((flag) => (
            <Row key={flag} label={FLAG_LABELS[flag]}>
              {features[flag] ? (
                <Badge tone="brand">On</Badge>
              ) : (
                <Badge tone="muted">Off</Badge>
              )}
            </Row>
          ))}
        </dl>
      </Section>

      {download_defaults ? (
        <Section
          title="Download defaults"
          description="The server's effective download settings (used to pre-fill submit forms)."
        >
          <DownloadDefaultsRows defaults={download_defaults} />
        </Section>
      ) : null}
    </div>
  );
}

function DownloadDefaultsRows({ defaults }: { defaults: DownloadDefaults }) {
  return (
    <dl>
      <Row label="Output format">
        <span className="font-mono">{defaults.output_format}</span>
      </Row>
      <Row label="Bitrate">
        <span className="font-mono">{defaults.bitrate}</span>
      </Row>
      <Row label="Concurrency">{defaults.concurrency}</Row>
      <Row label="Output template">
        <span className="font-mono break-all">{defaults.output_template}</span>
      </Row>
      <Row label="Scan existing">{defaults.scan_existing ? "Yes" : "No"}</Row>
      <Row label="Skip explicit">{defaults.skip_explicit ? "Yes" : "No"}</Row>
    </dl>
  );
}

const THEMES: { value: Theme; label: string }[] = [
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
  { value: "system", label: "System" },
];

function AppearancePanel() {
  const theme = useUiStore((s) => s.theme);
  const setTheme = useUiStore((s) => s.setTheme);

  return (
    <Section title="Appearance" description="Choose how spotDL looks on this device.">
      {/* MERGE: replace with design-system <SegmentedControl> */}
      <div
        role="radiogroup"
        aria-label="Theme"
        className="inline-flex rounded-md border border-black/10 p-0.5 dark:border-white/15"
      >
        {THEMES.map(({ value, label }) => (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={theme === value}
            onClick={() => setTheme(value)}
            className={`rounded px-3 py-1.5 text-sm font-medium transition-colors ${
              theme === value ? "bg-brand-600 text-white" : "text-muted hover:text-fg"
            }`}
          >
            {label}
          </button>
        ))}
      </div>
    </Section>
  );
}

type TestState = "idle" | "testing" | "ok" | "error";

// A blank base URL means "same origin" (the server that served this page); any
// override must be an absolute http(s) URL.
function isValidBaseUrl(value: string): boolean {
  const trimmed = value.trim();
  if (trimmed === "") return true;
  try {
    const url = new URL(trimmed);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}

function ConnectionPanel() {
  const apiBaseUrl = useSessionStore((s) => s.apiBaseUrl);
  const setApiBaseUrl = useSessionStore((s) => s.setApiBaseUrl);
  const queryClient = useQueryClient();
  const [value, setValue] = useState(apiBaseUrl);
  const [test, setTest] = useState<TestState>("idle");

  const valid = isValidBaseUrl(value);
  const dirty = value.trim() !== apiBaseUrl;

  // Persist the base URL and drop all cached server data — every cached result
  // belonged to the *previous* origin (CONTRACT B).
  function apply() {
    setApiBaseUrl(value.trim());
    queryClient.clear();
    setTest("idle");
  }

  async function testConnection() {
    // Persist first so `checkHealth` (→ resolveHttpBase) probes the entered URL.
    if (dirty) apply();
    setTest("testing");
    setTest((await checkHealth()) ? "ok" : "error");
  }

  return (
    <Section
      title="Connection"
      description="The API server this app talks to. Leave blank to use the server that served this page."
    >
      <form
        className="flex flex-col gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          if (valid && dirty) apply();
        }}
      >
        <div>
          <label className="block text-sm font-medium text-fg" htmlFor="api-base-url">
            API base URL
          </label>
          <Input
            id="api-base-url"
            name="apiBaseUrl"
            type="url"
            inputMode="url"
            placeholder="https://nas.local:7070"
            value={value}
            onChange={(e) => {
              setValue(e.target.value);
              setTest("idle");
            }}
            aria-invalid={!valid}
            className="mt-1"
          />
          {!valid ? (
            <p className="mt-1 text-sm text-danger">
              Enter a valid http(s) URL, or leave it blank.
            </p>
          ) : null}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button type="submit" disabled={!valid || !dirty}>
            Save
          </Button>
          <Button
            type="button"
            variant="secondary"
            disabled={!valid || test === "testing"}
            onClick={() => void testConnection()}
          >
            Test connection
          </Button>
          {test === "testing" ? (
            <Spinner label="Testing connection" className="size-4" />
          ) : null}
          {test === "ok" ? (
            <span className="text-sm font-medium text-brand-700 dark:text-brand-100">
              Connected
            </span>
          ) : null}
          {test === "error" ? (
            <span className="text-sm font-medium text-danger">
              Couldn&apos;t reach the server
            </span>
          ) : null}
        </div>
      </form>
    </Section>
  );
}

function AccountPanel() {
  const me = useMe();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const resetAuth = useAuthStore((s) => s.reset);
  const clearSessionAuth = useSessionStore((s) => s.clearAuth);
  const accessToken = useAuthStore((s) => s.accessToken);

  // Local sign-out: drop the in-memory access token and the persisted refresh
  // token, and purge every cached (now-unauthorized) query. Server-side refresh
  // revocation is CONTRACT C (Task 4).
  function signOut() {
    resetAuth();
    clearSessionAuth();
    queryClient.clear();
    void navigate({ to: "/" });
  }

  if (accessToken === null) {
    return (
      <Section title="Account" description="You're not signed in on this device.">
        <Button type="button" onClick={() => void navigate({ to: "/login" })}>
          Sign in
        </Button>
      </Section>
    );
  }

  return (
    <Section title="Account">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted">
          Signed in{me.data ? ` as ${me.data.display_name ?? me.data.email}` : ""}.
        </p>
        <Button type="button" variant="danger" onClick={signOut}>
          Sign out
        </Button>
      </div>
    </Section>
  );
}

function SettingsPage() {
  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 px-6 py-8">
      <h1 className="text-2xl font-semibold tracking-tight text-fg">Settings</h1>
      <ServerConfigPanel />
      <AppearancePanel />
      <ConnectionPanel />
      <Feature flag="auth">
        <AccountPanel />
      </Feature>
    </div>
  );
}
