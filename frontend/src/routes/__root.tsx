import { createRootRoute, Link, Outlet } from "@tanstack/react-router";

export const Route = createRootRoute({
  component: () => (
    <div className="min-h-screen bg-gray-900 text-white">
      <nav className="border-b border-gray-800 px-6 py-4">
        <div className="flex items-center justify-between max-w-6xl mx-auto">
          <Link to="/" className="text-xl font-bold text-green-500">
            SpotDL
          </Link>
          <div className="flex gap-4">
            <Link
              to="/"
              className="hover:text-green-400 transition-colors [&.active]:text-green-500"
            >
              Home
            </Link>
            <Link
              to="/queue"
              className="hover:text-green-400 transition-colors [&.active]:text-green-500"
            >
              Queue
            </Link>
            <Link
              to="/matching"
              className="hover:text-green-400 transition-colors [&.active]:text-green-500"
            >
              Matching
            </Link>
            <Link
              to="/settings"
              className="hover:text-green-400 transition-colors [&.active]:text-green-500"
            >
              Settings
            </Link>
          </div>
        </div>
      </nav>
      <main className="max-w-6xl mx-auto px-6 py-8">
        <Outlet />
      </main>
    </div>
  ),
});
