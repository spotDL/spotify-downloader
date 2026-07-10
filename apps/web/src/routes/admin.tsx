import { createFileRoute, Link, Outlet, redirect } from "@tanstack/react-router";
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

// MERGE: replace with the design-system <Tabs>.
const TAB_CLASS =
  "rounded-md px-3 py-1.5 text-sm font-medium text-muted transition-colors hover:bg-black/5 hover:text-fg data-[status=active]:bg-brand-100 data-[status=active]:text-brand-700 dark:hover:bg-white/10 dark:data-[status=active]:bg-brand-700/30 dark:data-[status=active]:text-brand-100";

function AdminLayout() {
  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6 px-6 py-8">
      <h1 className="text-2xl font-semibold tracking-tight text-fg">Admin</h1>
      <nav className="flex flex-wrap gap-1" aria-label="Admin sections">
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
