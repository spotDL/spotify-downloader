import {
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from "@tanstack/react-query";
// The generated TanStack Query factories are the ONLY data-fetch surface
// (spec §3); these app hooks wrap them so components never touch the SDK.
import {
  cancelDownloadApiV1DownloadsJobIdDeleteMutation,
  listDownloadsApiV1DownloadsGetOptions,
  submitDownloadApiV1DownloadsPostMutation,
} from "./generated/@tanstack/react-query.gen";
import type { DownloadStatus } from "./generated/types.gen";
import { resolveHttpBase } from "./client";

// Every `GET /downloads` query key carries this stable `_id` tag (see the
// generated `createQueryKey`). Matching on it invalidates *all* filtered
// downloads pages at once — the queue and the library share one server truth
// (CONTRACT D/E: after a submit/cancel or a terminal WS event, refetch).
export const DOWNLOADS_QUERY_ID = "listDownloadsApiV1DownloadsGet";

/** Invalidate every cached `GET /downloads` page regardless of its filters. */
export function invalidateDownloads(queryClient: QueryClient): Promise<void> {
  return queryClient.invalidateQueries({
    predicate: (query) =>
      (query.queryKey[0] as { _id?: string } | undefined)?._id ===
      DOWNLOADS_QUERY_ID,
  });
}

export type DownloadsFilter = {
  status?: DownloadStatus;
  batchId?: string;
  limit?: number;
};

/** `GET /downloads?status=&batch_id=&limit=` — a page of queue rows. */
export function useDownloads(filter: DownloadsFilter = {}) {
  return useQuery(
    listDownloadsApiV1DownloadsGetOptions({
      query: {
        ...(filter.status ? { status: filter.status } : {}),
        ...(filter.batchId ? { batch_id: filter.batchId } : {}),
        ...(filter.limit !== undefined ? { limit: filter.limit } : {}),
      },
    }),
  );
}

/**
 * `POST /downloads` — submit a query (URL / `provider:type:id` ref / an entity
 * id); the server expands albums & playlists into N jobs. Invalidates the
 * downloads cache on success so the queue reflects the new batch.
 */
export function useSubmitDownload() {
  const queryClient = useQueryClient();
  return useMutation({
    ...submitDownloadApiV1DownloadsPostMutation(),
    onSuccess: () => invalidateDownloads(queryClient),
  });
}

/** `DELETE /downloads/{job_id}` — cancel a queued/running job. */
export function useCancelDownload() {
  const queryClient = useQueryClient();
  return useMutation({
    ...cancelDownloadApiV1DownloadsJobIdDeleteMutation(),
    onSuccess: () => invalidateDownloads(queryClient),
  });
}

// File links point straight at the server (a browser navigation, not a fetch),
// so they carry the runtime API base (CONTRACT B). The audio-file and batch
// save-file endpoints are open unless the operator sets `downloads_require_auth`
// (default off) — see the report note on the bearer-header limitation.
export function downloadFileUrl(jobId: string): string {
  return `${resolveHttpBase()}/api/v1/downloads/${encodeURIComponent(jobId)}/file`;
}

export function batchSaveFileUrl(batchId: string): string {
  return `${resolveHttpBase()}/api/v1/downloads/batches/${encodeURIComponent(batchId)}/save-file`;
}
