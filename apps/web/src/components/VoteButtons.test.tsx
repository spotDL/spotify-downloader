import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { VoteButtons } from "./VoteButtons";

describe("VoteButtons", () => {
  it("optimistically toggles the vote and reports the next value", async () => {
    const user = userEvent.setup();
    const onVote = vi.fn();
    render(<VoteButtons value={0} canVote onVote={onVote} />);

    const up = screen.getByRole("button", { name: "Upvote" });
    await user.click(up);
    expect(up).toHaveAttribute("aria-pressed", "true"); // optimistic flip
    expect(onVote).toHaveBeenLastCalledWith(1);

    // Re-clicking retracts (back to 0).
    await user.click(up);
    expect(up).toHaveAttribute("aria-pressed", "false");
    expect(onVote).toHaveBeenLastCalledWith(0);
  });

  it("switches sides when the opposite button is clicked", async () => {
    const user = userEvent.setup();
    const onVote = vi.fn();
    render(<VoteButtons value={1} canVote onVote={onVote} />);

    await user.click(screen.getByRole("button", { name: "Downvote" }));
    expect(screen.getByRole("button", { name: "Downvote" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: "Upvote" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    expect(onVote).toHaveBeenLastCalledWith(-1);
  });

  it("disables both buttons with a sign-in tooltip when the viewer can't vote", () => {
    render(<VoteButtons value={0} canVote={false} />);
    const up = screen.getByRole("button", { name: "Upvote" });
    const down = screen.getByRole("button", { name: "Downvote" });
    expect(up).toBeDisabled();
    expect(down).toBeDisabled();
    expect(up).toHaveAttribute("title", "Sign in to vote");
  });
});
