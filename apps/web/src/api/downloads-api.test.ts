import { describe, expect, it } from "vitest";
import { QueryClient } from "@tanstack/react-query";
import { listDownloadsApiV1DownloadsGetQueryKey } from "./generated/@tanstack/react-query.gen";
import { invalidateDownloads } from "./downloads";
import { makeDownloadList } from "../test/msw/fixtures";

// The queue and the library are two filtered views of the same server truth, so
// a submit/cancel (and every terminal WS event, Task 9) must invalidate ALL
// downloads pages — the `["downloads"]` contract realized as an `_id` predicate.
describe("invalidateDownloads", () => {
  it("invalidates every downloads page regardless of filters, and nothing else", async () => {
    const queryClient = new QueryClient();
    const completedKey = listDownloadsApiV1DownloadsGetQueryKey({
      query: { status: "completed" },
    });
    const activeKey = listDownloadsApiV1DownloadsGetQueryKey({ query: {} });
    const unrelatedKey = [{ _id: "somethingElse" }] as const;

    queryClient.setQueryData(completedKey, makeDownloadList());
    queryClient.setQueryData(activeKey, makeDownloadList());
    queryClient.setQueryData(unrelatedKey, { ok: true });

    await invalidateDownloads(queryClient);

    expect(queryClient.getQueryState(completedKey)?.isInvalidated).toBe(true);
    expect(queryClient.getQueryState(activeKey)?.isInvalidated).toBe(true);
    expect(queryClient.getQueryState(unrelatedKey)?.isInvalidated).toBe(false);
  });
});
