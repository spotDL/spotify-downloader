import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Button } from "../components/Button";
import { EmptyState } from "../components/EmptyState";
import { Input } from "../components/Input";

export const Route = createFileRoute("/")({
  validateSearch: (search: Record<string, unknown>): { q?: string } => {
    const q = search.q;
    return typeof q === "string" && q.length > 0 ? { q } : {};
  },
  component: Home,
});

function Home() {
  const { q } = Route.useSearch();
  const navigate = Route.useNavigate();
  const [query, setQuery] = useState(q ?? "");
  const [url, setUrl] = useState("");

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-8 py-8">
      <section className="flex flex-col gap-2 text-center">
        <h1 className="text-3xl font-semibold tracking-tight text-fg">spotDL</h1>
        <p className="text-muted">
          Search for a track, album, artist, or playlist — or paste a link.
        </p>
      </section>

      <form
        role="search"
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          const next = query.trim();
          if (next.length > 0) void navigate({ to: "/", search: { q: next } });
        }}
      >
        <Input
          type="search"
          aria-label="Search"
          placeholder="e.g. Daft Punk — Get Lucky"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <Button type="submit">Search</Button>
      </form>

      <form
        className="flex gap-2"
        onSubmit={(e) => {
          // Task 6 wires POST /resolve → navigate to the resolved entity route.
          e.preventDefault();
        }}
      >
        <Input
          type="url"
          aria-label="Paste a link"
          placeholder="Paste a Spotify or other supported link…"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
        />
        <Button type="submit" variant="secondary">
          Open
        </Button>
      </form>

      {q ? (
        <EmptyState
          title={`Results for “${q}”`}
          description="Search results land in a later task."
        />
      ) : null}
    </div>
  );
}
