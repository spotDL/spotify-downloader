import { createFileRoute } from "@tanstack/react-router";
import { EmptyState } from "../components/EmptyState";

// Placeholder — the login form (email/password + OAuth buttons) and the
// `features.auth` guard land in Task 4. The route exists now so the gated
// AppShell "Sign in" link has a real, type-safe target.
export const Route = createFileRoute("/login")({
  component: () => (
    <EmptyState title="Sign in" description="Authentication lands in a later task." />
  ),
});
