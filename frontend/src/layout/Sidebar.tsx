import { NavLink, useNavigate } from 'react-router-dom';
import { ChevronLeft, ChevronRight, Store, Shield } from 'lucide-react';
import { useState, useMemo } from 'react';
import type { OrgRole } from '../types/org';

export interface NavItem {
  to: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  end?: boolean;
  roles?: OrgRole[];
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
  activeRole = null, user = null,
  orgs = [], activeOrg = null, onSwitchOrg, onLogout,
}: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();

  const filteredNavItems = useMemo(() => {
    return navItems.filter(item => {
      if (!item.roles) return true;
      if (!activeRole) return false;
      return item.roles.includes(activeRole);
    });
  }, [navItems, activeRole]);

  const filteredOrgNavItems = useMemo(() => {
    return orgNavItems.filter(item => {
      if (!item.roles) return true;
      if (!activeRole) return false;
      return item.roles.includes(activeRole);
    });
  }, [orgNavItems, activeRole]);

  const showOrgSection = filteredOrgNavItems.length > 0;

  return (
    <>
      {open && (
        <div className="fixed inset-0 bg-overlay/50 z-40 lg:hidden" onClick={onClose} />
      )}

      <aside className={`h-screen bg-section shadow-sm flex flex-col transition-all duration-200
        ${collapsed ? 'w-14' : 'w-56'}
        fixed lg:static z-50 lg:z-auto
        ${open ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        <div className="h-14 flex items-center px-4 border-b border-hover">
          {!collapsed && (
            <span className="text-sm font-semibold text-primary truncate">{brand}</span>
          )}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className={`p-1 rounded-lg text-muted hover:text-secondary hover:bg-hover ${collapsed ? 'mx-auto' : 'ms-auto'}`}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        {!collapsed && useOrgSelector && activeOrg && (
          <div className="px-3 py-2 border-b border-hover">
            <select
              value={activeOrg.id}
              onChange={(e) => {
                onSwitchOrg?.(e.target.value);
                navigate('/dashboard');
              }}
              className="w-full text-xs bg-transparent text-secondary border border-hover rounded px-2 py-1"
            >
              {orgs.map((o) => (
                <option key={o.id} value={o.id}>{o.name}</option>
              ))}
              {orgs.length === 0 && activeOrg && (
                <option value={activeOrg.id}>{activeOrg.name}</option>
              )}
            </select>
          </div>
        )}

        <nav className="flex-1 py-3 space-y-1 px-2 overflow-y-auto">
          {filteredNavItems.map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end ?? item.to === '/'}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-action-primary/15 text-action-primary'
                    : 'text-secondary hover:bg-hover hover:text-primary'
                } ${collapsed ? 'justify-center px-2' : ''}`
              }
            >
              <item.icon className="w-4 h-4 shrink-0" />
              {!collapsed && <span>{item.label}</span>}
            </NavLink>
          ))}

          {!collapsed && showOrgSection && (
            <div className="pt-3 mt-3">
              <div className="h-px bg-hover mb-3" />
              <p className="px-3 text-xs font-medium text-muted uppercase tracking-wider mb-2">
                Organization
              </p>
              {filteredOrgNavItems.map(item => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={onClose}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-action-primary/15 text-action-primary'
                        : 'text-secondary hover:bg-hover hover:text-primary'
                    }`
                  }
                >
                  <item.icon className="w-4 h-4 shrink-0" />
                  <span>{item.label}</span>
                </NavLink>
              ))}
            </div>
          )}

          {!collapsed && showMarketplace && (
            <>
              <div className="h-px bg-hover my-3" />
              <NavLink
                to="/opportunity-hub"
                onClick={onClose}
                className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-secondary hover:bg-hover hover:text-primary"
              >
                <Store className="w-4 h-4 shrink-0" />
                <span>Opportunity Hub</span>
              </NavLink>
            </>
          )}

          {!collapsed && showAdmin && (
            <NavLink
              to="/admin"
              onClick={onClose}
              className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-secondary hover:bg-hover hover:text-primary"
            >
              <Shield className="w-4 h-4 shrink-0" />
              <span>Admin</span>
            </NavLink>
          )}


        </nav>

        <div className="p-3 border-t border-hover">
          <div className={`flex items-center gap-2 ${collapsed ? 'justify-center' : ''}`}>
            <div className="w-6 h-6 rounded-full bg-action-primary flex items-center justify-center text-inverse text-xs font-medium shrink-0">
              {user?.name?.charAt(0)?.toUpperCase() || '?'}
            </div>
            {!collapsed && (
              <div className="min-w-0 flex-1">
                <p className="text-xs text-primary truncate">{user?.name || 'User'}</p>
                <p className="text-xs text-muted truncate">{user?.email || ''}</p>
              </div>
            )}
            {!collapsed && onLogout && (
              <button
                onClick={onLogout}
                className="text-xs text-red-500 hover:text-red-600 ml-1 shrink-0"
              >
                Sign Out
              </button>
            )}
          </div>
        </div>
      </aside>
    </>
  );
}
