import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import type { LyricsOut, MatchOut, TrackOut } from "../api/generated/types.gen";
import {
  useEnqueueDownload,
  useRefreshTrack,
  useSubmitMatch,
  useSubmitReport,
  useTrack,
  useTrackLyrics,
  useTrackMatches,
  useVoteLyrics,
  useVoteMatch,
} from "../api/queries";
import { reportError } from "../lib/report-error";
import { formatDuration, joinArtists } from "../lib/format";
import { providerMeta, trackProviderUrl } from "../lib/providers";
import { useFeature } from "../app/config";
import { useAuthStore } from "../stores/auth";
import { ActionButton } from "../components/ActionButton";
import { Badge } from "../components/Badge";
import { Card, DetailRow } from "../components/Card";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { Feature } from "../components/Feature";
import { HeroBackdrop } from "../components/HeroBackdrop";
import { Input } from "../components/Input";
import { PlatformLinks, type PlatformLink } from "../components/PlatformLinks";
import { Spinner } from "../components/Spinner";
import { StatChip } from "../components/StatChip";
import { SyncedLyricsViewer } from "../components/SyncedLyricsViewer";
import { toast } from "../components/Toasts";
import { MatchStatusBadge } from "../components/MatchStatusBadge";
import { VuGauge } from "../components/VuGauge";
import { VoteButtons, type VoteValue } from "../components/VoteButtons";
import { DownloadIcon, ExternalIcon, FlagIcon, RefreshIcon } from "../components/icons";

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

  if (track.isPending) {
    return (
      <div className="flex justify-center py-16">
        <Spinner label="Loading track" className="size-8" />
      </div>
    );
  }

  if (track.isError) {
    return (
      <div className="mx-auto max-w-[1080px] px-6 py-16">
        <ErrorState
          title="Couldn't load this track"
          description="The track may not exist, or the server is unreachable."
        />
      </div>
    );
  }

  return <TrackDetail trackId={trackId} t={track.data} />;
}

function TrackDetail({ trackId, t }: { trackId: string; t: TrackOut }) {
  const enqueue = useEnqueueDownload();
  const refresh = useRefreshTrack(trackId);
  const matches = useTrackMatches(trackId);
  const cover = t.album?.cover_url ?? null;
  const matchList = matches.data?.matches ?? [];

  // "Listen on" = the canonical provider link (when buildable) plus each match's
  // audio target, de-duplicated by provider.
  const listen: PlatformLink[] = [];
  const seen = new Set<string>();
  const canonUrl = trackProviderUrl(t.provider, t.provider_id);
  if (canonUrl && t.provider) {
    listen.push({ provider: t.provider, url: canonUrl });
    seen.add(t.provider);
  }
  for (const m of matchList) {
    if (seen.has(m.target_provider)) continue;
    seen.add(m.target_provider);
    listen.push({ provider: m.target_provider, url: m.target_url });
  }

  return (
    <div>
      <div className="grain relative overflow-hidden border-b border-line-soft">
        <HeroBackdrop coverUrl={cover} />
        <div className="relative z-[2] mx-auto max-w-[1080px] px-6">
          <div className="flex flex-col gap-6 pt-9 pb-7 sm:flex-row sm:items-end sm:gap-7">
            <div className="size-40 shrink-0 overflow-hidden rounded-[14px] shadow-[0_24px_60px_-18px_#000] ring-1 ring-white/10 sm:size-[196px]">
              {cover ? (
                <img src={cover} alt="" className="size-full object-cover" />
              ) : (
                <div className="grid size-full place-items-center bg-elevated text-4xl text-ink-4">
                  ♪
                </div>
              )}
            </div>
            <div className="min-w-0 flex-1 pb-1">
              <div className="mb-3.5 flex flex-wrap gap-2">
                <Badge tone="brand">Track</Badge>
                {t.explicit ? <Badge tone="danger">Explicit</Badge> : null}
                {t.popularity != null ? (
                  <Badge tone="muted">★ {t.popularity}</Badge>
                ) : null}
              </div>
              <h1 className="text-[clamp(30px,5vw,52px)] font-black leading-[1.02] tracking-[-0.03em] text-fg">
                {t.name}
              </h1>
              <p className="mt-2 text-[17px] text-ink-2">
                <span className="font-semibold text-fg">{joinArtists(t.artists)}</span>
              </p>
              <div className="mt-4 mb-5 flex flex-wrap gap-x-6 gap-y-2">
                <StatChip label="dur">{formatDuration(t.duration_ms)}</StatChip>
                {t.album?.name ? <StatChip label="album">{t.album.name}</StatChip> : null}
                {t.year ? <StatChip label="year">{t.year}</StatChip> : null}
              </div>
              <div className="flex flex-wrap gap-2.5">
                <Feature flag="downloads">
                  <ActionButton
                    icon={<DownloadIcon className="size-4" />}
                    disabled={enqueue.isPending}
                    onClick={() =>
                      enqueue.mutate(
                        // Post the bare canonical id: the server short-circuits a
                        // UUID to the local DB and picks the best match. Prefixing
                        // `spotify:track:` would route it to Spotify's API → 400.
                        { body: { query: t.id } },
                        {
                          onSuccess: () => toast.info("Added to the download queue."),
                          onError: (e) => reportError(e, "Couldn't enqueue this track."),
                        },
                      )
                    }
                  >
                    {enqueue.isPending ? "Enqueuing…" : "Download best match"}
                  </ActionButton>
                </Feature>
                <ActionButton
                  variant="ghost"
                  icon={<RefreshIcon className="size-4" />}
                  onClick={() => {
                    refresh();
                    toast.info("Refreshing metadata…");
                  }}
                >
                  Refresh metadata
                </ActionButton>
                <Feature flag="voting">
                  <ReportButton subjectId={t.id} />
                </Feature>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-[1080px] px-6">
        <div className="grid gap-5 py-7 lg:grid-cols-[1.9fr_1fr]">
          <div className="flex min-w-0 flex-col gap-5">
            <MatchesCard trackId={trackId} />
            <LyricsSection trackId={trackId} />
          </div>

          <div className="flex min-w-0 flex-col gap-5">
            {listen.length > 0 ? (
              <Card title="Listen on">
                <PlatformLinks links={listen} />
              </Card>
            ) : null}
            <Card title="Details">
              {t.isrc ? <DetailRow label="ISRC">{t.isrc}</DetailRow> : null}
              {t.popularity != null ? (
                <DetailRow label="Popularity">{t.popularity} / 100</DetailRow>
              ) : null}
              <DetailRow label="Matches">{matchList.length}</DetailRow>
              {t.year ? <DetailRow label="Year">{t.year}</DetailRow> : null}
              {t.album?.name ? <DetailRow label="Album">{t.album.name}</DetailRow> : null}
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}

// --- Report ------------------------------------------------------------------

function ReportButton({ subjectId }: { subjectId: string }) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const submit = useSubmitReport();
  const anonymous = useAnonymous();

  return (
    <div className="relative">
      <ActionButton
        variant="ghost"
        icon={<FlagIcon className="size-4" />}
        onClick={() => setOpen((o) => !o)}
      >
        Report
      </ActionButton>
      {open ? (
        <form
          className="absolute left-0 top-full z-10 mt-2 flex w-72 flex-col gap-2 rounded-card border border-line bg-panel p-3 shadow-card"
          title={anonymous ? ANON_VOTE_TOOLTIP : undefined}
          onSubmit={(e) => {
            e.preventDefault();
            const value = reason.trim();
            if (value.length === 0 || anonymous) return;
            submit.mutate(
              {
                body: {
                  subject_type: "track",
                  subject_id: subjectId,
                  reason: value,
                },
              },
              {
                onSuccess: () => {
                  toast.info("Thanks — your report was submitted.");
                  setReason("");
                  setOpen(false);
                },
                onError: (e) => reportError(e, "Couldn't submit that report."),
              },
            );
          }}
        >
          <label className="text-xs font-medium text-ink-2" htmlFor="report-reason">
            What's wrong with this track?
          </label>
          <Input
            id="report-reason"
            aria-label="Report reason"
            placeholder="e.g. wrong title, bad match…"
            value={reason}
            disabled={anonymous || submit.isPending}
            onChange={(e) => setReason(e.target.value)}
          />
          <div className="flex justify-end gap-2">
            <ActionButton variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </ActionButton>
            <ActionButton type="submit" disabled={anonymous || submit.isPending}>
              {submit.isPending ? "Sending…" : "Submit"}
            </ActionButton>
          </div>
        </form>
      ) : null}
    </div>
  );
}

// --- Matches -----------------------------------------------------------------

function MatchesCard({ trackId }: { trackId: string }) {
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

  const list = matches.data?.matches ?? [];

  return (
    <Card
      title="Cross-platform matches"
      action={list.length > 0 ? `${list.length} sources` : undefined}
    >
      {matches.isPending ? (
        <div className="flex justify-center py-8">
          <Spinner label="Loading matches" />
        </div>
      ) : matches.isError ? (
        <ErrorState
          title="Couldn't load matches"
          description="Try refreshing in a moment."
        />
      ) : list.length === 0 ? (
        <EmptyState
          title="No matches yet"
          description="No audio sources have been matched to this track. Submit one below."
        />
      ) : (
        <div className="flex flex-col gap-2.5">
          {list.map((match, i) => {
            const meta = providerMeta(match.target_provider);
            const best = i === 0;
            return (
              <div
                key={match.id}
                className={`flex items-center gap-3.5 rounded-xl bg-elevated p-3 transition-colors hover:bg-hover ${
                  best ? "shadow-[inset_0_0_0_1px_var(--color-emerald)]" : ""
                }`}
              >
                {/* Match.score is the matcher's 0–100 value (v4 parity); VuGauge's
                    contract is 0–1, so normalize here rather than clamp to 100%. */}
                <VuGauge score={match.score / 100} />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[13px] font-semibold text-fg">
                    {match.candidate_name ?? match.target_id}
                  </p>
                  <p className="mt-0.5 flex items-center gap-2 text-[11px] text-muted">
                    <span className={`size-2 rounded-full ${meta.dotClass}`} aria-hidden />
                    <span className="truncate">
                      {meta.label}
                      {match.candidate_duration_ms != null
                        ? ` · ${formatDuration(match.candidate_duration_ms)}`
                        : ""}
                    </span>
                    {best ? (
                      <span className="rounded bg-emerald/10 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wide text-emerald">
                        Best
                      </span>
                    ) : null}
                    {match.status !== "auto" ? (
                      <MatchStatusBadge status={match.status} />
                    ) : null}
                  </p>
                </div>
                <a
                  href={match.target_url}
                  target="_blank"
                  rel="noreferrer"
                  aria-label="Open match"
                  className="text-muted transition-colors hover:text-fg"
                >
                  <ExternalIcon className="size-4" />
                </a>
                <Feature flag="voting">
                  <VoteButtons
                    netScore={match.net_score}
                    value={toVoteValue(myVotes[match.id])}
                    canVote={!anonymous}
                    onVote={(next) => castVote(match, next)}
                  />
                </Feature>
              </div>
            );
          })}
        </div>
      )}

      <Feature flag="voting">
        <div className="mt-4">
          <SubmitMatchForm trackId={trackId} disabled={anonymous} />
        </div>
      </Feature>
    </Card>
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
      <label className="text-xs font-medium text-ink-2" htmlFor="submit-match-url">
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
        <ActionButton type="submit" disabled={disabled || submit.isPending}>
          {submit.isPending ? "Submitting…" : "Submit"}
        </ActionButton>
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
      <Card title="Lyrics">
        <div className="flex justify-center py-8">
          <Spinner label="Loading lyrics" />
        </div>
      </Card>
    );
  }

  if (lyrics.isError || lyrics.data.lyrics.length === 0) {
    return (
      <Card title="Lyrics">
        <EmptyState title="No lyrics" description="No lyrics found for this track." />
      </Card>
    );
  }

  const sources = lyrics.data.lyrics.map((l) => l.source).join(" · ");
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
    <Card title="Lyrics" action={sources}>
      <SyncedLyricsViewer lyrics={lyrics.data.lyrics} renderVote={renderVote} />
    </Card>
  );
}
