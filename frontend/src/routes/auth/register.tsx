import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useState } from "react";
import { useRegister } from "@/api";
import { Button, Input, Card, CardContent, CardHeader, CardTitle } from "@/components/ui";

export const Route = createFileRoute("/auth/register")({
  component: RegisterPage,
});

function RegisterPage() {
  const navigate = useNavigate();
  const registerMutation = useRegister();

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

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
    } catch (err) {
      console.error("Registration failed:", err);
    }
  };

  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <Card variant="bordered" className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-center">Create Account</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
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
              placeholder="Create a password"
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
              <p className="text-sm text-red-400">
                {error ||
                  (registerMutation.error instanceof Error
                    ? registerMutation.error.message
                    : "Registration failed. Please try again.")}
              </p>
            )}

            <Button
              type="submit"
              className="w-full"
              isLoading={registerMutation.isPending}
            >
              Create Account
            </Button>
          </form>

          <p className="mt-4 text-center text-sm text-gray-400">
            Already have an account?{" "}
            <Link
              to="/auth/login"
              className="text-blue-400 hover:text-blue-300"
            >
              Sign in
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
