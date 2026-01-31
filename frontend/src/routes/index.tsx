import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";

export const Route = createFileRoute("/")({
  component: HomePage,
});

function HomePage() {
  const [searchQuery, setSearchQuery] = useState("");

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    // TODO: Implement search
    console.log("Searching for:", searchQuery);
  };

  return (
    <div className="space-y-8">
      <div className="text-center space-y-4">
        <h1 className="text-4xl font-bold">
          Download Music from <span className="text-green-500">Any Platform</span>
        </h1>
        <p className="text-gray-400 max-w-xl mx-auto">
          Enter a song URL from Spotify, Apple Music, Deezer, YouTube Music, or
          any supported platform to find and download the best audio match.
        </p>
      </div>

      <form onSubmit={handleSearch} className="max-w-2xl mx-auto">
        <div className="flex gap-2">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Paste a song URL or search..."
            className="flex-1 px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:border-green-500 transition-colors"
          />
          <button
            type="submit"
            className="px-6 py-3 bg-green-600 hover:bg-green-500 rounded-lg font-medium transition-colors"
          >
            Search
          </button>
        </div>
      </form>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-2xl mx-auto">
        {["Spotify", "Apple Music", "Deezer", "YouTube Music"].map(
          (platform) => (
            <div
              key={platform}
              className="p-4 bg-gray-800 rounded-lg text-center text-sm text-gray-400"
            >
              {platform}
            </div>
          )
        )}
      </div>
    </div>
  );
}
