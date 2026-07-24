import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useOrg } from '../contexts/OrgContext';
import { DashboardShell } from './DashboardShell';
import {
  LayoutDashboard, Building2, ListChecks, BarChart3, FlaskConical, Settings,
  Users,
} from 'lucide-react';
import type { OrgRole } from '../types/org';

const navItems = [
  { to: '/org',       icon: LayoutDashboard, label: 'Dashboard', end: true },
  { to: '/departments',icon: Building2,       label: 'Departments', roles: ['owner'] as OrgRole[] },
  { to: '/sessions',  icon: ListChecks,      label: 'Sessions' },
  { to: '/analytics', icon: BarChart3,       label: 'Analytics', roles: ['owner'] as OrgRole[] },
  { to: '/avatar-lab',icon: FlaskConical,    label: 'Avatar Lab', roles: ['owner'] as OrgRole[] },
  { to: '/settings',  icon: Settings,        label: 'Settings', roles: ['owner'] as OrgRole[] },
];

const orgNavItems = [
  { to: '/org/members', icon: Users, label: 'Team', roles: ['owner'] as OrgRole[] },
];

export function AppShell() {
  const { user, memberships, logout } = useAuth();
  const { activeOrg, orgs, switchOrg } = useOrg();
  const navigate = useNavigate();

  const activeRole = useMemo(() => {
    if (!activeOrg) return null;
    const membership = memberships.find(m => m.org_id === activeOrg.id);
    return (membership?.role as OrgRole) || null;
  }, [activeOrg, memberships]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <DashboardShell
      navItems={navItems}
      orgNavItems={orgNavItems}
      brand="AI Interview"
      showMarketplace={true}
      showAdmin={user?.is_admin ?? false}
      useOrgSelector={true}
      activeRole={activeRole}
      user={user}
      orgs={orgs}
      activeOrg={activeOrg}
      onSwitchOrg={switchOrg}
      onLogout={handleLogout}
    />
  );
}
