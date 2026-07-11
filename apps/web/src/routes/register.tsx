import { useState } from "react";
import { Link, createFileRoute, redirect, useNavigate } from "@tanstack/react-router";
import { motion, useReducedMotion } from "motion/react";
import { CircleAlert } from "lucide-react";
import { useRegister } from "../api/mutations";
import { resolveHttpBase } from "../api/client";
import { isApiError, messageForApiError } from "../api/errors";
import { useConfig } from "../app/config";
import { Button } from "../components/Button";
import { Input } from "../components/Input";
import { cn } from "../lib/utils";

// CONTRACT G guard: register requires `features.auth`; an already-authenticated
// visitor is bounced home.
export const Route = createFileRoute("/register")({
  beforeLoad: ({ context }) => {
    if (!context.config.features.auth) {
      throw redirect({ to: "/" });
    }
    if (context.auth.getAccessToken() !== null) {
      throw redirect({ to: "/" });
    }
  },
  component: RegisterPage,
});

function oauthAuthorizeHref(provider: string): string {
  return `${resolveHttpBase()}/api/v1/auth/oauth/${provider}/authorize`;
}

// Provider identity dots — platform brand tokens where one exists, a neutral
// dot otherwise. Colors carry identity only; they never chrome the button.
const PROVIDER_DOT: Record<string, string> = {
  spotify: "bg-spotify",
  apple: "bg-apple",
  deezer: "bg-deezer",
  youtube: "bg-youtube",
  soundcloud: "bg-soundcloud",
  musicbrainz: "bg-musicbrainz",
};

function providerDot(provider: string): string {
  return PROVIDER_DOT[provider.toLowerCase()] ?? "bg-muted-foreground";
}

function Wordmark() {
  return (
    <div className="text-center">
      <span className="font-display text-3xl font-bold tracking-tight">
        <span className="text-foreground">spot</span>
        <span className="text-primary">DL</span>
      </span>
    </div>
  );
}

function RegisterPage() {
  const navigate = useNavigate();
  const reduceMotion = useReducedMotion();
  const register = useRegister();
  const { data: config } = useConfig();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const providers = config?.oauth_providers ?? [];

  const errorMessage = register.isError
    ? isApiError(register.error)
      ? messageForApiError(register.error)
      : "Couldn't create your account. Try again."
    : null;

  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <motion.div
        initial={reduceMotion ? false : { opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
        className="mx-auto w-full max-w-sm space-y-6"
      >
        <Wordmark />

        <div className="space-y-1 text-center">
          <p className="text-xs font-medium uppercase tracking-wider text-faint">
            Account
          </p>
          <h1 className="font-display text-2xl font-bold tracking-tight text-foreground">
            Create an account
          </h1>
          <p className="text-sm text-muted-foreground">
            Join spotDL to save and sync your library.
          </p>
        </div>

        <div className="rounded-lg border border-border bg-card p-6">
          <form
            className="flex flex-col gap-4"
            onSubmit={(e) => {
              e.preventDefault();
              register.mutate(
                {
                  body: {
                    email,
                    password,
                    display_name:
                      displayName.trim() === "" ? null : displayName.trim(),
                  },
                },
                { onSuccess: () => void navigate({ to: "/" }) },
              );
            }}
          >
            <label className="flex flex-col gap-1.5 text-xs font-medium text-muted-foreground">
              <span>
                Display name <span className="text-faint">(optional)</span>
              </span>
              <Input
                type="text"
                name="display_name"
                autoComplete="nickname"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
              />
            </label>
            <label className="flex flex-col gap-1.5 text-xs font-medium text-muted-foreground">
              Email
              <Input
                type="email"
                name="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </label>
            <label className="flex flex-col gap-1.5 text-xs font-medium text-muted-foreground">
              Password
              <Input
                type="password"
                name="password"
                autoComplete="new-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>

            {errorMessage ? (
              <p
                role="alert"
                className="flex items-center gap-2 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs font-medium text-destructive"
              >
                <CircleAlert className="size-4 shrink-0" aria-hidden />
                {errorMessage}
              </p>
            ) : null}

            <Button
              type="submit"
              size="lg"
              className="w-full"
              isLoading={register.isPending}
            >
              {register.isPending ? "Creating account" : "Create account"}
            </Button>
          </form>

          {providers.length > 0 ? (
            <div className="mt-6 space-y-3">
              <div className="flex items-center gap-3">
                <span className="h-px flex-1 bg-border" />
                <span className="text-xs font-medium uppercase tracking-wider text-faint">
                  or continue with
                </span>
                <span className="h-px flex-1 bg-border" />
              </div>
              <div className="flex flex-col gap-2">
                {providers.map((provider) => (
                  <a
                    key={provider}
                    href={oauthAuthorizeHref(provider)}
                    className="inline-flex w-full items-center justify-center gap-2 rounded-md border border-border bg-surface px-3 py-2 text-sm font-medium capitalize text-foreground transition-colors hover:bg-elevated"
                  >
                    <span
                      className={cn("size-2 rounded-full", providerDot(provider))}
                      aria-hidden
                    />
                    {provider}
                  </a>
                ))}
              </div>
            </div>
          ) : null}
        </div>

        <p className="text-center text-sm text-muted-foreground">
          Already have an account?{" "}
          <Link
            to="/login"
            className="font-medium text-info underline-offset-4 hover:underline"
          >
            Sign in
          </Link>
        </p>

        <p className="text-center font-mono text-xs text-faint">
          spotDL · your music, downloaded
        </p>
      </motion.div>
    </div>
  );
}
