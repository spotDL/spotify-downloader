import { createFileRoute } from "@tanstack/react-router";
import { EmptyState } from "../components/EmptyState";

// Placeholder — the QueueTable + live WS progress land in Task 9 (and the
// `features.downloads` guard is added there). The route exists now so the gated
// AppShell nav link (CONTRACT G) has a real, type-safe target.
export const Route = createFileRoute("/downloads")({
  component: () => (
    <EmptyState title="Downloads" description="The download queue lands in a later task." />
  ),
});
