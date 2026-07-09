import type { QueryClient } from "@tanstack/react-query";
import type { DownloadJobOut, DownloadListResponse } from "./generated/types.gen";
import type { Severity } from "./errors";
import type { WsMessage, WsBatchFinished } from "./ws-types.gen";
import { WS_PROTOCOL_VERSION } from "./ws-protocol";
import { DOWNLOADS_QUERY_ID, invalidateDownloads } from "./downloads";

// The batch detail query's stable `_id` tag (generated createQueryKey).
const BATCH_QUERY_ID = "getBatchApiV1DownloadsBatchesBatchIdGet";

/** A toast the socket layer should raise as a side effect of a pure fold. */
export type WsToastSignal = { message: string; severity: Severity };

/**
 * The result of folding one WS frame into the cache. A `hello` frame reports
 * protocol compatibility (the hook tears the socket down on a mismatch); every
 * other frame is `applied` to the cache. `applied` may carry a `toast` the
 * transport layer should surface (the reducer stays pure — CONTRACT E — so it
 * *describes* the toast rather than calling the toast store itself).
 */
export type WsApplyResult =
  | { type: "applied"; toast?: WsToastSignal }
  | { type: "hello"; compatible: boolean; version: number | undefined };

/**
 * CONTRACT E — the pure event→cache reducer and the *only* writer of download
 * server-state from the socket (so there is no parallel store). Progress and
 * lifecycle events patch the job row(s) in place with no refetch; terminal and
 * batch events additionally invalidate the affected batch query. Returns a
 * `hello` result so the caller can verify the protocol version.
 */
export function applyWsMessage(
  queryClient: QueryClient,
  msg: WsMessage,
): WsApplyResult {
  switch (msg.type) {
    case "hello":
      return {
        type: "hello",
        compatible: msg.protocol_version === WS_PROTOCOL_VERSION,
        version: msg.protocol_version,
      };

    case "job_queued":
      // A brand-new row we can't fully synthesize from the event — refetch.
      void invalidateDownloads(queryClient);
      return { type: "applied" };

    case "job_started":
      patchJob(queryClient, msg.job_id, { status: "running" });
      return { type: "applied" };

    case "progress":
      // `overall` is the 0..1 fraction the server persists as job.progress.
      patchJob(queryClient, msg.job_id, {
        status: "running",
        progress: msg.overall,
      });
      return { type: "applied" };

    case "job_finished":
      patchJob(queryClient, msg.job_id, {
        status: "completed",
        progress: 1,
        output_path: msg.output_path,
        skip_reason: msg.skip_reason,
      });
      invalidateBatch(queryClient, msg.batch_id);
      return { type: "applied" };

    case "job_failed":
      patchJob(queryClient, msg.job_id, {
        status: "failed",
        error_message: msg.error,
        error_step: msg.step,
      });
      invalidateBatch(queryClient, msg.batch_id);
      return { type: "applied" };

    case "job_cancelled":
      patchJob(queryClient, msg.job_id, { status: "cancelled" });
      invalidateBatch(queryClient, msg.batch_id);
      return { type: "applied" };

    case "batch_finished":
      invalidateBatch(queryClient, msg.batch_id);
      void invalidateDownloads(queryClient);
      return { type: "applied", toast: batchFinishedToast(msg) };

    default:
      return { type: "applied" };
  }
}

/**
 * The CONTRACT E batch-complete toast: the done/failed/skipped tally plus a note
 * on which playlist artifacts (save file, m3u playlists) landed on disk. Warns
 * when anything failed, otherwise informational.
 */
function batchFinishedToast(msg: WsBatchFinished): WsToastSignal {
  const artifacts: string[] = [];
  if (msg.save_file_path) artifacts.push("save file");
  if (msg.m3u_paths.length > 0) {
    artifacts.push(
      msg.m3u_paths.length === 1
        ? "M3U playlist"
        : `${msg.m3u_paths.length} M3U playlists`,
    );
  }
  const tally = `${msg.completed} done, ${msg.failed} failed, ${msg.skipped} skipped`;
  const suffix = artifacts.length > 0 ? ` — ${artifacts.join(" + ")} saved` : "";
  return {
    message: `Batch complete: ${tally}${suffix}`,
    severity: msg.failed > 0 ? "warn" : "info",
  };
}

/** Patch one job (by id) across every cached downloads-list page, in place. */
function patchJob(
  queryClient: QueryClient,
  jobId: string,
  patch: Partial<DownloadJobOut>,
): void {
  queryClient.setQueriesData<DownloadListResponse>(
    {
      predicate: (query) =>
        (query.queryKey[0] as { _id?: string } | undefined)?._id ===
        DOWNLOADS_QUERY_ID,
    },
    (old) => {
      if (!old) return old;
      let changed = false;
      const jobs = old.jobs.map((job) => {
        if (job.id !== jobId) return job;
        changed = true;
        return { ...job, ...patch };
      });
      return changed ? { ...old, jobs } : old;
    },
  );
}

/** Invalidate a single batch's detail query (terminal/batch events). */
function invalidateBatch(
  queryClient: QueryClient,
  batchId: string | null,
): void {
  if (!batchId) return;
  void queryClient.invalidateQueries({
    predicate: (query) => {
      const key = query.queryKey[0] as
        | { _id?: string; path?: { batch_id?: string } }
        | undefined;
      return key?._id === BATCH_QUERY_ID && key.path?.batch_id === batchId;
    },
  });
}
