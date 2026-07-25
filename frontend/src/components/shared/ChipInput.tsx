import { useState, KeyboardEvent } from 'react';

interface ChipInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
}

export function ChipInput({ value, onChange, placeholder = 'Type and press Enter', disabled }: ChipInputProps) {
  const [input, setInput] = useState('');
  const chips = value ? value.split(',').map(s => s.trim()).filter(Boolean) : [];

  const addChip = (text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;
    if (chips.includes(trimmed)) return;
    const next = [...chips, trimmed].join(', ');
    onChange(next);
  };

  const removeChip = (index: number) => {
    const next = chips.filter((_, i) => i !== index).join(', ');
    onChange(next);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      addChip(input);
      setInput('');
    }
    if (e.key === 'Backspace' && !input && chips.length > 0) {
      removeChip(chips.length - 1);
    }
  };

  return (
    <div className="flex flex-wrap items-center gap-1.5 px-3 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-page)] focus-within:ring-2 focus-within:ring-[var(--focus-ring)] focus-within:border-[var(--action-primary)] transition-colors min-h-[42px] cursor-text" onClick={(e) => { if (e.target === e.currentTarget) (e.currentTarget.querySelector('input') as HTMLInputElement)?.focus() }}>
      {chips.map((chip, i) => (
        <span key={i} className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-[var(--action-primary)]/10 text-[var(--action-primary)]">
          {chip}
          <button type="button" onClick={() => removeChip(i)} className="hover:text-red-500 transition-colors" aria-label={`Remove ${chip}`}>&times;</button>
        </span>
      ))}
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={() => { if (input) { addChip(input); setInput(''); } }}
        placeholder={chips.length === 0 ? placeholder : ''}
        disabled={disabled}
        className="flex-1 min-w-[80px] bg-transparent text-sm text-[var(--text-primary)] outline-none placeholder:text-[var(--text-muted)]"
      />
    </div>
  );
}
