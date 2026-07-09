import { createRootRoute, Outlet } from "@tanstack/react-router";

// Placeholder root route so TanStack Router codegen (`tsr generate`) has a tree
// to build in this task. Task 3 replaces this with the real AppShell layout.
export const Route = createRootRoute({
  component: () => <Outlet />,
});
