import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useState } from "react";
import { useLogin } from "@/api";
import { Button, Input, Card, CardContent, CardHeader, CardTitle } from "@/components/ui";

export const Route = createFileRoute("/auth/login")({
  component: LoginPage,
});

function LoginPage() {
  const navigate = useNavigate();
  const loginMutation = useLogin();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await loginMutation.mutateAsync({ username, password });
      navigate({ to: "/" });
    } catch (error) {
      console.error("Login failed:", error);
    }
  };

  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <Card variant="bordered" className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-center">Welcome Back</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
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
              <p className="text-sm text-red-400">
                {loginMutation.error instanceof Error
                  ? loginMutation.error.message
                  : "Login failed. Please try again."}
              </p>
            )}

            <Button
              type="submit"
              className="w-full"
              isLoading={loginMutation.isPending}
            >
              Sign In
            </Button>
          </form>

          <p className="mt-4 text-center text-sm text-gray-400">
            Don't have an account?{" "}
            <Link
              to="/auth/register"
              className="text-blue-400 hover:text-blue-300"
            >
              Sign up
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
