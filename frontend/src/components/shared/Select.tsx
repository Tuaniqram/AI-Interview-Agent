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
      {label && <label className="block text-xs font-medium text-secondary">{label}</label>}
      <div ref={ref} className="relative">
        <button type="button" onClick={() => setOpen(!open)} disabled={disabled}
          className={`w-full flex items-center justify-between px-3 py-2 text-sm rounded-lg border transition-colors
            ${error ? 'border-error' : 'border-border'}
            ${disabled ? 'bg-input/50 text-muted cursor-not-allowed' : 'bg-input text-primary hover:border-border/80'}
            ${open ? 'ring-2 ring-focus-ring' : ''}`}
        >
          <span className={selected ? '' : 'text-muted'}>{selected ? selected.label : (placeholder || 'Select...')}</span>
          <ChevronDown className={`w-4 h-4 text-muted transition-transform ${open ? 'rotate-180' : ''}`} />
        </button>
        {open && (
          <div className="absolute z-50 mt-1 w-full bg-elevated border border-border rounded-lg shadow-lg max-h-60 overflow-y-auto">
            {options.length === 0 && (
              <div className="px-3 py-2 text-sm text-muted">No options</div>
            )}
            {options.map(opt => (
              <button key={opt.value} type="button" onClick={() => { onChange(opt.value); setOpen(false); }}
                className={`w-full text-left px-3 py-2 text-sm transition-colors
                  ${opt.value === value ? 'bg-action-primary/10 text-action-primary font-medium' : 'text-secondary hover:bg-hover'}
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
