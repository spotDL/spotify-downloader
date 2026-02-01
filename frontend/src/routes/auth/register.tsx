import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useState } from "react";
import { useRegister, useSystemStats } from "@/api";
import { Button, Input, Card, CardContent } from "@/components/ui";
import { features } from "@/config";

export const Route = createFileRoute("/auth/register")({
  component: RegisterPage,
});

// Simple background with gradient accents
function SimpleBackground() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {/* Radial gradient accents */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-violet-500/5 rounded-full blur-3xl" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/5 rounded-full blur-3xl" />
    </div>
  );
}

function RegisterPage() {
  const navigate = useNavigate();
  const registerMutation = useRegister();

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  // Check if this is the first user (for admin notice)
  const { data: stats } = useSystemStats();
  const isFirstUser = features.isSelfHosted && (stats?.entities.users === 0);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }

    try {
      await registerMutation.mutateAsync({ username, email, password });
      navigate({ to: "/" });
    } catch {
      // Error is handled by registerMutation.error in the UI
    }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center relative">
      {/* Background */}
      <SimpleBackground />

      <div className="w-full max-w-md space-y-8 relative z-20">
        {/* Header */}
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-violet-500 to-purple-500 mb-6 shadow-lg shadow-violet-500/25">
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
                d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"
              />
            </svg>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-[var(--color-text-primary)]">
            Create Account
          </h1>
          <p className="text-[var(--color-text-muted)] mt-2">
            Join SpotDL to contribute and vote on matches
          </p>
        </div>

        {/* First user admin notice */}
        {isFirstUser && (
          <div className="flex items-center gap-3 p-4 rounded-xl bg-[var(--accent-safe)]/10 border border-[var(--accent-safe)]/30 text-[var(--accent-safe)]">
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
                d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
              />
            </svg>
            <p className="text-sm">
              This is a self-hosted instance. The first user will automatically become an administrator.
            </p>
          </div>
        )}

        {/* Form Card */}
        <Card variant="bordered" className="animate-scale-in glass">
          <CardContent className="pt-6">
            <form onSubmit={handleSubmit} className="space-y-5">
              <Input
                label="Username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Choose a username"
                required
              />
              <Input
                label="Email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Enter your email"
                required
              />
              <Input
                label="Password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Create a password (min. 8 characters)"
                required
              />
              <Input
                label="Confirm Password"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Confirm your password"
                required
              />

              {(error || registerMutation.error) && (
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
                    {error ||
                      (registerMutation.error instanceof Error
                        ? registerMutation.error.message
                        : "Registration failed. Please try again.")}
                  </p>
                </div>
              )}

              <Button
                type="submit"
                className="w-full"
                size="lg"
                isLoading={registerMutation.isPending}
              >
                Create Account
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Footer */}
        <p className="text-center text-sm text-[var(--color-text-muted)]">
          Already have an account?{" "}
          <Link
            to="/auth/login"
            className="text-[var(--accent-safe)] hover:text-[var(--accent-safe)]/80 font-medium transition-colors"
          >
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
