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
    <div className="flex flex-wrap items-center gap-1.5 px-2 py-1.5 rounded-md border border-[var(--border-strong)] bg-input shadow-sm focus-within:ring-[3px] focus-within:ring-[var(--focus-ring)] focus-within:border-[var(--action-primary)] transition-colors min-h-[36px] cursor-text" onClick={(e) => { if (e.target === e.currentTarget) (e.currentTarget.querySelector('input') as HTMLInputElement)?.focus() }}>
      {chips.map((chip, i) => (
        <span key={i} className="inline-flex items-center gap-1 h-6 pl-2 pr-1 text-xs font-medium rounded-md bg-hover text-primary">
          {chip}
          <button type="button" onClick={() => removeChip(i)} className="w-4 h-4 rounded flex items-center justify-center text-tertiary hover:text-primary hover:bg-border transition-colors" aria-label={`Remove ${chip}`}>&times;</button>
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
        className="flex-1 min-w-[80px] h-6 px-1 bg-transparent text-[13px] text-primary outline-none placeholder:text-tertiary"
      />
    </div>
  );
}
