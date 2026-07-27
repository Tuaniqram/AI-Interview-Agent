import { useState, useRef, useEffect } from 'react';
import { ChevronDown, X } from 'lucide-react';

export interface MultiSelectOption {
  value: string;
  label: string;
}

interface MultiSelectProps {
  label?: string;
  options: MultiSelectOption[];
  values: string[];
  onChange: (values: string[]) => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
}

export function MultiSelect({ label, options, values, onChange, placeholder, className = '', disabled }: MultiSelectProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const toggle = (val: string) => {
    if (values.includes(val)) {
      onChange(values.filter(v => v !== val));
    } else {
      onChange([...values, val]);
    }
  };

  return (
    <div className={`space-y-1.5 ${className}`}>
      {label && <label className="block text-xs font-medium text-secondary">{label}</label>}
      <div ref={ref} className="relative">
        <button type="button" onClick={() => setOpen(!open)} disabled={disabled}
          className={`w-full flex items-center gap-1 flex-wrap px-3 py-2 text-sm rounded-lg border border-border bg-input text-primary transition-colors
            ${disabled ? 'opacity-50 cursor-not-allowed' : 'hover:border-border/80'}
            ${open ? 'ring-2 ring-focus-ring' : ''}`}
        >
          {values.length === 0 && <span className="text-muted">{placeholder || 'Select...'}</span>}
          {values.slice(0, 3).map(v => {
            const opt = options.find(o => o.value === v);
            return (
              <span key={v} className="inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded bg-action-primary/10 text-action-primary">
                {opt?.label || v}
                {!disabled && <X className="w-3 h-3 cursor-pointer" onClick={(e) => { e.stopPropagation(); toggle(v); }} />}
              </span>
            );
          })}
          {values.length > 3 && <span className="text-xs text-muted">+{values.length - 3}</span>}
          <ChevronDown className={`w-4 h-4 text-muted ml-auto transition-transform ${open ? 'rotate-180' : ''}`} />
        </button>
        {open && (
          <div className="absolute z-50 mt-1 w-full bg-elevated border border-border rounded-lg shadow-lg max-h-60 overflow-y-auto">
            {options.map(opt => {
              const checked = values.includes(opt.value);
              return (
                <label key={opt.value} className="flex items-center gap-2 px-3 py-2 text-sm text-secondary hover:bg-hover cursor-pointer">
                  <input type="checkbox" checked={checked} onChange={() => toggle(opt.value)} className="rounded border-border" />
                  {opt.label}
                </label>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
