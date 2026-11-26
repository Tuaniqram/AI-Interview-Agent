import { Outlet, useLocation } from 'react-router-dom';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Store, Shield } from 'lucide-react';
import { Sidebar, visibleItems } from './Sidebar';
import { TopBar } from './TopBar';
import { CommandPalette } from './CommandPalette';
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

const COLLAPSED_KEY = 'sidebar-collapsed';

function isTyping(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null;
  return !!el && (el.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName));
}

/**
 * The app frame: the sidebar sits on the page tone and the content on a bordered panel set into it,
 * so navigation and work never compete for attention.
 */
export function DashboardShell({
  navItems, orgNavItems = [], brand, showMarketplace = false, showAdmin = false,
  useOrgSelector, activeRole = null, user, orgs, activeOrg, onSwitchOrg, onLogout,
}: DashboardShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(COLLAPSED_KEY) === '1');
  const { pathname } = useLocation();

  const toggleCollapsed = useCallback(() => {
    setCollapsed(c => { localStorage.setItem(COLLAPSED_KEY, c ? '0' : '1'); return !c; });
  }, []);

  const pages = useMemo(() => {
    const list = [...visibleItems(navItems, activeRole), ...visibleItems(orgNavItems, activeRole)];
    if (showMarketplace) list.push({ to: '/opportunity-hub', label: 'Opportunity Hub', icon: Store });
    if (showAdmin) list.push({ to: '/admin', label: 'Admin', icon: Shield });
    return list;
  }, [navItems, orgNavItems, activeRole, showMarketplace, showAdmin]);

  const labels = useMemo(() => Object.fromEntries(pages.map(p => [p.to, p.label])), [pages]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); setPaletteOpen(o => !o); }
      else if (e.key === '[' && !e.ctrlKey && !e.metaKey && !isTyping(e.target)) toggleCollapsed();
    };
    const onOpen = () => setPaletteOpen(true);
    window.addEventListener('keydown', onKey);
    window.addEventListener('open-search', onOpen);
    return () => { window.removeEventListener('keydown', onKey); window.removeEventListener('open-search', onOpen); };
  }, [toggleCollapsed]);

  // A new page starts at the top.
  useEffect(() => { document.getElementById('app-content')?.scrollTo(0, 0); }, [pathname]);

  return (
    <div className="flex h-screen bg-page">
      <Sidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        collapsed={collapsed}
        onToggleCollapsed={toggleCollapsed}
        onOpenSearch={() => setPaletteOpen(true)}
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
      <div className="flex-1 min-w-0 flex lg:py-2 lg:pr-2">
        <div className="flex-1 min-w-0 flex flex-col bg-section lg:rounded-xl lg:border lg:border-border overflow-hidden">
          <TopBar
            onMenuToggle={() => setSidebarOpen(o => !o)}
            onOpenSearch={() => setPaletteOpen(true)}
            labels={labels}
          />
          <main id="app-content" className="flex-1 overflow-y-auto">
            <div key={pathname} className="mx-auto w-full max-w-[1240px] px-4 sm:px-8 py-6 sm:py-8 animate-fade-in">
              <Outlet />
            </div>
          </main>
        </div>
      </div>
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} pages={pages} onLogout={onLogout} />
    </div>
  );
}
