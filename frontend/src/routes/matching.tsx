import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/matching")({
  component: MatchingPage,
});

function MatchingPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Match Voting</h1>
      <p className="text-gray-400">
        Help improve matching accuracy by voting on song matches.
        Login required to vote.
      </p>
      <div className="bg-gray-800 rounded-lg p-8 text-center text-gray-400">
        <p>Login to vote on matches</p>
      </div>
    </div>
  );
}
