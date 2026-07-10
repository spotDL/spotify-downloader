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
import {
  DiscIcon,
  DownloadIcon,
  ExternalIcon,
  FlagIcon,
  SettingsIcon,
  UserIcon,
} from "../components/icons";

// Settings is entirely a client/prefs surface plus a READ-ONLY window onto the
// server's startup config (spec §4/§8). There is deliberately no `PUT /config`
// operation — server config is immutable at runtime, so nothing here mutates it.
export const Route = createFileRoute("/settings")({
  component: SettingsPage,
});

// A bordered card group led by a section header with a small emerald icon tile.
function Section({
  title,
  description,
  icon,
  children,
}: {
  title: string;
  description?: ReactNode;
  icon: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="rounded-card border border-line-soft bg-surface p-5">
      <header className="flex items-start gap-3">
        <span
          className="grid size-9 shrink-0 place-items-center rounded-[10px] border border-emerald/25 bg-emerald/12 text-emerald"
          aria-hidden
        >
          {icon}
        </span>
        <div className="min-w-0">
          <h2 className="text-[15px] font-bold tracking-tight text-fg">{title}</h2>
          {description ? (
            <p className="mt-0.5 text-xs text-muted">{description}</p>
          ) : null}
        </div>
      </header>
      <div className="mt-4">{children}</div>
    </section>
  );
}

// A key/value row — kept as <dt>/<dd> so the read-only server rows stay a
// semantic definition list; value is mono/tabular for technical data.
function Row({
  label,
  children,
  mono = false,
}: {
  label: string;
  children: ReactNode;
  mono?: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-line-soft py-2 last:border-b-0">
      <dt className="text-[12.5px] text-muted">{label}</dt>
      <dd
        className={`text-right text-[12.5px] text-fg ${
          mono ? "font-mono tabular-nums" : "font-medium"
        }`}
      >
        {children}
      </dd>
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
    <div className="flex flex-col gap-5">
      <Section
        icon={<SettingsIcon className="size-4" />}
        title="Server"
        description="Fixed by the server at startup — these can't be changed from here."
      >
        <dl>
          <Row label="Deployment mode">
            <Badge tone="brand" className="uppercase">
              {mode}
            </Badge>
          </Row>
          <Row label="Matcher version" mono>
            {matcher_version}
          </Row>
        </dl>
      </Section>

      <Section
        icon={<FlagIcon className="size-4" />}
        title="Features"
        description="Which capabilities this server exposes."
      >
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
          icon={<DownloadIcon className="size-4" />}
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
      <Row label="Output format" mono>
        {defaults.output_format}
      </Row>
      <Row label="Bitrate" mono>
        {defaults.bitrate}
      </Row>
      <Row label="Concurrency" mono>
        {defaults.concurrency}
      </Row>
      <Row label="Output template" mono>
        <span className="break-all">{defaults.output_template}</span>
      </Row>
      <Row label="Scan existing" mono>
        {defaults.scan_existing ? "yes" : "no"}
      </Row>
      <Row label="Skip explicit" mono>
        {defaults.skip_explicit ? "yes" : "no"}
      </Row>
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
    <Section
      icon={<DiscIcon className="size-4" />}
      title="Appearance"
      description="Choose how spotDL looks on this device."
    >
      <div
        role="radiogroup"
        aria-label="Theme"
        className="inline-flex rounded-lg border border-line bg-void p-0.5"
      >
        {THEMES.map(({ value, label }) => (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={theme === value}
            onClick={() => setTheme(value)}
            className={`rounded-md px-3 py-1.5 text-xs font-semibold transition-colors ${
              theme === value
                ? "bg-emerald text-void"
                : "text-muted hover:text-fg"
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
      icon={<ExternalIcon className="size-4" />}
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
          <label
            className="block text-[12.5px] font-medium text-ink-2"
            htmlFor="api-base-url"
          >
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
            className="mt-1 font-mono"
          />
          {!valid ? (
            <p className="mt-1 text-xs text-red">
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
            <span className="text-xs font-semibold text-emerald">Connected</span>
          ) : null}
          {test === "error" ? (
            <span className="text-xs font-semibold text-red">
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
      <Section
        icon={<UserIcon className="size-4" />}
        title="Account"
        description="You're not signed in on this device."
      >
        <Button type="button" onClick={() => void navigate({ to: "/login" })}>
          Sign in
        </Button>
      </Section>
    );
  }

  return (
    <Section icon={<UserIcon className="size-4" />} title="Account">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-[12.5px] text-muted">
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
    <div className="mx-auto flex max-w-2xl flex-col gap-5 px-6 py-8">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold tracking-tight text-fg">Settings</h1>
        <p className="text-sm text-muted">
          Server configuration and this device's preferences.
        </p>
      </div>
      <ServerConfigPanel />
      <AppearancePanel />
      <ConnectionPanel />
      <Feature flag="auth">
        <AccountPanel />
      </Feature>
    </div>
  );
}
