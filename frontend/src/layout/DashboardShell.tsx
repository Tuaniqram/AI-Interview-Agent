import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { useState } from 'react';
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
          <div className="animate-fade-in">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
