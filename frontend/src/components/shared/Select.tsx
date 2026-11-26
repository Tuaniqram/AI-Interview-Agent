import { useState, useRef, useEffect } from 'react';
import { ChevronDown } from 'lucide-react';

export interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps {
  label?: string;
  options: SelectOption[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  error?: string;
  className?: string;
  disabled?: boolean;
}

export function Select({ label, options, value, onChange, placeholder, error, className = '', disabled }: SelectProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const selected = options.find(o => o.value === value);

  return (
    <div className={`space-y-1.5 ${className}`}>
      {label && <label className="block text-[13px] font-medium text-primary">{label}</label>}
      <div ref={ref} className="relative">
        <button type="button" onClick={() => setOpen(!open)} disabled={disabled}
          aria-haspopup="listbox" aria-expanded={open}
          className={`w-full h-8 flex items-center justify-between gap-2 px-3 text-[13px] rounded-md border shadow-sm transition-colors
            ${error ? 'border-error' : 'border-[var(--border-strong)]'}
            ${disabled ? 'bg-input opacity-50 text-tertiary cursor-not-allowed' : 'bg-input text-primary hover:border-[var(--text-tertiary)]'}
            ${open ? 'ring-[3px] ring-[var(--focus-ring)] border-[var(--action-primary)]' : ''}`}
        >
          <span className={`truncate ${selected ? '' : 'text-tertiary'}`}>{selected ? selected.label : (placeholder || 'Select...')}</span>
          <ChevronDown className={`w-4 h-4 shrink-0 text-tertiary transition-transform ${open ? 'rotate-180' : ''}`} />
        </button>
        {open && (
          <div role="listbox" className="absolute z-50 mt-1 w-full min-w-[10rem] bg-elevated border border-border rounded-lg shadow-lg max-h-60 overflow-y-auto p-1">
            {options.length === 0 && (
              <div className="px-3 py-2 text-sm text-muted">No options</div>
            )}
            {options.map(opt => (
              <button key={opt.value} type="button" onClick={() => { onChange(opt.value); setOpen(false); }}
                role="option" aria-selected={opt.value === value}
                className={`w-full text-left px-2.5 h-8 rounded-md text-[13px] transition-colors
                  ${opt.value === value ? 'bg-action-primary-soft text-action-primary font-medium' : 'text-primary hover:bg-hover'}
                `}
              >
                {opt.label}
              </button>
            ))}
          </div>
        )}
      </div>
      {error && <p className="text-xs text-error">{error}</p>}
    </div>
  );
}
