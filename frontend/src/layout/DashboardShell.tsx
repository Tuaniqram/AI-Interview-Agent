import { Outlet, useLocation, Link } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { useState, Fragment } from 'react';
import { ChevronRight, Home } from 'lucide-react';
import type { NavItem } from './Sidebar';
import type { OrgRole } from '../types/org';

interface DashboardShellProps {
  navItems: NavItem[];
  orgNavItems?: NavItem[];
  brand?: string;
  showMarketplace?: boolean;
  showAdmin?: boolean;
  useOrgSelector?: boolean;
  activeRole?: OrgRole | null;
  user?: { name?: string; email?: string } | null;
  orgs?: { id: string; name: string }[];
  activeOrg?: { id: string; name: string } | null;
  onSwitchOrg?: (orgId: string) => void;
  onLogout?: () => void;
}

export function DashboardShell({
  navItems, orgNavItems, brand, showMarketplace, showAdmin,
  useOrgSelector, activeRole, user, orgs, activeOrg, onSwitchOrg, onLogout,
}: DashboardShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();
  const segments = location.pathname.split('/').filter(Boolean);

  return (
    <div className="flex h-screen bg-page">
      <Sidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        navItems={navItems}
        orgNavItems={orgNavItems}
        brand={brand}
        showMarketplace={showMarketplace}
        showAdmin={showAdmin}
        useOrgSelector={useOrgSelector}
        activeRole={activeRole}
        user={user}
        orgs={orgs}
        activeOrg={activeOrg}
        onSwitchOrg={onSwitchOrg}
        onLogout={onLogout}
      />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar onMenuToggle={() => setSidebarOpen(prev => !prev)} />
        <main className="flex-1 overflow-y-auto p-6">
          <nav className="flex items-center gap-1.5 text-xs text-muted mb-4 animate-fade-in overflow-x-auto">
            <Link to="/org" className="hover:text-primary transition-colors shrink-0">
              <Home className="w-3.5 h-3.5" />
            </Link>
            {segments.map((seg, i) => (
              <Fragment key={i}>
                <ChevronRight className="w-3 h-3 shrink-0" />
                <Link
                  to={'/' + segments.slice(0, i + 1).join('/')}
                  className="hover:text-primary transition-colors truncate whitespace-nowrap capitalize"
                >
                  {seg.replace(/-/g, ' ')}
                </Link>
              </Fragment>
            ))}
          </nav>
          <div className="animate-fade-in">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
