import { createRootRoute, Link, Outlet } from "@tanstack/react-router";
import { useAuthStore } from "@/stores/auth";
import { useLogout, useHealth } from "@/api";
import { Button, Badge } from "@/components/ui";

export const Route = createRootRoute({
  component: RootLayout,
});

function RootLayout() {
  const { isAuthenticated, user } = useAuthStore();
  const logoutMutation = useLogout();
  const { isError: isOffline } = useHealth();

  const handleLogout = () => {
    logoutMutation.mutate();
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <nav className="border-b border-gray-800 px-6 py-4">
        <div className="flex items-center justify-between max-w-6xl mx-auto">
          <div className="flex items-center gap-4">
            <Link to="/" className="text-xl font-bold text-green-500">
              SpotDL
            </Link>
            {isOffline ? (
              <Badge variant="warning">Offline</Badge>
            ) : (
              <Badge variant="success">Online</Badge>
            )}
          </div>

          <div className="flex items-center gap-6">
            {/* Navigation Links */}
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

            {/* Auth Section */}
            <div className="flex items-center gap-2 border-l border-gray-700 pl-6">
              {isAuthenticated ? (
                <>
                  <span className="text-sm text-gray-400">
                    {user?.username}
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleLogout}
                    isLoading={logoutMutation.isPending}
                  >
                    Logout
                  </Button>
                </>
              ) : (
                <>
                  <Link to="/auth/login">
                    <Button variant="ghost" size="sm">
                      Login
                    </Button>
                  </Link>
                  <Link to="/auth/register">
                    <Button variant="primary" size="sm">
                      Sign Up
                    </Button>
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-6xl mx-auto px-6 py-8">
        <Outlet />
      </main>

      <footer className="border-t border-gray-800 px-6 py-4 mt-auto">
        <div className="max-w-6xl mx-auto text-center text-sm text-gray-500">
          <p>
            SpotDL v5.0.0 •{" "}
            <a
              href="https://github.com/spotDL/spotify-downloader"
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-400 hover:text-gray-300"
            >
              GitHub
            </a>
          </p>
        </div>
      </footer>
    </div>
  );
}
