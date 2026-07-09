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
      {/* MERGE: replace with the design-system <DataTable>. */}
      <div className="overflow-x-auto rounded-card border border-black/10 dark:border-white/10">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-black/10 text-muted dark:border-white/10">
            <tr>
              <th className="px-4 py-2 font-medium">User</th>
              <th className="px-4 py-2 font-medium">Email</th>
              <th className="px-4 py-2 font-medium">Role</th>
              <th className="px-4 py-2 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {items.map((user) => (
              <tr
                key={user.id}
                className="border-b border-black/5 last:border-b-0 dark:border-white/5"
              >
                <td className="px-4 py-2 font-medium text-fg">
                  {user.display_name ?? "—"}
                </td>
                <td className="px-4 py-2 text-muted">{user.email}</td>
                <td className="px-4 py-2">
                  {user.is_admin ? <Badge tone="brand">Admin</Badge> : <Badge tone="muted">User</Badge>}
                </td>
                <td className="px-4 py-2">
                  {user.is_active ? (
                    <Badge tone="neutral">Active</Badge>
                  ) : (
                    <Badge tone="danger">Inactive</Badge>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between gap-3">
        <p className="text-sm text-muted">
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
