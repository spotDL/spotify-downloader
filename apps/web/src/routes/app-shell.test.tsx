import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import type { DeploymentMode } from "../api/generated/types.gen";
import { server } from "../test/msw/server";
import { makeConfig } from "../test/msw/fixtures";
import { renderApp } from "../test/render-app";

// CONTRACT G — nav links are gated by the /config feature flags, which the
// server computes from the deployment mode (fixtures.ts MODE_FLAGS):
//   selfhost → downloads+library+auth+voting on
//   hosted   → downloads+library off, auth on
//   embedded → downloads+library on, auth off

function serveMode(mode: DeploymentMode) {
  server.use(http.get("*/api/v1/config", () => HttpResponse.json(makeConfig({ mode }))));
}

async function renderInMode(mode: DeploymentMode) {
  serveMode(mode);
  renderApp();
  // Wait for the gate to render the shell.
  await screen.findByRole("navigation", { name: "Primary" });
}

describe("AppShell gated nav", () => {
  it("always shows Home and Settings", async () => {
    await renderInMode("selfhost");
    expect(screen.getByRole("link", { name: "Home" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Settings" })).toBeInTheDocument();
  });

  it("selfhost shows Downloads, Library, and Sign in", async () => {
    await renderInMode("selfhost");
    expect(screen.getByRole("link", { name: "Downloads" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Library" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in" })).toBeInTheDocument();
  });

  it("hosted hides Downloads and Library but shows Sign in", async () => {
    await renderInMode("hosted");
    expect(screen.queryByRole("link", { name: "Downloads" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Library" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in" })).toBeInTheDocument();
  });

  it("embedded shows Downloads and Library but hides Sign in (auth off)", async () => {
    await renderInMode("embedded");
    expect(screen.getByRole("link", { name: "Downloads" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Library" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Sign in" })).not.toBeInTheDocument();
  });
});
