import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/settings")({
  component: SettingsPage,
});

function SettingsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Settings</h1>

      <div className="bg-gray-800 rounded-lg p-6 space-y-4">
        <h2 className="text-lg font-semibold">Download Options</h2>

        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <label className="text-gray-300">Output Format</label>
            <select className="bg-gray-700 border border-gray-600 rounded px-3 py-1">
              <option>MP3</option>
              <option>FLAC</option>
              <option>OGG</option>
              <option>M4A</option>
            </select>
          </div>

          <div className="flex justify-between items-center">
            <label className="text-gray-300">Audio Quality</label>
            <select className="bg-gray-700 border border-gray-600 rounded px-3 py-1">
              <option>Best</option>
              <option>320kbps</option>
              <option>256kbps</option>
              <option>192kbps</option>
            </select>
          </div>

          <div className="flex justify-between items-center">
            <label className="text-gray-300">Embed Metadata</label>
            <input type="checkbox" defaultChecked className="w-5 h-5" />
          </div>
        </div>
      </div>

      <div className="bg-gray-800 rounded-lg p-6 space-y-4">
        <h2 className="text-lg font-semibold">Server</h2>

        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <label className="text-gray-300">API URL</label>
            <input
              type="text"
              defaultValue="http://localhost:8000"
              className="bg-gray-700 border border-gray-600 rounded px-3 py-1 w-64"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
