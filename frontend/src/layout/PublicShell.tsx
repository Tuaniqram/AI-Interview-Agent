import { Outlet, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export function PublicShell() {
  const { isAuthenticated, isLoading } = useAuth();

  return (
    <div className="min-h-screen bg-[var(--bg-page)] flex flex-col">
      <header className="border-b border-[var(--border-color)] bg-[var(--bg-section)]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link to="/" className="text-xl font-bold text-[var(--text-primary)]">
            AI Interview Agent
          </Link>
          <nav className="flex items-center gap-4">
            {isLoading ? null : isAuthenticated ? (
              <Link
                to="/dashboard"
                className="text-sm px-4 py-2 rounded-lg bg-[var(--action-primary)] text-white hover:opacity-90"
              >
                Dashboard
              </Link>
            ) : (
              <>
                <Link to="/login" className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]">
                  Sign In
                </Link>
                <Link
                  to="/register"
                  className="text-sm px-4 py-2 rounded-lg bg-[var(--action-primary)] text-white hover:opacity-90"
                >
                  Get Started
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>
      <main className="flex-1">
        <Outlet />
      </main>
      <footer className="border-t border-[var(--border-color)] py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-sm text-[var(--text-secondary)]">
          AI Interview Agent. All rights reserved.
        </div>
      </footer>
    </div>
  );
}
