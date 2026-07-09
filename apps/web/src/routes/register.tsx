import { useState } from "react";
import { Link, createFileRoute, redirect, useNavigate } from "@tanstack/react-router";
import { useRegister } from "../api/mutations";
import { resolveHttpBase } from "../api/client";
import { isApiError } from "../api/errors";
import { useConfig } from "../app/config";
import { toast } from "../components/Toasts";
import { Button } from "../components/Button";
import { Input } from "../components/Input";

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

  return (
    <div className="mx-auto flex max-w-sm flex-col gap-6 py-10">
      <h1 className="text-2xl font-semibold text-fg">Create an account</h1>
      <form
        className="flex flex-col gap-4"
        onSubmit={(e) => {
          e.preventDefault();
          register.mutate(
            {
              body: {
                email,
                password,
                display_name: displayName.trim() === "" ? null : displayName.trim(),
              },
            },
            {
              onSuccess: () => void navigate({ to: "/" }),
              onError: (error) => {
                if (isApiError(error)) toast.fromApiError(error);
              },
            },
          );
        }}
      >
        <label className="flex flex-col gap-1 text-sm font-medium text-fg">
          Display name <span className="text-muted">(optional)</span>
          <Input
            type="text"
            name="display_name"
            autoComplete="nickname"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium text-fg">
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
        <label className="flex flex-col gap-1 text-sm font-medium text-fg">
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
        <Button type="submit" disabled={register.isPending}>
          {register.isPending ? "Creating account…" : "Create account"}
        </Button>
      </form>

      {providers.length > 0 ? (
        <div className="flex flex-col gap-2">
          <span className="text-center text-xs uppercase tracking-wide text-muted">
            or continue with
          </span>
          {providers.map((provider) => (
            <a
              key={provider}
              href={oauthAuthorizeHref(provider)}
              className="inline-flex items-center justify-center gap-2 rounded-md border border-black/10 bg-surface px-3 py-1.5 text-sm font-medium capitalize text-fg hover:bg-black/5 dark:border-white/15 dark:hover:bg-white/10"
            >
              {provider}
            </a>
          ))}
        </div>
      ) : null}

      <p className="text-center text-sm text-muted">
        Already have an account?{" "}
        <Link to="/login" className="font-medium text-brand-600 hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}
