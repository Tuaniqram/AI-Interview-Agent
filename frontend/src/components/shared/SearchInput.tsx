import { Search } from 'lucide-react';

interface SearchInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
}

export function SearchInput({ value, onChange, placeholder = 'Search...', className = '' }: SearchInputProps) {
  return (
    <div className={`relative ${className}`}>
      <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-tertiary pointer-events-none" />
      <input
        type="text"
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label={placeholder}
        className="h-8 w-full bg-input text-primary border border-[var(--border-strong)] hover:border-[var(--text-tertiary)] focus:border-[var(--action-primary)] rounded-md pl-8 pr-3 text-[13px] shadow-sm focus:outline-none focus:ring-[3px] focus:ring-[var(--focus-ring)] transition-colors placeholder:text-tertiary disabled:opacity-50 disabled:cursor-not-allowed"
      />
    </div>
  );
}
