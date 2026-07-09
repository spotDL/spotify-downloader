import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { server } from "../test/msw/server";
import {
  makeDownloadJob,
  makeDownloadList,
} from "../test/msw/fixtures";
import { MockWebSocket, installMockWebSocket } from "../test/mock-websocket";
import { renderApp } from "../test/render-app";

// The queue mounts the live socket (useProgressSocket); mock it so a test can
// push WS frames and watch the cache-driven UI update — no real server.
let restoreSocket: () => void;
beforeEach(() => {
  restoreSocket = installMockWebSocket();
});
afterEach(() => {
  restoreSocket();
});

function serveDownloads(jobs = [makeDownloadJob({ status: "running", progress: 0 })]) {
  server.use(
    http.get("*/api/v1/downloads", () =>
      HttpResponse.json(makeDownloadList({ jobs, total: jobs.length })),
    ),
  );
}

describe("Downloads page", () => {
  it("renders the queue from the REST list", async () => {
    serveDownloads();
    renderApp("/downloads");

    expect(await screen.findByText("Get Lucky")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "0");
  });

  it("updates a job's progress bar from a WS progress frame", async () => {
    serveDownloads();
    renderApp("/downloads");
    await screen.findByText("Get Lucky");

    const socket = MockWebSocket.instances[0];
    act(() => {
      socket.emitMessage({
        type: "progress",
        job_id: "job-1",
        batch_id: "batch-1",
        overall: 0.5,
        percent: 50,
        phase: "convert",
      });
    });

    await waitFor(() =>
      expect(screen.getByRole("progressbar")).toHaveAttribute(
        "aria-valuenow",
        "50",
      ),
    );
  });

  it("shows a file link when a WS job_finished frame arrives", async () => {
    serveDownloads();
    renderApp("/downloads");
    await screen.findByText("Get Lucky");
    expect(screen.queryByRole("link", { name: "Download" })).not.toBeInTheDocument();

    const socket = MockWebSocket.instances[0];
    act(() => {
      socket.emitMessage({
        type: "job_finished",
        job_id: "job-1",
        batch_id: "batch-1",
        status: "completed",
        skipped: false,
        output_path: "/library/Get Lucky.mp3",
        skip_reason: null,
      });
    });

    const link = await screen.findByRole("link", { name: "Download" });
    expect(link).toHaveAttribute("href", expect.stringContaining("/downloads/job-1/file"));
  });

  it("cancels a job and invalidates the queue", async () => {
    serveDownloads([makeDownloadJob({ status: "queued", progress: 0 })]);
    let listGets = 0;
    let deleted: string | null = null;
    server.use(
      http.get("*/api/v1/downloads", () => {
        listGets += 1;
        return HttpResponse.json(
          makeDownloadList({
            jobs: [makeDownloadJob({ status: "queued", progress: 0 })],
            total: 1,
          }),
        );
      }),
      http.delete("*/api/v1/downloads/:jobId", ({ params }) => {
        deleted = String(params.jobId);
        return HttpResponse.json(
          makeDownloadJob({ status: "cancelled" }),
        );
      }),
    );
    renderApp("/downloads");

    await userEvent.click(await screen.findByRole("button", { name: "Cancel" }));

    await waitFor(() => expect(deleted).toBe("job-1"));
    // Cancel invalidates ["downloads"], so the list is refetched.
    await waitFor(() => expect(listGets).toBeGreaterThanOrEqual(2));
  });
});
