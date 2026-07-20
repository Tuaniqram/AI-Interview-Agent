import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, Building2, ListChecks, FlaskConical, Settings, ChevronLeft, ChevronRight, PlusCircle
} from 'lucide-react';
import { useState } from 'react';

const navItems = [
  { to: '/',          icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/companies', icon: Building2,       label: 'Companies' },
  { to: '/sessions',  icon: ListChecks,       label: 'Sessions' },
  { to: '/avatar-lab',icon: FlaskConical,     label: 'Avatar Lab' },
  { to: '/settings',  icon: Settings,         label: 'Settings' },
];

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside className={`h-screen bg-section border-r border-default flex flex-col transition-all duration-200 ${collapsed ? 'w-14' : 'w-56'}`}>
      <div className="h-14 flex items-center px-4 border-b border-default">
        {!collapsed && (
          <span className="text-sm font-semibold text-primary truncate">AI Interview</span>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className={`p-1 rounded-lg text-muted hover:text-secondary hover:bg-hover ${collapsed ? 'mx-auto' : 'ms-auto'}`}
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      <nav className="flex-1 py-3 space-y-1 px-2">
        {navItems.map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
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
        <div className="pt-3 border-t border-default mt-3">
          <NavLink
            to="/new-interview"
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-action-primary/15 text-action-primary'
                  : 'text-action-primary hover:bg-action-primary/15'
              } ${collapsed ? 'justify-center px-2' : ''}`
            }
          >
            <PlusCircle className="w-4 h-4 shrink-0" />
            {!collapsed && <span>New Interview</span>}
          </NavLink>
        </div>
      </nav>

      <div className="p-3 border-t border-default">
        <div className={`flex items-center gap-2 ${collapsed ? 'justify-center' : ''}`}>
          <div className="w-6 h-6 rounded-full bg-action-primary flex items-center justify-center text-inverse text-xs font-medium shrink-0">
            A
          </div>
          {!collapsed && <span className="text-xs text-muted truncate">v2.0</span>}
        </div>
      </div>
    </aside>
  );
}
