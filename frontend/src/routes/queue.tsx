import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/queue")({
  component: QueuePage,
});

function QueuePage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Download Queue</h1>
      <div className="bg-gray-800 rounded-lg p-8 text-center text-gray-400">
        <p>No downloads in queue</p>
        <p className="text-sm mt-2">
          Search for a song to start downloading
        </p>
      </div>
    </div>
  );
}
