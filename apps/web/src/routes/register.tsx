import { useState } from "react";
import { Link, createFileRoute, redirect, useNavigate } from "@tanstack/react-router";
import { useRegister } from "../api/mutations";
import { resolveHttpBase } from "../api/client";
import { isApiError, messageForApiError } from "../api/errors";
import { useConfig } from "../app/config";
import { Button } from "../components/Button";
import { Input } from "../components/Input";
import { UserIcon } from "../components/icons";

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

function RegisterPage() {
  const navigate = useNavigate();
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
    <div className="mx-auto flex w-full max-w-md flex-col px-6 py-12">
      <div className="glass animate-rise flex flex-col gap-6 rounded-card border border-line-soft p-8 shadow-card">
        <div className="flex flex-col items-center gap-4 text-center">
          <span
            className="grid size-14 place-items-center rounded-2xl bg-gradient-to-br from-emerald to-emerald-dim text-void shadow-glow"
            aria-hidden
          >
            <UserIcon className="size-7" />
          </span>
          <div className="flex flex-col gap-1">
            <h1 className="text-2xl font-bold tracking-tight text-fg">
              Create an account
            </h1>
            <p className="text-sm text-muted">
              Join spotDL to save and sync your library.
            </p>
          </div>
        </div>

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
          <label className="flex flex-col gap-1.5 text-[12.5px] font-medium text-ink-2">
            <span>
              Display name <span className="text-muted">(optional)</span>
            </span>
            <Input
              type="text"
              name="display_name"
              autoComplete="nickname"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
            />
          </label>
          <label className="flex flex-col gap-1.5 text-[12.5px] font-medium text-ink-2">
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
          <label className="flex flex-col gap-1.5 text-[12.5px] font-medium text-ink-2">
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
              className="rounded-md border border-red/30 bg-red/10 px-3 py-2 text-xs font-medium text-red"
            >
              {errorMessage}
            </p>
          ) : null}

          <Button type="submit" className="w-full" disabled={register.isPending}>
            {register.isPending ? "Creating account…" : "Create account"}
          </Button>
        </form>

        {providers.length > 0 ? (
          <div className="flex flex-col gap-2">
            <span className="text-center text-[11px] uppercase tracking-wide text-muted">
              or continue with
            </span>
            {providers.map((provider) => (
              <a
                key={provider}
                href={oauthAuthorizeHref(provider)}
                className="inline-flex items-center justify-center gap-2 rounded-md border border-line bg-elevated px-3 py-2 text-sm font-medium capitalize text-fg transition-colors hover:bg-hover"
              >
                {provider}
              </a>
            ))}
          </div>
        ) : null}

        <p className="text-center text-sm text-muted">
          Already have an account?{" "}
          <Link to="/login" className="font-semibold text-emerald hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
