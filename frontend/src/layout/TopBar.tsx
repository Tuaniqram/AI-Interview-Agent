import { useLocation } from 'react-router-dom';
import { Sun, Moon } from 'lucide-react';
import { useState, useEffect } from 'react';

const THEME_KEY = 'ai-interview-theme';

const pageTitles: Record<string, string> = {
  '/': 'Dashboard',
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

export function TopBar() {
  const location = useLocation();
  const base = '/' + location.pathname.split('/').filter(Boolean)[0] || '/';
  const title = pageTitles[base] || 'AI Interview';

  const [isDark, setIsDark] = useState(getInitialTheme);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
    localStorage.setItem(THEME_KEY, isDark ? 'dark' : 'light');
  }, [isDark]);

  return (
    <header className="h-14 bg-section border-b border-default flex items-center justify-between px-6">
      <h2 className="text-sm font-semibold text-primary">{title}</h2>
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
