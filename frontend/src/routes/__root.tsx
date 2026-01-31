import { createRootRoute, Link, Outlet } from "@tanstack/react-router";
import { useAuthStore } from "@/stores/auth";
import { useLogout, useHealth } from "@/api";
import { Button, Badge } from "@/components/ui";

export const Route = createRootRoute({
  component: RootLayout,
});

// Logo component with vinyl disc styling
function Logo() {
  return (
    <Link to="/" className="flex items-center gap-3 group">
      <div className="relative w-9 h-9">
        {/* Vinyl outer ring */}
        <div className="absolute inset-0 rounded-full bg-gradient-to-br from-zinc-700 to-zinc-900 shadow-lg" />
        {/* Vinyl grooves */}
        <div className="absolute inset-1 rounded-full border border-zinc-600/30" />
        <div className="absolute inset-2 rounded-full border border-zinc-600/20" />
        {/* Center label with gradient */}
        <div className="absolute inset-[10px] rounded-full bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center">
          <div className="w-1.5 h-1.5 rounded-full bg-zinc-900" />
        </div>
        {/* Spin animation on hover */}
        <div className="absolute inset-0 rounded-full group-hover:animate-[spin_3s_linear_infinite] transition-transform" />
      </div>
      <span className="text-xl font-bold tracking-tight">
        <span className="gradient-text">Spot</span>
        <span className="text-zinc-100">DL</span>
      </span>
    </Link>
  );
}

// Navigation link component
function NavLink({ to, children }: { to: string; children: React.ReactNode }) {
  return (
    <Link
      to={to}
      className="relative px-3 py-2 text-sm font-medium text-zinc-400 hover:text-zinc-100 transition-colors [&.active]:text-emerald-400"
    >
      {children}
      <span className="absolute inset-x-3 -bottom-px h-px bg-gradient-to-r from-emerald-500/0 via-emerald-500 to-emerald-500/0 opacity-0 [.active_&]:opacity-100 transition-opacity" />
    </Link>
  );
}

function RootLayout() {
  const { isAuthenticated, user } = useAuthStore();
  const logoutMutation = useLogout();
  const { isError: isOffline } = useHealth();

  const handleLogout = () => {
    logoutMutation.mutate();
  };

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-zinc-100 flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-50 glass border-b border-zinc-800/50">
        <nav className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          {/* Left section - Logo + Status */}
          <div className="flex items-center gap-6">
            <Logo />
            <div className="h-6 w-px bg-zinc-800" />
            {isOffline ? (
              <Badge variant="warning" size="sm" pulse>
                Offline
              </Badge>
            ) : (
              <Badge variant="success" size="sm" pulse>
                Online
              </Badge>
            )}
          </div>

          {/* Center section - Navigation */}
          <div className="hidden md:flex items-center gap-1">
            <NavLink to="/">Home</NavLink>
            <NavLink to="/queue">Queue</NavLink>
            <NavLink to="/matching">Matching</NavLink>
            <NavLink to="/settings">Settings</NavLink>
          </div>

          {/* Right section - Auth */}
          <div className="flex items-center gap-3">
            {isAuthenticated ? (
              <>
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-zinc-800/50">
                  <div className="w-6 h-6 rounded-full bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center text-xs font-bold text-white">
                    {user?.username?.charAt(0).toUpperCase()}
                  </div>
                  <span className="text-sm text-zinc-300">{user?.username}</span>
                </div>
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
        </nav>
      </header>

      {/* Main content */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-10">
        <div className="animate-fade-in">
          <Outlet />
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-800/50 py-6">
        <div className="max-w-6xl mx-auto px-6 flex items-center justify-between">
          <p className="text-sm text-zinc-500">
            SpotDL v5.0.0
          </p>
          <div className="flex items-center gap-4">
            <a
              href="https://github.com/spotDL/spotify-downloader"
              target="_blank"
              rel="noopener noreferrer"
              className="text-zinc-500 hover:text-zinc-300 transition-colors"
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.17 6.839 9.49.5.092.682-.217.682-.482 0-.237-.008-.866-.013-1.7-2.782.604-3.369-1.34-3.369-1.34-.454-1.156-1.11-1.463-1.11-1.463-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.831.092-.646.35-1.086.636-1.336-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0112 6.836c.85.004 1.705.114 2.504.336 1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C19.138 20.167 22 16.418 22 12c0-5.523-4.477-10-10-10z" />
              </svg>
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
