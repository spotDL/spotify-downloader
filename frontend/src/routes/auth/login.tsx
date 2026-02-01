import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useState } from "react";
import { useLogin } from "@/api";
import { Button, Input, Card, CardContent } from "@/components/ui";

interface LoginSearch {
  redirect?: string;
}

export const Route = createFileRoute("/auth/login")({
  validateSearch: (search: Record<string, unknown>): LoginSearch => {
    return {
      redirect: typeof search.redirect === "string" ? search.redirect : undefined,
    };
  },
  component: LoginPage,
});

function LoginPage() {
  const navigate = useNavigate();
  const { redirect } = Route.useSearch();
  const loginMutation = useLogin();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await loginMutation.mutateAsync({ username, password });
      // Navigate to redirect path or home
      navigate({ to: redirect || "/" });
    } catch (error) {
      console.error("Login failed:", error);
    }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center relative">
      <div className="w-full max-w-md space-y-8 relative z-20">
        {/* Header */}
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-[var(--accent-safe)] to-[var(--accent-cool)] mb-6 shadow-lg glow">
            <svg
              className="w-8 h-8 text-white"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
              />
            </svg>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-[var(--color-text-primary)]">
            Welcome Back
          </h1>
          <p className="text-[var(--color-text-muted)] mt-2">
            Sign in to your account to continue
          </p>
        </div>

        {/* Form Card */}
        <Card variant="bordered" className="animate-scale-in glass">
          <CardContent className="pt-6">
            <form onSubmit={handleSubmit} className="space-y-5">
              <Input
                label="Username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter your username"
                required
              />
              <Input
                label="Password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                required
              />

              {loginMutation.error && (
                <div className="flex items-center gap-2 p-3 rounded-xl bg-[var(--accent-peak)]/10 border border-[var(--accent-peak)]/30 text-[var(--accent-peak)]">
                  <svg
                    className="w-5 h-5 shrink-0"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  <p className="text-sm">
                    {loginMutation.error instanceof Error
                      ? loginMutation.error.message
                      : "Login failed. Please try again."}
                  </p>
                </div>
              )}

              <Button
                type="submit"
                className="w-full"
                size="lg"
                isLoading={loginMutation.isPending}
              >
                Sign In
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Footer */}
        <p className="text-center text-sm text-[var(--color-text-muted)]">
          Don't have an account?{" "}
          <Link
            to="/auth/register"
            className="text-[var(--accent-safe)] hover:text-[var(--accent-safe)]/80 font-medium transition-colors"
          >
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
