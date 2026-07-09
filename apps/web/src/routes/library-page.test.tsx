import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "../test/msw/server";
import {
  makeConfig,
  makeDownloadJob,
  makeDownloadList,
} from "../test/msw/fixtures";
import { renderApp } from "../test/render-app";

function serveCompleted() {
  server.use(
    http.get("*/api/v1/downloads", () =>
      HttpResponse.json(
        makeDownloadList({
          jobs: [
            makeDownloadJob({
              status: "completed",
              progress: 1,
              output_path: "/library/Get Lucky.mp3",
            }),
          ],
          total: 1,
        }),
      ),
    ),
  );
}

describe("Library page", () => {
  it("lists completed downloads with file and batch save-file links", async () => {
    serveCompleted();
    renderApp("/library");

    expect(await screen.findByText("Get Lucky")).toBeInTheDocument();
    const fileLink = screen.getByRole("link", { name: "Download" });
    expect(fileLink).toHaveAttribute(
      "href",
      expect.stringContaining("/downloads/job-1/file"),
    );
    const saveFile = screen.getByRole("link", { name: /save file/i });
    expect(saveFile).toHaveAttribute(
      "href",
      expect.stringContaining("/downloads/batches/batch-1/save-file"),
    );
  });

  it("is unavailable when the library feature is off", async () => {
    server.use(
      http.get("*/api/v1/config", () =>
        HttpResponse.json(makeConfig({ mode: "hosted" })),
      ),
    );
    renderApp("/library");

    expect(
      await screen.findByText(/not available on this server/i),
    ).toBeInTheDocument();
  });
});
