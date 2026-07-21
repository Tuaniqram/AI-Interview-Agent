import { useLocation } from 'react-router-dom';
import { Sun, Moon, Menu } from 'lucide-react';
import { useState, useEffect } from 'react';

const THEME_KEY = 'ai-interview-theme';

const pageTitles: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/companies': 'Companies',
  '/sessions': 'Interview Sessions',
  '/analytics': 'Analytics',
  '/avatar-lab': 'Avatar Lab',
  '/settings': 'Settings',
  '/new-interview': 'New Interview',
};

function getInitialTheme(): boolean {
  const stored = localStorage.getItem(THEME_KEY);
  if (stored === 'dark') return true;
  if (stored === 'light') return false;
  return window.matchMedia('(prefers-color-scheme: dark)').matches;
}

interface TopBarProps {
  onMenuToggle?: () => void;
}

export function TopBar({ onMenuToggle }: TopBarProps) {
  const location = useLocation();
  const base = '/' + location.pathname.split('/').filter(Boolean)[0] || '/';
  const title = pageTitles[base] || 'AI Interview';

  const [isDark, setIsDark] = useState(getInitialTheme);

  useEffect(() => {
    const theme = isDark ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(THEME_KEY, theme);
  }, [isDark]);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
  }, []);

  return (
    <header className="h-14 bg-section shadow-sm flex items-center justify-between px-4 lg:px-6">
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
        <h2 className="text-sm font-semibold text-primary">{title}</h2>
      </div>
      <button
        onClick={() => setIsDark(prev => !prev)}
        className="p-2 rounded-lg text-muted hover:text-secondary hover:bg-hover transition-colors"
        aria-label={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
      >
        {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
      </button>
    </header>
  );
}
