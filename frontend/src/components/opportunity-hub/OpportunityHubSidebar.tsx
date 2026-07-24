import { Link, useLocation } from 'react-router-dom';
import { Home, LayoutDashboard, X, Search } from 'lucide-react';
import { Checkbox } from '../shared/Checkbox';
import { RadioGroup } from '../shared/RadioGroup';

export interface HubFilters {
  modes: string[];
  expiry: string;
}

interface OpportunityHubSidebarProps {
  open: boolean;
  onClose: () => void;
  isAuthenticated: boolean;
  filters: HubFilters;
  onFiltersChange: (filters: HubFilters) => void;
  onApply: () => void;
}

const INTERVIEW_MODES = [
  { value: 'typing', label: 'Typing' },
  { value: 'voice', label: 'Voice' },
  { value: 'avatar', label: 'Avatar' },
];

const EXPIRY_OPTIONS = [
  { value: 'any', label: 'Any Time' },
  { value: '7d', label: 'Within 7 days' },
  { value: '30d', label: 'Within 30 days' },
];

export function OpportunityHubSidebar({
  open, onClose, isAuthenticated, filters, onFiltersChange, onApply,
}: OpportunityHubSidebarProps) {
  const location = useLocation();

  const toggleMode = (mode: string) => {
    const next = filters.modes.includes(mode)
      ? filters.modes.filter(m => m !== mode)
      : [...filters.modes, mode];
    onFiltersChange({ ...filters, modes: next });
  };

  const isActive = (path: string) => location.pathname === path;

  return (
    <>
      {open && (
        <div className="fixed inset-0 bg-overlay/50 z-40 lg:hidden" onClick={onClose} />
      )}

      <aside className={`w-56 shrink-0 h-full bg-[var(--bg-section)] border-r border-[var(--border-color)] overflow-y-auto
        ${open ? 'fixed left-0 top-16 z-50' : 'hidden'}
        lg:static lg:block lg:z-auto
      `}>
        <div className="p-4 border-b border-[var(--border-color)] flex items-center justify-between lg:hidden">
          <span className="font-semibold text-sm text-primary">Navigation</span>
          <button onClick={onClose} className="p-1 rounded-lg text-secondary hover:text-primary hover:bg-hover" aria-label="Close sidebar">
            <X className="w-4 h-4" />
          </button>
        </div>

        <nav className="p-3 space-y-1">
          <p className="px-3 text-xs font-medium text-muted uppercase tracking-wider mb-2 mt-1">
            Browse
          </p>

          <Link
            to="/opportunity-hub"
            onClick={onClose}
            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
              isActive('/opportunity-hub')
                ? 'bg-[#7C3AED]/15 text-[#7C3AED]'
                : 'text-secondary hover:bg-hover hover:text-primary'
            }`}
          >
            <Home className="w-4 h-4" />
            All Opportunities
          </Link>

          {isAuthenticated && (
            <>
              <div className="h-px bg-[var(--border-color)] my-3" />
              <p className="px-3 text-xs font-medium text-muted uppercase tracking-wider mb-2">
                Account
              </p>
              <Link
                to="/dashboard"
                onClick={onClose}
                className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-secondary hover:bg-hover hover:text-primary transition-colors"
              >
                <LayoutDashboard className="w-4 h-4" />
                Back to Dashboard
              </Link>
            </>
          )}

          <div className="h-px bg-[var(--border-color)] my-3" />

          <p className="px-3 text-xs font-medium text-muted uppercase tracking-wider mb-2">
            Filters
          </p>

          <div className="space-y-1 mb-4">
            <p className="px-3 text-xs font-medium text-secondary">Interview Mode</p>
            {INTERVIEW_MODES.map(mode => (
              <Checkbox
                key={mode.value}
                checked={filters.modes.includes(mode.value)}
                onChange={() => toggleMode(mode.value)}
                label={mode.label}
              />
            ))}
          </div>

          <div className="mb-4">
            <RadioGroup
              name="expiry"
              label="Expiry"
              value={filters.expiry}
              onChange={(v) => onFiltersChange({ ...filters, expiry: v })}
              options={EXPIRY_OPTIONS}
            />
          </div>

          <button
            onClick={() => { onApply(); onClose(); }}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm font-medium bg-[#7C3AED] text-white hover:bg-[#6D28D9] transition-colors"
          >
            <Search className="w-3.5 h-3.5" />
            Apply Filters
          </button>
        </nav>
      </aside>
    </>
  );
}
