import { useState } from 'react';
import { Outlet, Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useCandidateAuth } from '../contexts/CandidateAuthContext';
import { OpportunityHubSidebar } from '../components/opportunity-hub/OpportunityHubSidebar';
import type { HubFilters } from '../components/opportunity-hub/OpportunityHubSidebar';
import { Menu, Search, LogIn, UserPlus, LayoutDashboard } from 'lucide-react';

export function OpportunityHubLayout() {
  const { isAuthenticated, isLoading, user, logout } = useAuth();
  const { isAuthenticated: isCandidateAuth, isLoading: isCandidateLoading, logout: candidateLogout, candidate } = useCandidateAuth();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [filters, setFilters] = useState<HubFilters>({ modes: [], expiry: 'any' });

  const applyFilters = () => {
    const params = new URLSearchParams();
    if (search) params.set('search', search);
    if (filters.modes.length) params.set('modes', filters.modes.join(','));
    if (filters.expiry !== 'any') params.set('expiry', filters.expiry);
    navigate({ pathname: '/opportunity-hub', search: params.toString() });
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    applyFilters();
  };

  return (
    <div className="h-screen bg-[var(--bg-page)] flex flex-col overflow-hidden">
      <header className="shrink-0 z-30 h-16 bg-[var(--bg-section)]/90 backdrop-blur-md border-b border-[var(--border-color)]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-full flex items-center gap-4">
          <button
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden p-2 -ml-2 rounded-lg text-secondary hover:text-primary hover:bg-hover"
            aria-label="Open sidebar"
          >
            <Menu className="w-5 h-5" />
          </button>

          <Link to="/opportunity-hub" className="flex items-center gap-2.5 shrink-0">
            <img src="/favicon.svg" className="w-7 h-7" alt="" />
            <span className="font-semibold text-primary hidden sm:inline font-heading">Opportunity Hub</span>
          </Link>

          <form onSubmit={handleSearch} className="flex-1 max-w-md mx-auto hidden md:block">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" />
              <input
                type="text"
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search organizations..."
                className="w-full pl-9 pr-3 py-2 text-sm bg-[var(--bg-page)] text-primary rounded-lg border border-[var(--border-color)] focus:outline-none focus:ring-2 focus:ring-[#7C3AED]/30 focus:border-[#7C3AED] placeholder:text-muted transition-colors"
              />
            </div>
          </form>

          <nav className="flex items-center gap-3 ms-auto">
            {!isLoading && !isCandidateLoading && (isAuthenticated || isCandidateAuth) ? (
              <>
                {isAuthenticated ? (
                  <Link
                    to="/dashboard"
                    className="flex items-center gap-2 text-sm px-3 py-2 rounded-lg text-secondary hover:text-primary hover:bg-hover transition-colors"
                  >
                    <LayoutDashboard className="w-4 h-4" />
                    <span className="hidden sm:inline">Dashboard</span>
                  </Link>
                ) : (
                  <Link
                    to="/candidate/dashboard"
                    className="flex items-center gap-2 text-sm px-3 py-2 rounded-lg text-secondary hover:text-primary hover:bg-hover transition-colors"
                  >
                    <LayoutDashboard className="w-4 h-4" />
                    <span className="hidden sm:inline">Dashboard</span>
                  </Link>
                )}
                <div className="flex items-center gap-2 pl-2 border-l border-[var(--border-color)]">
                  <div className="w-6 h-6 rounded-full bg-[#7C3AED] flex items-center justify-center text-white text-xs font-medium">
                    {(isAuthenticated ? user?.name : candidate?.name)?.charAt(0)?.toUpperCase() || '?'}
                  </div>
                  <button
                    onClick={() => {
                      if (isAuthenticated) logout();
                      else candidateLogout();
                      navigate('/');
                    }}
                    className="text-xs text-red-500 hover:text-red-600"
                  >
                    Sign Out
                  </button>
                </div>
              </>
            ) : isCandidateLoading || isLoading ? null : (
              <>
                <Link
                  to="/login"
                  className="flex items-center gap-1.5 text-sm px-3 py-2 rounded-lg text-secondary hover:text-primary hover:bg-hover transition-colors"
                >
                  <LogIn className="w-4 h-4" />
                  <span className="hidden sm:inline">Sign In</span>
                </Link>
                <Link
                  to="/register"
                  className="flex items-center gap-1.5 text-sm px-4 py-2 rounded-lg bg-[#7C3AED] text-white hover:bg-[#6D28D9] transition-colors"
                >
                  <UserPlus className="w-4 h-4" />
                  <span className="hidden sm:inline">Get Started</span>
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        <OpportunityHubSidebar
          open={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          isAuthenticated={isAuthenticated}
          filters={filters}
          onFiltersChange={setFilters}
          onApply={applyFilters}
        />

        <main className="flex-1 min-w-0 overflow-y-auto">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 animate-fade-in">
            <Outlet context={{ search, setSearch }} />
          </div>
        </main>
      </div>
    </div>
  );
}
