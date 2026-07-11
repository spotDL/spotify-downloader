import { createFileRoute, Link, Outlet, redirect } from "@tanstack/react-router";
import { ShieldCheck } from "lucide-react";
import { meQueryOptions } from "../api/queries";

// CONTRACT G — admin is gated on `auth && is_admin`. `auth` (a startup feature
// flag) is read synchronously from the router context; `is_admin` comes from the
// ["me"] query, so the guard warms it via `ensureQueryData` before the layout
// renders. A signed-out user goes to /login; a non-admin (or an auth-off server)
// is bounced home. There is no admin write surface beyond report review.
export const Route = createFileRoute("/admin")({
  beforeLoad: async ({ context }) => {
    if (!context.config.features.auth) throw redirect({ to: "/" });
    if (context.auth.getAccessToken() === null) throw redirect({ to: "/login" });
    let isAdmin: boolean;
    try {
      const me = await context.queryClient.ensureQueryData(meQueryOptions());
      isAdmin = me.is_admin;
    } catch {
      // A rejected/expired token can't prove admin — send them to sign in.
      throw redirect({ to: "/login" });
    }
    if (!isAdmin) throw redirect({ to: "/" });
  },
  component: AdminLayout,
});

// Underline sub-nav tab. TanStack Router stamps data-status="active" on the
// matching Link; the amber underline is the Control Room active marker.
const TAB_CLASS =
  "relative -mb-px border-b-2 border-transparent px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground data-[status=active]:border-primary data-[status=active]:text-foreground";

function AdminLayout() {
  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <p className="text-xs font-medium uppercase tracking-wider text-faint">
          System
        </p>
        <div className="flex items-center gap-2">
          <ShieldCheck className="size-5 text-primary" aria-hidden />
          <h1 className="font-display text-2xl font-bold tracking-tight text-foreground">
            Admin
          </h1>
        </div>
        <p className="text-sm text-muted-foreground">
          Moderation and community-metadata review.
        </p>
      </header>
      <nav
        className="flex flex-wrap gap-1 border-b border-border"
        aria-label="Admin sections"
      >
        <Link to="/admin" activeOptions={{ exact: true }} className={TAB_CLASS}>
          Overview
        </Link>
        <Link to="/admin/reports" className={TAB_CLASS}>
          Reports
        </Link>
        <Link to="/admin/users" className={TAB_CLASS}>
          Users
        </Link>
      </nav>
      <Outlet />
    </div>
  );
}
