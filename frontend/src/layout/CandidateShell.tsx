import { useNavigate } from 'react-router-dom';
import { useCandidateAuth } from '../contexts/CandidateAuthContext';
import { DashboardShell } from './DashboardShell';
import { LayoutDashboard, ListChecks, PlayCircle, User } from 'lucide-react';

const navItems = [
  { to: '/candidate/dashboard', icon: LayoutDashboard, label: 'Dashboard', end: true },
  { to: '/candidate/interviews', icon: ListChecks, label: 'My Interviews' },
  { to: '/candidate/practice', icon: PlayCircle, label: 'Practice' },
  { to: '/candidate/profile', icon: User, label: 'Profile' },
];

export function CandidateShell() {
  const { logout, candidate } = useCandidateAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <DashboardShell
      navItems={navItems}
      brand="My Dashboard"
      showMarketplace={true}
      showAdmin={false}
      useOrgSelector={false}
      user={candidate}
      onLogout={handleLogout}
    />
  );
}
