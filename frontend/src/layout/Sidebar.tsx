import { NavLink, useNavigate } from 'react-router-dom';
import { Store, Shield, X, Command as CommandIcon, Search as SearchIcon, Monitor as MonitorIcon } from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { Select } from '../components/shared/Select';
import type { OrgRole } from '../types/org';

export interface NavItem {
  to: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  end?: boolean;
  roles?: OrgRole[];
  shortcut?: string;
  description?: string;
}

interface SidebarProps {
  open: boolean;
  onClose: () => void;
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

export function Sidebar({
  open, onClose, navItems, orgNavItems = [], brand = 'AI Interview',
  showMarketplace = true, showAdmin = false, useOrgSelector = false,
  activeRole = null as OrgRole | null, user = null,
  orgs = [], activeOrg = null, onSwitchOrg, onLogout,
}: SidebarProps) {
  const navigate = useNavigate();
  const [showShortcuts, setShowShortcuts] = useState(false);

  const filteredNavItems = (() => {
    return navItems.filter((item: NavItem) => {
      if (!item.roles) return true;
      if (!activeRole) return false;
      return item.roles.includes(activeRole);
    });
  })();

  const filteredOrgNavItems = (() => {
    return orgNavItems.filter((item: NavItem) => {
      if (!item.roles) return true;
      if (!activeRole) return false;
      return item.roles.includes(activeRole);
    });
  })();

  const showOrgSection = filteredOrgNavItems.length > 0;

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl+K or Cmd+K for global search
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        window.dispatchEvent(new CustomEvent('open-search'));
      }
      // Ctrl+/ or Cmd+/ for shortcuts
      if ((e.ctrlKey || e.metaKey) && e.key === '/') {
        e.preventDefault();
        setShowShortcuts(true);
      }
      // Escape to close sidebar (mobile)
      if (e.key === 'Escape' && open) {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [open, onClose, setShowShortcuts]);

  const getIcon = (icon: React.ComponentType<{ className?: string }>, isActive: boolean) => {
    return React.createElement(icon, { 
      className: isActive ? 'text-action-primary' : '' 
    });
  };

  return (
    <>
      {open && (
        <div 
          className="fixed inset-0 bg-overlay/50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      <aside 
        className={`h-screen bg-section flex flex-col w-52 fixed lg:static z-50 lg:z-auto
          ${open ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        `}
      >
        <div 
          className="h-14 flex items-center gap-2 px-4 shrink-0"
          onClick={onClose}
        >
          <img src="/favicon.svg" className="w-6 h-6 shrink-0" alt="" />
          <span className="text-sm font-semibold text-primary truncate">{brand}</span>
        </div>

        {useOrgSelector && activeOrg && (
          <div className="px-3 py-1.5 shrink-0">
            <Select
              value={String(activeOrg.id)}
              onChange={(v) => { onSwitchOrg?.(v); navigate('/dashboard'); }}
              options={orgs.length > 0
                ? orgs.map(o => ({ value: String(o.id), label: o.name }))
                : [{ value: String(activeOrg.id), label: activeOrg.name }]
              }
            />
          </div>
        )}

        <nav className="flex-1 py-2 space-y-0.5 px-2 overflow-y-auto">
          {filteredNavItems.map((item: NavItem) => {
            const NavLinkButton = () => (
              <div className="flex items-center gap-3 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors group relative overflow-hidden bg-action-primary/10 text-action-primary">
                <span className="absolute inset-0 bg-gradient-to-r from-transparent via-action-primary/5 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-500" />
                {getIcon(item.icon, true)}
                <span className="relative z-10 flex-1 min-w-0">{item.label}</span>
              </div>
            );

            const NavLinkButtonDefault = () => (
              <div className="flex items-center gap-3 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors group relative overflow-hidden text-secondary hover:bg-hover hover:text-primary">
                <span className="absolute inset-0 bg-gradient-to-r from-transparent via-action-primary/5 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-500" />
                {getIcon(item.icon, false)}
                <span className="relative z-10 flex-1 min-w-0">{item.label}</span>
                {item.shortcut && (
                  <kbd className="hidden sm:inline-flex absolute right-3 text-[10px] font-medium text-muted bg-bg-input px-1.5 py-0.5 rounded border border-border">
                    {item.shortcut}
                  </kbd>
                )}
              </div>
            );

            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end ?? item.to === '/'}
                onClick={onClose}
              >
                {({ isActive }) => isActive ? <NavLinkButton /> : <NavLinkButtonDefault />}
              </NavLink>
            );
          })}

          {showOrgSection && (
            <div className="pt-3 mt-3">
              <div className="h-px bg-border mb-2" />
              <p className="px-3 text-[10px] font-semibold text-muted uppercase tracking-wider mb-1.5">
                Organization
              </p>
              {filteredOrgNavItems.map((item: NavItem) => {
                const NavLinkButton = () => (
                  <div className="flex items-center gap-3 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors group relative overflow-hidden bg-action-primary/10 text-action-primary">
                    <span className="absolute inset-0 bg-gradient-to-r from-transparent via-action-primary/5 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-500" />
                    {getIcon(item.icon, true)}
                    <span className="relative z-10 flex-1 min-w-0">{item.label}</span>
                  </div>
                );

                const NavLinkButtonDefault = () => (
                  <div className="flex items-center gap-3 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors group relative overflow-hidden text-secondary hover:bg-hover hover:text-primary">
                    <span className="absolute inset-0 bg-gradient-to-r from-transparent via-action-primary/5 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-500" />
                    {getIcon(item.icon, false)}
                    <span className="relative z-10 flex-1 min-w-0">{item.label}</span>
                  </div>
                );

                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    onClick={onClose}
                  >
                    {({ isActive }) => isActive ? <NavLinkButton /> : <NavLinkButtonDefault />}
                  </NavLink>
                );
              })}
            </div>
          )}

          {showMarketplace && (
            <>
              <div className="h-px bg-border my-3" />
              <NavLink
                to="/opportunity-hub"
                onClick={onClose}
                className={({ isActive }) => (
                  `flex items-center gap-3 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors group relative overflow-hidden ${
                    isActive
                      ? 'bg-action-primary/10 text-action-primary'
                      : 'text-secondary hover:bg-hover group hover:text-primary'
                  }`
                )}
              >
                <span className="absolute inset-0 bg-gradient-to-r from-transparent via-action-primary/5 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-500" />
                <Store className="shrink-0" />
                <span className="relative z-10 flex-1">Opportunity Hub</span>
              </NavLink>
            </>
          )}

          {showAdmin && (
            <NavLink
              to="/admin"
              onClick={onClose}
              className={({ isActive }) => (
                `flex items-center gap-3 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors group relative overflow-hidden ${isActive ? 'bg-action-primary/10 text-action-primary' : 'text-secondary hover:bg-hover group hover:text-primary'}`
              )}
            >
              <span className="absolute inset-0 bg-gradient-to-r from-transparent via-action-primary/5 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-500" />
              <Shield className="shrink-0" />
              <span className="relative z-10 flex-1">Admin</span>
            </NavLink>
          )}
        </nav>

        <div className="p-3 shrink-0">
          {/* Keyboard shortcuts hint */}
          <div
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-muted bg-bg-input hover:bg-hover cursor-pointer mb-2 border border-border hover:border-action-primary transition-colors"
            onClick={() => setShowShortcuts(true)}
          >
            <kbd className="bg-bg-elevated px-1.5 py-0.5 rounded text-[10px] font-medium">Ctrl+</kbd>
            <span className="text-[10px]">Shortcuts</span>
          </div>

          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-action-primary/10 text-action-primary flex items-center justify-center text-xs font-semibold shrink-0">
              {user?.name?.charAt(0)?.toUpperCase() || '?'}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-medium text-primary truncate">{user?.name || 'User'}</p>
              <p className="text-[10px] text-muted truncate">{user?.email || ''}</p>
            </div>
            {onLogout && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onLogout();
                }}
                className="text-xs text-muted hover:text-error transition-colors ml-auto p-1 rounded hover:bg-error/10"
                title="Sign Out (Ctrl+Shift+Q)"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </aside>

      {/* Global Shortcuts Modal */}
      {showShortcuts && (
        <div 
          className="fixed inset-0 z-[100] flex items-center justify-center"
          onClick={() => setShowShortcuts(false)}
        >
          <div 
            className="fixed inset-0 bg-overlay/50 backdrop-blur-sm"
            onClick={() => setShowShortcuts(false)}
          />
          <div className="relative bg-section rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden border border-border">
            <div className="p-5 border-b border-border">
              <h3 className="text-lg font-semibold text-primary">
                <div className="flex items-center gap-2">
                  <CommandIcon className="w-5 h-5 text-action-primary" />
                  Keyboard Shortcuts
                </div>
                <p className="text-sm text-muted mt-1">Ctrl+ / Close modal</p>
              </h3>
            </div>
            
            <div className="divide-y divide-border">
              <div className="flex items-center justify-between p-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-action-primary/10 flex items-center justify-center">
                    <SearchIcon className="w-5 h-5 text-action-primary" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-primary">Search</p>
                    <p className="text-xs text-muted">Quick find anything</p>
                  </div>
                </div>
                <kbd className="bg-bg-input px-2.5 py-1 rounded border border-border text-xs font-medium text-muted">
                  ⌘ K
                </kbd>
              </div>

              <div className="flex items-center justify-between p-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-action-primary/10 flex items-center justify-center">
                    <CommandIcon className="w-5 h-5 text-action-primary" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-primary">Toggle Shortcuts</p>
                    <p className="text-xs text-muted">Show this menu</p>
                  </div>
                </div>
                <kbd className="bg-bg-input px-2.5 py-1 rounded border border-border text-xs font-medium text-muted">
                  ⎋ /
                </kbd>
              </div>

              <div className="flex items-center justify-between p-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-action-primary/10 flex items-center justify-center">
                    <X className="w-5 h-5 text-action-primary" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-primary">Close Sidebar</p>
                    <p className="text-xs text-muted">Hide navigation</p>
                  </div>
                </div>
                <kbd className="bg-bg-input px-2.5 py-1 rounded border border-border text-xs font-medium text-muted">
                  Esc
                </kbd>
              </div>

              <div className="flex items-center justify-between p-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-action-primary/10 flex items-center justify-center">
                    <MonitorIcon className="w-5 h-5 text-action-primary" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-primary">Log Out</p>
                    <p className="text-xs text-muted">Sign out of your account</p>
                  </div>
                </div>
                <kbd className="bg-bg-input px-2.5 py-1 rounded border border-border text-xs font-medium text-muted">
                  ⌘⇧Q
                </kbd>
              </div>
            </div>

            <div className="p-4 bg-bg-input border-t border-border flex justify-end">
              <button
                onClick={() => setShowShortcuts(false)}
                className="px-4 py-2 text-sm font-medium text-primary bg-bg-elevated rounded-lg hover:bg-hover transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}