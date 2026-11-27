import { Outlet, Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useCandidateAuth } from '../contexts/CandidateAuthContext';

/**
 * The public hub: a plain top bar (name, then account links); each page opens with a full-width banner.
 * No sidebar: the hub has one filter, and it lives with the list it filters.
 */
export function OpportunityHubLayout() {
  const { isAuthenticated, isLoading, user, logout } = useAuth();
  const { isAuthenticated: isCandidateAuth, isLoading: isCandidateLoading, logout: candidateLogout, candidate } = useCandidateAuth();
  const navigate = useNavigate();

  const ready = !isLoading && !isCandidateLoading;
  const signedIn = isAuthenticated || isCandidateAuth;
  const name = isAuthenticated ? user?.name : candidate?.name;

  const signOut = () => {
    try {
      if (isAuthenticated) logout();
      else candidateLogout();
    } finally {
      navigate('/');
    }
  };

  const linkCls = 'h-8 px-3 inline-flex items-center rounded-md text-[13px] text-secondary hover:text-primary hover:bg-hover transition-colors';

  return (
    <div className="min-h-screen bg-page flex flex-col">
      <header className="sticky top-0 z-30 h-14 bg-page/95 backdrop-blur border-b border-border">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 h-full flex items-center gap-3">
          <Link to="/opportunity-hub" className="flex items-center gap-2 shrink-0 rounded-md">
            <img src="/favicon.svg" className="w-6 h-6" alt="" />
            <span className="text-sm font-semibold text-primary">Opportunity Hub</span>
          </Link>

          <nav className="ms-auto flex items-center gap-1" aria-label="Account">
            {!ready ? null : signedIn ? (
              <>
                <Link to={isAuthenticated ? '/dashboard' : '/candidate/dashboard'} className={linkCls}>Dashboard</Link>
                <span className="hidden sm:inline-flex items-center gap-2 pl-3 ml-1 border-l border-border text-[13px] text-secondary">
                  <span className="w-6 h-6 rounded-full bg-hover border border-border flex items-center justify-center text-[11px] font-medium text-primary" aria-hidden>
                    {name?.charAt(0)?.toUpperCase() || '?'}
                  </span>
                  <span className="max-w-[12rem] truncate">{name}</span>
                </span>
                <button onClick={signOut} className={linkCls}>Sign out</button>
              </>
            ) : (
              <>
                <Link to="/account" className={linkCls}>Sign in</Link>
                <Link
                  to="/candidate/register"
                  className="h-8 px-3 inline-flex items-center rounded-md text-[13px] font-medium bg-action-primary text-action-primary-text hover:bg-action-primary-hover transition-colors"
                >
                  Create account
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>

      {/* Pages draw their own full-width banner, then their body (see HubBanner / HubBody). */}
      <main className="flex-1 animate-fade-in">
        <Outlet />
      </main>
    </div>
  );
}
