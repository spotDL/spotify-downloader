import { createFileRoute } from "@tanstack/react-router";
import { EmptyState } from "../components/EmptyState";

// Placeholder — the read-only server-config panel + UI prefs + API base URL
// field land in Task 10. The route exists now so the always-on AppShell nav
// link has a real, type-safe target.
export const Route = createFileRoute("/settings")({
  component: () => (
    <EmptyState title="Settings" description="Server config and preferences land in a later task." />
  ),
});
