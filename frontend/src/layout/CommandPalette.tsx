import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, CornerDownLeft, Sun, Moon, LogOut } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';
import type { NavItem } from './Sidebar';

interface Command {
  id: string;
  label: string;
  group: string;
  icon: React.ComponentType<{ className?: string }>;
  run: () => void;
}

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
  pages: NavItem[];
  onLogout?: () => void;
}

/** Ctrl K: jump to any page in the current area, switch theme, or sign out. */
export function CommandPalette({ open, onClose, pages, onLogout }: CommandPaletteProps) {
  const navigate = useNavigate();
  const { isDark, toggle } = useTheme();
  const [query, setQuery] = useState('');
  const [index, setIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const commands = useMemo<Command[]>(() => {
    const list: Command[] = pages.map(p => ({
      id: p.to, label: p.label, group: 'Go to', icon: p.icon, run: () => navigate(p.to),
    }));
    list.push({ id: 'theme', label: isDark ? 'Switch to light theme' : 'Switch to dark theme', group: 'Actions', icon: isDark ? Sun : Moon, run: toggle });
    if (onLogout) list.push({ id: 'logout', label: 'Sign out', group: 'Actions', icon: LogOut, run: onLogout });
    return list;
  }, [pages, isDark, toggle, onLogout, navigate]);

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    return q ? commands.filter(c => c.label.toLowerCase().includes(q)) : commands;
  }, [commands, query]);

  useEffect(() => {
    if (open) { setQuery(''); setIndex(0); requestAnimationFrame(() => inputRef.current?.focus()); }
  }, [open]);
  useEffect(() => setIndex(0), [query]);

  if (!open) return null;

  const run = (c: Command | undefined) => { if (!c) return; onClose(); c.run(); };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setIndex(i => Math.min(i + 1, results.length - 1)); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setIndex(i => Math.max(i - 1, 0)); }
    else if (e.key === 'Enter') { e.preventDefault(); run(results[index]); }
    else if (e.key === 'Escape') { e.preventDefault(); onClose(); }
  };

  let lastGroup = '';
  return (
    <div className="fixed inset-0 z-[110] flex items-start justify-center pt-[14vh] px-4" role="dialog" aria-modal="true" aria-label="Search">
      <div className="fixed inset-0 bg-overlay" onClick={onClose} />
      <div className="relative w-full max-w-lg rounded-xl border border-border bg-elevated shadow-lg overflow-hidden" onKeyDown={onKeyDown}>
        <div className="flex items-center gap-2.5 px-4 h-12 border-b border-border">
          <Search className="w-4 h-4 text-tertiary shrink-0" />
          <input
            ref={inputRef}
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search pages and actions"
            className="flex-1 bg-transparent text-sm text-primary placeholder:text-tertiary focus:outline-none"
            role="combobox"
            aria-expanded="true"
            aria-controls="command-results"
            aria-activedescendant={results[index] ? `cmd-${results[index].id}` : undefined}
          />
          <kbd className="text-[11px] font-sans text-tertiary border border-border rounded px-1.5 py-0.5">Esc</kbd>
        </div>
        <ul id="command-results" role="listbox" className="max-h-80 overflow-y-auto p-1.5">
          {results.length === 0 && <li className="px-3 py-6 text-center text-sm text-tertiary">Nothing matches “{query}”.</li>}
          {results.map((c, i) => {
            const header = c.group !== lastGroup ? c.group : null;
            lastGroup = c.group;
            const Icon = c.icon;
            return (
              <React.Fragment key={c.id}>
                {header && <li className="px-2.5 pt-2 pb-1 text-xs text-tertiary" role="presentation">{header}</li>}
                <li
                  id={`cmd-${c.id}`}
                  role="option"
                  aria-selected={i === index}
                  onMouseMove={() => setIndex(i)}
                  onClick={() => run(c)}
                  className={`flex items-center gap-2.5 px-2.5 h-9 rounded-md text-[13px] cursor-pointer ${i === index ? 'bg-hover text-primary' : 'text-secondary'}`}
                >
                  <Icon className="w-4 h-4 text-tertiary shrink-0" />
                  <span className="flex-1 truncate">{c.label}</span>
                  {i === index && <CornerDownLeft className="w-3.5 h-3.5 text-tertiary" />}
                </li>
              </React.Fragment>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
