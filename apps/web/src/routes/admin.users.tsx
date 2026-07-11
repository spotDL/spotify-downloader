import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useAdminUsers } from "../api/queries";
import { Button } from "../components/Button";
import { Badge } from "../components/Badge";
import { Spinner } from "../components/Spinner";
import { ErrorState } from "../components/ErrorState";

export const Route = createFileRoute("/admin/users")({
  component: AdminUsers,
});

const PAGE_SIZE = 20;

const TH = "px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wider text-faint";

function AdminUsers() {
  const [offset, setOffset] = useState(0);
  const users = useAdminUsers({ limit: PAGE_SIZE, offset });

  if (users.isPending) return <Spinner label="Loading users" />;
  if (users.isError || !users.data)
    return <ErrorState description="Couldn't load users." />;

  const { items, total } = users.data;
  const start = total === 0 ? 0 : offset + 1;
  const end = offset + items.length;

  return (
    <div className="flex flex-col gap-4">
      <div className="overflow-x-auto rounded-lg border border-border bg-card">
        <table className="w-full text-left text-[13px]">
          <thead className="bg-surface">
            <tr className="border-b border-border">
              <th className={TH}>User</th>
              <th className={TH}>Email</th>
              <th className={TH}>Role</th>
              <th className={TH}>Status</th>
              <th className={TH}>Joined</th>
            </tr>
          </thead>
          <tbody>
            {items.map((user) => {
              const initial = (user.display_name ?? user.email)
                .charAt(0)
                .toUpperCase();
              return (
                <tr
                  key={user.id}
                  className="border-t border-border transition-colors hover:bg-elevated/50"
                >
                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-3">
                      <span
                        aria-hidden
                        className="flex size-8 shrink-0 items-center justify-center rounded-md bg-elevated font-mono text-sm font-semibold text-foreground"
                      >
                        {initial}
                      </span>
                      <span className="font-medium text-foreground">
                        {user.display_name ?? "—"}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-2.5 font-mono text-xs text-muted-foreground tnum">
                    {user.email}
                  </td>
                  <td className="px-4 py-2.5">
                    {user.is_admin ? (
                      <Badge tone="brand">Admin</Badge>
                    ) : (
                      <Badge tone="muted">User</Badge>
                    )}
                  </td>
                  <td className="px-4 py-2.5">
                    {user.is_active ? (
                      <Badge tone="neutral">Active</Badge>
                    ) : (
                      <Badge tone="danger">Inactive</Badge>
                    )}
                  </td>
                  <td className="px-4 py-2.5 font-mono text-xs text-muted-foreground tnum">
                    {new Date(user.created_at).toLocaleDateString()}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between gap-3">
        <p className="font-mono text-xs text-muted-foreground tnum">
          {start}–{end} of {total}
        </p>
        <div className="flex gap-2">
          <Button
            type="button"
            variant="secondary"
            disabled={offset === 0}
            onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
          >
            Previous
          </Button>
          <Button
            type="button"
            variant="secondary"
            disabled={end >= total}
            onClick={() => setOffset((o) => o + PAGE_SIZE)}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}
