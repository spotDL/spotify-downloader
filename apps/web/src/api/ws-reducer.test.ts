import { describe, expect, it } from "vitest";
import { QueryClient } from "@tanstack/react-query";
import {
  getBatchApiV1DownloadsBatchesBatchIdGetQueryKey,
  listDownloadsApiV1DownloadsGetQueryKey,
} from "./generated/@tanstack/react-query.gen";
import type { DownloadListResponse } from "./generated/types.gen";
import { WS_PROTOCOL_VERSION } from "./ws-protocol";
import { applyWsMessage } from "./ws-reducer";
import { makeDownloadBatch, makeDownloadJob } from "../test/msw/fixtures";

// CONTRACT E — applyWsMessage is a pure cache reducer: it is the ONLY writer of
// download server-state from the socket, so there is no parallel store. Progress
// patches the job row in place (no refetch); terminal + batch events invalidate
// the affected batch query. A hello frame reports protocol compatibility.

const LIST_KEY = listDownloadsApiV1DownloadsGetQueryKey({ query: {} });
const BATCH_KEY = getBatchApiV1DownloadsBatchesBatchIdGetQueryKey({
  path: { batch_id: "batch-1" },
});

function seed() {
  const queryClient = new QueryClient();
  queryClient.setQueryData<DownloadListResponse>(LIST_KEY, {
    jobs: [
      makeDownloadJob({
        id: "job-1",
        batch_id: "batch-1",
        status: "queued",
        progress: 0,
        output_path: null,
      }),
    ],
    total: 1,
    limit: 50,
    offset: 0,
  });
  queryClient.setQueryData(BATCH_KEY, makeDownloadBatch());
  return queryClient;
}

function job(queryClient: QueryClient) {
  return queryClient.getQueryData<DownloadListResponse>(LIST_KEY)!.jobs[0];
}

describe("applyWsMessage", () => {
  it("patches a job's progress in place, without invalidating the list", () => {
    const queryClient = seed();
    const result = applyWsMessage(queryClient, {
      type: "progress",
      job_id: "job-1",
      batch_id: "batch-1",
      overall: 0.5,
      percent: 50,
      phase: "convert",
    });

    expect(result).toEqual({ type: "applied" });
    expect(job(queryClient).progress).toBe(0.5);
    expect(job(queryClient).status).toBe("running");
    // The list is patched, not refetched (CONTRACT E).
    expect(queryClient.getQueryState(LIST_KEY)?.isInvalidated).toBe(false);
  });

  it("marks a started job running", () => {
    const queryClient = seed();
    applyWsMessage(queryClient, {
      type: "job_started",
      job_id: "job-1",
      batch_id: "batch-1",
    });
    expect(job(queryClient).status).toBe("running");
    expect(queryClient.getQueryState(LIST_KEY)?.isInvalidated).toBe(false);
  });

  it("refetches the list on job_queued (a new row it can't synthesize)", () => {
    const queryClient = seed();
    applyWsMessage(queryClient, {
      type: "job_queued",
      job_id: "job-2",
      batch_id: "batch-1",
      list_length: 2,
      list_position: 2,
      track_name: "Instant Crush",
    });
    expect(queryClient.getQueryState(LIST_KEY)?.isInvalidated).toBe(true);
  });

  it("completes a job with its file path and invalidates the batch", () => {
    const queryClient = seed();
    applyWsMessage(queryClient, {
      type: "job_finished",
      job_id: "job-1",
      batch_id: "batch-1",
      status: "completed",
      skipped: false,
      output_path: "/library/Get Lucky.mp3",
      skip_reason: null,
    });
    expect(job(queryClient).status).toBe("completed");
    expect(job(queryClient).progress).toBe(1);
    expect(job(queryClient).output_path).toBe("/library/Get Lucky.mp3");
    // Terminal → the batch query (counts, save-file) is invalidated, but the
    // in-place list patch survives (no list refetch to clobber the file link).
    expect(queryClient.getQueryState(BATCH_KEY)?.isInvalidated).toBe(true);
    expect(queryClient.getQueryState(LIST_KEY)?.isInvalidated).toBe(false);
  });

  it("fails a job with its error and invalidates the batch", () => {
    const queryClient = seed();
    applyWsMessage(queryClient, {
      type: "job_failed",
      job_id: "job-1",
      batch_id: "batch-1",
      error: "no audio source",
      step: "fetch",
    });
    expect(job(queryClient).status).toBe("failed");
    expect(job(queryClient).error_message).toBe("no audio source");
    expect(queryClient.getQueryState(BATCH_KEY)?.isInvalidated).toBe(true);
  });

  it("cancels a job and invalidates the batch", () => {
    const queryClient = seed();
    applyWsMessage(queryClient, {
      type: "job_cancelled",
      job_id: "job-1",
      batch_id: "batch-1",
    });
    expect(job(queryClient).status).toBe("cancelled");
    expect(queryClient.getQueryState(BATCH_KEY)?.isInvalidated).toBe(true);
  });

  it("invalidates the batch and the list on batch_finished", () => {
    const queryClient = seed();
    applyWsMessage(queryClient, {
      type: "batch_finished",
      batch_id: "batch-1",
      completed: 1,
      failed: 0,
      skipped: 0,
      cancelled: 0,
      m3u_paths: ["/library/mix.m3u8"],
      save_file_path: "/library/mix.spotdl",
    });
    expect(queryClient.getQueryState(BATCH_KEY)?.isInvalidated).toBe(true);
    expect(queryClient.getQueryState(LIST_KEY)?.isInvalidated).toBe(true);
  });

  it("flags a hello with an unsupported protocol version", () => {
    const queryClient = seed();
    expect(
      applyWsMessage(queryClient, { type: "hello", protocol_version: 999 }),
    ).toEqual({ type: "hello", compatible: false, version: 999 });
    expect(
      applyWsMessage(queryClient, {
        type: "hello",
        protocol_version: WS_PROTOCOL_VERSION,
      }),
    ).toEqual({ type: "hello", compatible: true, version: WS_PROTOCOL_VERSION });
  });
});
