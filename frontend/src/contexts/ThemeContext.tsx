import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';

const THEME_KEY = 'ai-interview-theme';

export type ThemeMode = 'light' | 'dark' | 'system';

interface ThemeContextType {
  isDark: boolean;
  mode: ThemeMode;
  setMode: (mode: ThemeMode) => void;
  toggle: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

const media = () => window.matchMedia('(prefers-color-scheme: dark)');

function readMode(): ThemeMode {
  const stored = localStorage.getItem(THEME_KEY);
  return stored === 'dark' || stored === 'light' ? stored : 'system';
}

function resolve(mode: ThemeMode): boolean {
  return mode === 'system' ? media().matches : mode === 'dark';
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [mode, setModeState] = useState<ThemeMode>(readMode);
  const [isDark, setIsDark] = useState(() => resolve(readMode()));

  // Apply the resolved theme, and follow the OS while the mode is "system".
  useEffect(() => {
    const apply = () => {
      const dark = resolve(mode);
      setIsDark(dark);
      document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');
    };
    apply();
    if (mode !== 'system') return;
    const mq = media();
    mq.addEventListener('change', apply);
    return () => mq.removeEventListener('change', apply);
  }, [mode]);

  // Keep other tabs in step.
  useEffect(() => {
    const handleStorage = (e: StorageEvent) => {
      if (e.key === THEME_KEY) setModeState(readMode());
    };
    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
  }, []);

  const setMode = useCallback((next: ThemeMode) => {
    if (next === 'system') localStorage.removeItem(THEME_KEY);
    else localStorage.setItem(THEME_KEY, next);
    setModeState(next);
  }, []);

  const toggle = useCallback(() => setMode(isDark ? 'light' : 'dark'), [isDark, setMode]);

  return (
    <ThemeContext.Provider value={{ isDark, mode, setMode, toggle }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider');
  return ctx;
}
