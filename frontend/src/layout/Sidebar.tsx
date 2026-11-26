import { NavLink, useNavigate } from 'react-router-dom';
import {
  Store, Shield, Search, ChevronsUpDown, Check, LogOut, Keyboard, PanelLeftClose, PanelLeftOpen,
  Sun, Moon, Monitor, X,
} from 'lucide-react';
import React, { useEffect, useRef, useState } from 'react';
import { useTheme, type ThemeMode } from '../contexts/ThemeContext';
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
  collapsed: boolean;
  onToggleCollapsed: () => void;
  onOpenSearch: () => void;
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

/** Nav items the current role may see. Items without `roles` are for everyone. */
export function visibleItems(items: NavItem[], role: OrgRole | null): NavItem[] {
  return items.filter(item => !item.roles || (role != null && item.roles.includes(role)));
}

function initials(name?: string): string {
  if (!name) return '?';
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] ?? '') + (parts.length > 1 ? parts[parts.length - 1][0] : '')).toUpperCase() || '?';
}

/** Closes a popover on an outside click or Escape. */
function useDismiss(open: boolean, close: () => void) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) close(); };
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') close(); };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => { document.removeEventListener('mousedown', onDown); document.removeEventListener('keydown', onKey); };
  }, [open, close]);
  return ref;
}

function NavRow({ item, collapsed, onNavigate }: { item: NavItem; collapsed: boolean; onNavigate: () => void }) {
  const Icon = item.icon;
  return (
    <NavLink
      to={item.to}
      end={item.end ?? item.to === '/'}
      onClick={onNavigate}
      title={collapsed ? item.label : undefined}
      className={({ isActive }) =>
        `group flex items-center gap-2.5 h-8 rounded-md text-[13px] font-medium transition-colors border
        ${collapsed ? 'justify-center px-0' : 'px-2.5'}
        ${isActive
          ? 'bg-section border-border text-primary shadow-sm'
          : 'border-transparent text-secondary hover:bg-hover hover:text-primary'}`
      }
    >
      {({ isActive }) => (
        <>
          <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-action-primary' : 'text-tertiary group-hover:text-secondary'}`} />
          {!collapsed && <span className="truncate">{item.label}</span>}
        </>
      )}
    </NavLink>
  );
}

function Group({ label, collapsed, children }: { label?: string; collapsed: boolean; children: React.ReactNode }) {
  return (
    <div className="space-y-px">
      {label && (collapsed
        ? <div className="mx-auto my-2 h-px w-5 bg-border" />
        : <p className="px-2.5 pt-4 pb-1.5 text-xs font-medium text-tertiary">{label}</p>)}
      {children}
    </div>
  );
}

const THEME_OPTIONS: { mode: ThemeMode; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { mode: 'light', label: 'Light', icon: Sun },
  { mode: 'dark', label: 'Dark', icon: Moon },
  { mode: 'system', label: 'System', icon: Monitor },
];

export function Sidebar({
  open, onClose, collapsed, onToggleCollapsed, onOpenSearch,
  navItems, orgNavItems = [], brand = 'AI Interview',
  showMarketplace = true, showAdmin = false, useOrgSelector = false,
  activeRole = null, user = null, orgs = [], activeOrg = null, onSwitchOrg, onLogout,
}: SidebarProps) {
  const navigate = useNavigate();
  const { mode, setMode } = useTheme();
  const [showShortcuts, setShowShortcuts] = useState(false);
  const [orgMenu, setOrgMenu] = useState(false);
  const [userMenu, setUserMenu] = useState(false);
  const orgRef = useDismiss(orgMenu, () => setOrgMenu(false));
  const userRef = useDismiss(userMenu, () => setUserMenu(false));

  // On a phone the drawer always shows labels.
  const rail = collapsed && !open;
  const main = visibleItems(navItems, activeRole);
  const hiring = visibleItems(orgNavItems, activeRole);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === '/') { e.preventDefault(); setShowShortcuts(s => !s); }
      if (e.key === 'Escape') { if (open) onClose(); setShowShortcuts(false); }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  const orgList = orgs.length > 0 ? orgs : activeOrg ? [activeOrg] : [];

  return (
    <>
      {open && <div className="fixed inset-0 bg-overlay z-40 lg:hidden" onClick={onClose} />}

      <aside
        className={`h-screen shrink-0 bg-page flex flex-col fixed lg:static z-50 lg:z-auto transition-[width,transform] duration-200
          ${rail ? 'lg:w-[60px]' : 'lg:w-60'} w-64
          ${open ? 'translate-x-0 shadow-lg lg:shadow-none' : '-translate-x-full lg:translate-x-0'}`}
      >
        {/* Workspace */}
        <div className={`pt-3 pb-2 ${rail ? 'px-2' : 'px-3'}`}>
          {useOrgSelector && activeOrg ? (
            <div ref={orgRef} className="relative">
              <button
                onClick={() => setOrgMenu(o => !o)}
                title={rail ? activeOrg.name : undefined}
                aria-haspopup="menu"
                aria-expanded={orgMenu}
                className={`w-full flex items-center gap-2.5 h-10 rounded-lg hover:bg-hover transition-colors ${rail ? 'justify-center' : 'px-2'}`}
              >
                <span className="w-7 h-7 rounded-md bg-action-primary text-action-primary-text flex items-center justify-center text-xs font-semibold shrink-0">
                  {initials(activeOrg.name)}
                </span>
                {!rail && (
                  <>
                    <span className="flex-1 min-w-0 text-left">
                      <span className="block text-[13px] font-semibold text-primary truncate">{activeOrg.name}</span>
                      {activeRole && <span className="block text-[11px] text-tertiary capitalize leading-tight">{activeRole}</span>}
                    </span>
                    <ChevronsUpDown className="w-3.5 h-3.5 text-tertiary shrink-0" />
                  </>
                )}
              </button>
              {orgMenu && (
                <div role="menu" className="absolute left-0 top-11 z-50 w-full min-w-[13rem] rounded-lg border border-border bg-elevated shadow-lg p-1">
                  <p className="px-2 pt-1.5 pb-1 text-xs text-tertiary">Organizations</p>
                  {orgList.map(o => (
                    <button
                      key={o.id}
                      role="menuitem"
                      onClick={() => { setOrgMenu(false); onSwitchOrg?.(String(o.id)); navigate('/dashboard'); onClose(); }}
                      className="w-full flex items-center gap-2.5 px-2 h-8 rounded-md text-[13px] text-primary hover:bg-hover"
                    >
                      <span className="w-5 h-5 rounded bg-hover text-secondary flex items-center justify-center text-[10px] font-semibold">{initials(o.name)}</span>
                      <span className="flex-1 truncate text-left">{o.name}</span>
                      {String(o.id) === String(activeOrg.id) && <Check className="w-3.5 h-3.5 text-action-primary" />}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className={`flex items-center gap-2.5 h-10 ${rail ? 'justify-center' : 'px-2'}`}>
              <img src="/favicon.svg" className="w-7 h-7 shrink-0" alt="" />
              {!rail && <span className="text-[13px] font-semibold text-primary truncate">{brand}</span>}
            </div>
          )}
        </div>

        {/* Search */}
        <div className={rail ? 'px-2 pb-1' : 'px-3 pb-1'}>
          <button
            onClick={() => { onClose(); onOpenSearch(); }}
            title={rail ? 'Search (Ctrl K)' : undefined}
            className={`w-full flex items-center gap-2 h-8 rounded-md border border-border bg-section text-[13px] text-tertiary hover:border-border-strong hover:text-secondary transition-colors ${rail ? 'justify-center' : 'px-2.5'}`}
          >
            <Search className="w-3.5 h-3.5 shrink-0" />
            {!rail && (
              <>
                <span className="flex-1 text-left">Search</span>
                <kbd className="text-[11px] font-sans text-tertiary">Ctrl K</kbd>
              </>
            )}
          </button>
        </div>

        <nav className={`flex-1 overflow-y-auto pb-3 ${rail ? 'px-2' : 'px-3'}`} aria-label="Main">
          <Group collapsed={rail}>
            <div className="pt-2" />
            {main.map(item => <NavRow key={item.to} item={item} collapsed={rail} onNavigate={onClose} />)}
          </Group>

          {hiring.length > 0 && (
            <Group label="Hiring" collapsed={rail}>
              {hiring.map(item => <NavRow key={item.to} item={item} collapsed={rail} onNavigate={onClose} />)}
            </Group>
          )}

          {(showMarketplace || showAdmin) && (
            <Group label="More" collapsed={rail}>
              {showMarketplace && (
                <NavRow item={{ to: '/opportunity-hub', label: 'Opportunity Hub', icon: Store }} collapsed={rail} onNavigate={onClose} />
              )}
              {showAdmin && (
                <NavRow item={{ to: '/admin', label: 'Admin', icon: Shield }} collapsed={rail} onNavigate={onClose} />
              )}
            </Group>
          )}
        </nav>

        {/* Account */}
        <div className={`pb-3 pt-2 border-t border-border ${rail ? 'px-2' : 'px-3'}`}>
          <div ref={userRef} className="relative">
            <button
              onClick={() => setUserMenu(m => !m)}
              aria-haspopup="menu"
              aria-expanded={userMenu}
              title={rail ? user?.name || 'Account' : undefined}
              className={`w-full flex items-center gap-2.5 h-10 rounded-lg hover:bg-hover transition-colors ${rail ? 'justify-center' : 'px-2'}`}
            >
              <span className="w-7 h-7 rounded-full bg-hover border border-border text-secondary flex items-center justify-center text-[11px] font-semibold shrink-0">
                {initials(user?.name)}
              </span>
              {!rail && (
                <span className="flex-1 min-w-0 text-left">
                  <span className="block text-[13px] font-medium text-primary truncate">{user?.name || 'Account'}</span>
                  <span className="block text-[11px] text-tertiary truncate leading-tight">{user?.email || ''}</span>
                </span>
              )}
            </button>

            {userMenu && (
              <div role="menu" className="absolute bottom-12 left-0 z-50 w-full min-w-[13rem] rounded-lg border border-border bg-elevated shadow-lg p-1">
                <div className="px-2 py-1.5">
                  <p className="text-xs text-tertiary mb-1.5">Theme</p>
                  <div className="grid grid-cols-3 gap-0.5 p-0.5 rounded-md bg-hover">
                    {THEME_OPTIONS.map(({ mode: m, label, icon: Icon }) => (
                      <button
                        key={m}
                        onClick={() => setMode(m)}
                        aria-pressed={mode === m}
                        className={`flex items-center justify-center gap-1 h-7 rounded text-xs transition-colors
                          ${mode === m ? 'bg-section text-primary shadow-sm' : 'text-secondary hover:text-primary'}`}
                      >
                        <Icon className="w-3.5 h-3.5" />{label}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="h-px bg-border my-1" />
                <button role="menuitem" onClick={() => { setUserMenu(false); setShowShortcuts(true); }}
                  className="w-full flex items-center gap-2.5 px-2 h-8 rounded-md text-[13px] text-primary hover:bg-hover">
                  <Keyboard className="w-4 h-4 text-tertiary" /> <span className="flex-1 text-left">Keyboard shortcuts</span>
                  <kbd className="text-[11px] font-sans text-tertiary">Ctrl /</kbd>
                </button>
                <button role="menuitem" onClick={() => { setUserMenu(false); onToggleCollapsed(); }}
                  className="hidden lg:flex w-full items-center gap-2.5 px-2 h-8 rounded-md text-[13px] text-primary hover:bg-hover">
                  {collapsed ? <PanelLeftOpen className="w-4 h-4 text-tertiary" /> : <PanelLeftClose className="w-4 h-4 text-tertiary" />}
                  <span className="flex-1 text-left">{collapsed ? 'Expand sidebar' : 'Collapse sidebar'}</span>
                  <kbd className="text-[11px] font-sans text-tertiary">[</kbd>
                </button>
                {onLogout && (
                  <>
                    <div className="h-px bg-border my-1" />
                    <button role="menuitem" onClick={() => { setUserMenu(false); onLogout(); }}
                      className="w-full flex items-center gap-2.5 px-2 h-8 rounded-md text-[13px] text-primary hover:bg-hover">
                      <LogOut className="w-4 h-4 text-tertiary" /> Sign out
                    </button>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      </aside>

      {showShortcuts && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="shortcuts-title">
          <div className="fixed inset-0 bg-overlay" onClick={() => setShowShortcuts(false)} />
          <div className="relative w-full max-w-sm rounded-xl border border-border bg-elevated shadow-lg">
            <div className="flex items-center justify-between px-4 h-12 border-b border-border">
              <h3 id="shortcuts-title" className="text-sm font-semibold text-primary">Keyboard shortcuts</h3>
              <button onClick={() => setShowShortcuts(false)} className="p-1 rounded-md text-tertiary hover:bg-hover hover:text-primary" aria-label="Close">
                <X className="w-4 h-4" />
              </button>
            </div>
            <dl className="p-2">
              {[
                ['Search and jump to a page', 'Ctrl K'],
                ['Collapse or expand the sidebar', '['],
                ['Show this list', 'Ctrl /'],
                ['Close a menu or dialog', 'Esc'],
              ].map(([what, key]) => (
                <div key={what} className="flex items-center justify-between px-2 h-9 text-[13px]">
                  <dt className="text-secondary">{what}</dt>
                  <dd><kbd className="px-1.5 py-0.5 rounded border border-border bg-section text-xs font-sans text-primary">{key}</kbd></dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
      )}
    </>
  );
}
