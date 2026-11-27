import { Navigate, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { DashboardShell } from './DashboardShell';
import {
  LayoutDashboard, Building2, Users, ScrollText, Cpu, Mail, HeartPulse,
} from 'lucide-react';

const navItems = [
  { to: '/admin', icon: LayoutDashboard, label: 'Dashboard', end: true },
  { to: '/admin/organizations', icon: Building2, label: 'Organizations' },
  { to: '/admin/users', icon: Users, label: 'Users' },
  { to: '/admin/audit-logs', icon: ScrollText, label: 'Audit logs' },
  { to: '/admin/llm', icon: Cpu, label: 'LLM' },
  { to: '/admin/email-templates', icon: Mail, label: 'Emails' },
  { to: '/admin/health', icon: HeartPulse, label: 'Health' },
];

export function AdminShell() {
  const { logout, user, isLoading } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  if (!isLoading && !user?.is_admin) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <DashboardShell
      navItems={navItems}
      brand="Admin Panel"
      showMarketplace={false}
      showAdmin={false}
      useOrgSelector={false}
      user={user}
      onLogout={handleLogout}
    />
  );
}
