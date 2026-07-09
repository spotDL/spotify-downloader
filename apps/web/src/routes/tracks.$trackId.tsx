import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import type { LyricsOut, MatchOut } from "../api/generated/types.gen";
import {
  useEnqueueDownload,
  useSubmitMatch,
  useTrack,
  useTrackLyrics,
  useTrackMatches,
  useVoteLyrics,
  useVoteMatch,
} from "../api/queries";
import { reportError } from "../lib/report-error";
import { formatDuration, joinArtists } from "../lib/format";
import { useFeature } from "../app/config";
import { useAuthStore } from "../stores/auth";
import { Button } from "../components/Button";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { Feature } from "../components/Feature";
import { Input } from "../components/Input";
import { Spinner } from "../components/Spinner";
import { SyncedLyricsViewer } from "../components/SyncedLyricsViewer";
import { toast } from "../components/Toasts";
import { MatchStatusBadge } from "../components/MatchStatusBadge";
import { ScoreGauge } from "../components/ScoreGauge";
import { VoteButtons, type VoteValue } from "../components/VoteButtons";

export const Route = createFileRoute("/tracks/$trackId")({
  component: TrackPage,
});

const ANON_VOTE_TOOLTIP = "Sign in to vote.";

function useAnonymous(): boolean {
  return useAuthStore((s) => s.accessToken === null);
}

// The design-system VoteButtons speaks numeric votes (1/0/-1); the server's
// VoteRequest speaks the verbs `up`/`down`/`retract`. Convert at the boundary so
// the component stays UI-only and the wire contract is unchanged.
function voteVerb(next: VoteValue): "up" | "down" | "retract" {
  return next === 1 ? "up" : next === -1 ? "down" : "retract";
}

function toVoteValue(vote: number | null | undefined): VoteValue {
  return vote === 1 ? 1 : vote === -1 ? -1 : 0;
}

function TrackPage() {
  const { trackId } = Route.useParams();
  const track = useTrack(trackId);
  const enqueue = useEnqueueDownload();

  if (track.isPending) {
    return (
      <div className="flex justify-center py-16">
        <Spinner label="Loading track" className="size-8" />
      </div>
    );
  }

  if (track.isError) {
    return (
      <ErrorState
        title="Couldn't load this track"
        description="The track may not exist, or the server is unreachable."
      />
    );
  }

  const t = track.data;

  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end">
        <div className="size-40 shrink-0 overflow-hidden rounded-card bg-black/5 dark:bg-white/10">
          {t.album?.cover_url ? (
            <img src={t.album.cover_url} alt="" className="size-full object-cover" />
          ) : null}
        </div>
        <div className="flex flex-1 flex-col gap-1">
          <h1 className="text-2xl font-semibold text-fg">{t.name}</h1>
          <p className="text-muted">{joinArtists(t.artists)}</p>
          <p className="text-sm text-muted">
            {t.album?.name ? <span>{t.album.name}</span> : null}
            {t.year ? <span> · {t.year}</span> : null}
            <span> · {formatDuration(t.duration_ms)}</span>
          </p>
        </div>
        <Feature flag="downloads">
          <div className="sm:self-end">
            <Button
              disabled={enqueue.isPending}
              onClick={() =>
                enqueue.mutate(
                  { body: { query: `spotify:track:${t.id}` } },
                  {
                    onSuccess: () => toast.info("Added to the download queue."),
                    onError: (e) =>
                      reportError(e, "Couldn't enqueue this track."),
                  },
                )
              }
            >
              {enqueue.isPending ? <Spinner label="Enqueuing" /> : "Download"}
            </Button>
          </div>
        </Feature>
      </header>

      <MatchList trackId={trackId} />

      <LyricsSection trackId={trackId} />
    </div>
  );
}

// --- Matches -----------------------------------------------------------------

function MatchList({ trackId }: { trackId: string }) {
  const matches = useTrackMatches(trackId);
  const vote = useVoteMatch(trackId);
  const anonymous = useAnonymous();
  // MatchOut carries no `your_vote`, so track the caller's own vote locally
  // (seeded from each vote's response); tallies still come from the server.
  const [myVotes, setMyVotes] = useState<Record<string, number | null>>({});

  const castVote = (match: MatchOut, next: VoteValue) =>
    vote.mutate(
      { path: { match_id: match.id }, body: { value: voteVerb(next) } },
      {
        onSuccess: (res) =>
          setMyVotes((prev) => ({ ...prev, [match.id]: res.your_vote ?? null })),
        onError: (e) => reportError(e, "Your vote didn't go through."),
      },
    );

  return (
    <section className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-fg">Matches</h2>
      </div>

      {matches.isPending ? (
        <div className="flex justify-center py-8">
          <Spinner label="Loading matches" />
        </div>
      ) : matches.isError ? (
        <ErrorState
          title="Couldn't load matches"
          description="Try refreshing in a moment."
        />
      ) : matches.data.matches.length === 0 ? (
        <EmptyState
          title="No matches yet"
          description="No audio sources have been matched to this track. Submit one below."
        />
      ) : (
        <ul className="flex flex-col divide-y divide-black/5 rounded-card border border-black/10 dark:divide-white/5 dark:border-white/10">
          {matches.data.matches.map((match) => (
            <li
              key={match.id}
              className="flex items-center gap-3 px-4 py-3"
            >
              <ScoreGauge score={match.score} />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-fg">
                  {match.candidate_name ?? match.target_id}
                </p>
                <p className="truncate text-xs text-muted">
                  {match.candidate_artists && match.candidate_artists.length > 0
                    ? `${joinArtists(match.candidate_artists)} · `
                    : ""}
                  {match.target_provider}
                  {match.candidate_duration_ms != null
                    ? ` · ${formatDuration(match.candidate_duration_ms)}`
                    : ""}
                </p>
              </div>
              <MatchStatusBadge status={match.status} />
              <a
                href={match.target_url}
                target="_blank"
                rel="noreferrer"
                className="text-xs text-brand-600 hover:underline"
              >
                Open
              </a>
              <Feature flag="voting">
                <VoteButtons
                  netScore={match.net_score}
                  value={toVoteValue(myVotes[match.id])}
                  canVote={!anonymous}
                  onVote={(next) => castVote(match, next)}
                />
              </Feature>
            </li>
          ))}
        </ul>
      )}

      <Feature flag="voting">
        <SubmitMatchForm trackId={trackId} disabled={anonymous} />
      </Feature>
    </section>
  );
}

function SubmitMatchForm({
  trackId,
  disabled,
}: {
  trackId: string;
  disabled: boolean;
}) {
  const [url, setUrl] = useState("");
  const submit = useSubmitMatch(trackId);

  return (
    <form
      className="flex flex-col gap-2"
      title={disabled ? ANON_VOTE_TOOLTIP : undefined}
      onSubmit={(e) => {
        e.preventDefault();
        const value = url.trim();
        if (value.length === 0 || disabled) return;
        submit.mutate(
          { path: { id: trackId }, body: { url: value } },
          {
            onSuccess: () => {
              toast.info("Thanks — your match was submitted.");
              setUrl("");
            },
            onError: (e) => reportError(e, "Couldn't submit that match."),
          },
        );
      }}
    >
      <label className="text-sm font-medium text-fg" htmlFor="submit-match-url">
        Submit a match URL
      </label>
      <div className="flex gap-2">
        <Input
          id="submit-match-url"
          type="text"
          aria-label="Match URL"
          placeholder="Paste a YouTube / SoundCloud / … audio link"
          value={url}
          disabled={disabled || submit.isPending}
          onChange={(e) => setUrl(e.target.value)}
        />
        <Button type="submit" disabled={disabled || submit.isPending}>
          {submit.isPending ? <Spinner label="Submitting" /> : "Submit"}
        </Button>
      </div>
    </form>
  );
}

// --- Lyrics ------------------------------------------------------------------

function LyricsSection({ trackId }: { trackId: string }) {
  const lyrics = useTrackLyrics(trackId);
  const vote = useVoteLyrics(trackId);
  const votingOn = useFeature("voting");
  const anonymous = useAnonymous();
  const [myVotes, setMyVotes] = useState<Record<string, number | null>>({});

  if (lyrics.isPending) {
    return (
      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold text-fg">Lyrics</h2>
        <div className="flex justify-center py-8">
          <Spinner label="Loading lyrics" />
        </div>
      </section>
    );
  }

  if (lyrics.isError || lyrics.data.lyrics.length === 0) {
    return (
      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold text-fg">Lyrics</h2>
        <EmptyState title="No lyrics" description="No lyrics found for this track." />
      </section>
    );
  }

  const renderVote = votingOn
    ? (lyric: LyricsOut) => (
        <VoteButtons
          netScore={lyric.net_score}
          value={toVoteValue(myVotes[lyric.id])}
          canVote={!anonymous}
          onVote={(next) =>
            vote.mutate(
              { path: { lyrics_id: lyric.id }, body: { value: voteVerb(next) } },
              {
                onSuccess: (res) =>
                  setMyVotes((prev) => ({
                    ...prev,
                    [lyric.id]: res.your_vote ?? null,
                  })),
                onError: (e) => reportError(e, "Your vote didn't go through."),
              },
            )
          }
        />
      )
    : undefined;

  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-lg font-semibold text-fg">Lyrics</h2>
      <SyncedLyricsViewer lyrics={lyrics.data.lyrics} renderVote={renderVote} />
    </section>
  );
}
