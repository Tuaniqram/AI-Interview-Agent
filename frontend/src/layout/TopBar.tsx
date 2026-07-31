import { useLocation } from 'react-router-dom';
import { Sun, Moon, Menu } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';

const pageTitles: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/departments': 'Departments',
  '/sessions': 'Interview Sessions',
  '/analytics': 'Analytics',
  '/avatar-lab': 'Avatar Lab',
  '/settings': 'Settings',
  '/new-interview': 'New Interview',
};

interface TopBarProps {
  onMenuToggle?: () => void;
}

export function TopBar({ onMenuToggle }: TopBarProps) {
  const location = useLocation();
  const base = '/' + location.pathname.split('/').filter(Boolean)[0] || '/';
  const title = pageTitles[base] || 'AI Interview';
  const { isDark, toggle } = useTheme();

  return (
    <header className="h-14 bg-section flex items-center justify-between px-4 lg:px-6">
      <div className="flex items-center gap-3">
        {onMenuToggle && (
          <button
            onClick={onMenuToggle}
            className="p-2 rounded-lg text-muted hover:text-secondary hover:bg-hover transition-colors lg:hidden"
            aria-label="Toggle menu"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}
        <img src="/favicon.svg" className="w-5 h-5" alt="" />
        <h2 className="text-sm font-semibold text-primary">{title}</h2>
      </div>
      <button
        onClick={toggle}
        className="p-2 rounded-lg text-muted hover:text-secondary hover:bg-hover transition-colors"
        aria-label={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
      >
        {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
      </button>
    </header>
  );
}
