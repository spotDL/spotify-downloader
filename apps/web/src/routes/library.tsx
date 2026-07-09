import { createFileRoute } from "@tanstack/react-router";
import { EmptyState } from "../components/EmptyState";

// Placeholder — the library view (completed jobs + file links) lands in Task 9
// with its `features.library` guard. The route exists now so the gated AppShell
// nav link has a real, type-safe target.
export const Route = createFileRoute("/library")({
  component: () => (
    <EmptyState title="Library" description="Your downloaded library lands in a later task." />
  ),
});
