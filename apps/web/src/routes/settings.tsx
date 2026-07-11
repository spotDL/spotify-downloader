import { useState } from "react";
import type { ReactNode } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQueryClient } from "@tanstack/react-query";
import { motion, useReducedMotion } from "motion/react";
import type { DownloadDefaults, FeatureFlags } from "../api/generated/types.gen";
import { checkHealth, useConfig, useMe } from "../api/queries";
import { useSessionStore } from "../stores/session";
import { useUiStore, type Theme } from "../stores/ui";
import { useAuthStore } from "../stores/auth";
import { Feature } from "../components/Feature";
import { SectionDivider } from "../components/SectionDivider";
import { Button } from "../components/Button";
import { Input } from "../components/Input";
import { Badge } from "../components/Badge";
import { Spinner } from "../components/Spinner";
import { ErrorState } from "../components/ErrorState";
import { cn } from "../lib/utils";

// Settings is entirely a client/prefs surface plus a READ-ONLY window onto the
// server's startup config (spec §4/§8). There is deliberately no `PUT /config`
// operation — server config is immutable at runtime, so nothing here mutates it.
export const Route = createFileRoute("/settings")({
  component: SettingsPage,
});

// A settings section: a SectionDivider header (amber accent bar + title) with an
// optional description, followed by its control rows on a flat card surface.
function Section({
  id,
  title,
  description,
  children,
}: {
  id: string;
  title: string;
  description?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-24">
      <SectionDivider title={title} />
      {description ? (
        <p className="mt-2 text-sm text-muted-foreground">{description}</p>
      ) : null}
      <div className="mt-4 rounded-lg border border-border bg-card px-4">
        {children}
      </div>
    </section>
  );
}

// A hairline-divided control row: label (+ optional description) on the left,
// the control or value on the right. Read-only config rows stay a semantic
// <dt>/<dd> definition list; values are mono/tabular for technical data.
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
    <div className="flex items-center justify-between gap-4 border-b border-border py-3.5 last:border-b-0">
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd
        className={cn(
          "text-right text-sm text-foreground",
          mono ? "font-mono tnum" : "font-medium",
        )}
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
    <>
      <Section
        id="server"
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
        id="features"
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
          id="download-defaults"
          title="Download defaults"
          description="The server's effective download settings (used to pre-fill submit forms)."
        >
          <DownloadDefaultsRows defaults={download_defaults} />
        </Section>
      ) : null}
    </>
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
      id="appearance"
      title="Appearance"
      description="Choose how spotDL looks on this device."
    >
      <div className="flex items-center justify-between gap-4 py-3.5">
        <span className="text-sm text-muted-foreground">Theme</span>
        <div
          role="radiogroup"
          aria-label="Theme"
          className="inline-flex rounded-md border border-border bg-surface p-0.5"
        >
          {THEMES.map(({ value, label }) => (
            <button
              key={value}
              type="button"
              role="radio"
              aria-checked={theme === value}
              onClick={() => setTheme(value)}
              className={cn(
                "rounded-md px-3 py-1.5 text-xs font-semibold transition-colors",
                theme === value
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {label}
            </button>
          ))}
        </div>
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
      id="connection"
      title="Connection"
      description="The API server this app talks to. Leave blank to use the server that served this page."
    >
      <form
        className="flex flex-col gap-3 py-4"
        onSubmit={(e) => {
          e.preventDefault();
          if (valid && dirty) apply();
        }}
      >
        <div>
          <label
            className="block text-sm font-medium text-foreground"
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
            className="mt-1.5 font-mono"
          />
          {!valid ? (
            <p className="mt-1.5 text-xs text-destructive">
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
            <span className="font-mono text-xs font-semibold text-success">
              Connected
            </span>
          ) : null}
          {test === "error" ? (
            <span className="font-mono text-xs font-semibold text-destructive">
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
        id="account"
        title="Account"
        description="You're not signed in on this device."
      >
        <div className="py-4">
          <Button type="button" onClick={() => void navigate({ to: "/login" })}>
            Sign in
          </Button>
        </div>
      </Section>
    );
  }

  return (
    <Section id="account" title="Account">
      <div className="flex flex-wrap items-center justify-between gap-3 py-4">
        <p className="text-sm text-muted-foreground">
          Signed in
          {me.data ? ` as ${me.data.display_name ?? me.data.email}` : ""}.
        </p>
        <Button type="button" variant="danger" onClick={signOut}>
          Sign out
        </Button>
      </div>
    </Section>
  );
}

// Left-rail section index. Server-config sub-sections are always present; the
// account link only shows where the auth feature is on (matches AccountPanel).
const NAV_ITEMS: { id: string; label: string }[] = [
  { id: "server", label: "Server" },
  { id: "features", label: "Features" },
  { id: "appearance", label: "Appearance" },
  { id: "connection", label: "Connection" },
];

function SettingsNav() {
  return (
    <nav aria-label="Settings sections" className="hidden lg:block">
      <p className="mb-2 px-3 text-xs font-medium uppercase tracking-wider text-faint">
        Sections
      </p>
      <ul className="sticky top-20 space-y-0.5 text-sm">
        {NAV_ITEMS.map(({ id, label }) => (
          <li key={id}>
            <a
              href={`#${id}`}
              className="block rounded-md px-3 py-1.5 text-muted-foreground transition-colors hover:bg-surface hover:text-foreground"
            >
              {label}
            </a>
          </li>
        ))}
        <Feature flag="auth">
          <li>
            <a
              href="#account"
              className="block rounded-md px-3 py-1.5 text-muted-foreground transition-colors hover:bg-surface hover:text-foreground"
            >
              Account
            </a>
          </li>
        </Feature>
      </ul>
    </nav>
  );
}

function SettingsPage() {
  const reduceMotion = useReducedMotion();

  return (
    <motion.div
      initial={reduceMotion ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
      className="space-y-8"
    >
      <div className="flex flex-col gap-1">
        <p className="text-xs font-medium uppercase tracking-wider text-faint">
          Control room
        </p>
        <h1 className="font-display text-2xl font-bold tracking-tight text-foreground">
          Settings
        </h1>
        <p className="text-sm text-muted-foreground">
          Server configuration and this device's preferences.
        </p>
      </div>

      <div className="grid gap-8 lg:grid-cols-[184px_1fr]">
        <SettingsNav />
        <div className="min-w-0 space-y-10">
          <ServerConfigPanel />
          <AppearancePanel />
          <ConnectionPanel />
          <Feature flag="auth">
            <AccountPanel />
          </Feature>
        </div>
      </div>
    </motion.div>
  );
}
