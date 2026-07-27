import { NavLink } from 'react-router-dom';
import { Store, Shield } from 'lucide-react';
import { useMemo } from 'react';
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

      <aside className={`h-screen bg-section flex flex-col w-52 fixed lg:static z-50 lg:z-auto
        ${open ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        <div className="h-14 flex items-center gap-2 px-4 shrink-0">
          <img src="/favicon.svg" className="w-6 h-6 shrink-0" alt="" />
          <span className="text-sm font-semibold text-primary truncate">{brand}</span>
        </div>

        {useOrgSelector && activeOrg && (
          <div className="px-3 py-1.5 shrink-0">
            <select
              value={activeOrg.id}
              onChange={(e) => {
                onSwitchOrg?.(e.target.value);
                navigate('/dashboard');
              }}
              className="w-full text-xs bg-input text-secondary border border-border rounded px-2 py-1.5"
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

        <nav className="flex-1 py-2 space-y-0.5 px-2 overflow-y-auto">
          {filteredNavItems.map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end ?? item.to === '/'}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-action-primary/10 text-action-primary'
                    : 'text-secondary hover:bg-hover hover:text-primary'
                }`
              }
            >
              <item.icon className="w-4 h-4 shrink-0" />
              <span>{item.label}</span>
            </NavLink>
          ))}

          {showOrgSection && (
            <div className="pt-3 mt-3">
              <div className="h-px bg-border mb-2" />
              <p className="px-3 text-[10px] font-semibold text-muted uppercase tracking-wider mb-1.5">
                Organization
              </p>
              {filteredOrgNavItems.map(item => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={onClose}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-action-primary/10 text-action-primary'
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

          {showMarketplace && (
            <>
              <div className="h-px bg-border my-3" />
              <NavLink
                to="/opportunity-hub"
                onClick={onClose}
                className="flex items-center gap-3 px-3 py-1.5 rounded-lg text-sm font-medium text-secondary hover:bg-hover hover:text-primary transition-colors"
              >
                <Store className="w-4 h-4 shrink-0" />
                <span>Opportunity Hub</span>
              </NavLink>
            </>
          )}

          {showAdmin && (
            <NavLink
              to="/admin"
              onClick={onClose}
              className="flex items-center gap-3 px-3 py-1.5 rounded-lg text-sm font-medium text-secondary hover:bg-hover hover:text-primary transition-colors"
            >
              <Shield className="w-4 h-4 shrink-0" />
              <span>Admin</span>
            </NavLink>
          )}
        </nav>

        <div className="p-3 shrink-0">
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
                onClick={onLogout}
                className="text-xs text-muted hover:text-error transition-colors ml-auto"
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
