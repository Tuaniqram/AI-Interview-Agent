import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { DashboardShell } from './DashboardShell';
import { LayoutDashboard, Building2, Users } from 'lucide-react';

const navItems = [
  { to: '/admin', icon: LayoutDashboard, label: 'Dashboard', end: true },
  { to: '/admin/organizations', icon: Building2, label: 'Organizations' },
  { to: '/admin/users', icon: Users, label: 'Users' },
];

export function AdminShell() {
  const { logout, user } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

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
