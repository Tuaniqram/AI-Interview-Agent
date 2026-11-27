import { useId, useState, KeyboardEvent } from 'react';
import { X } from 'lucide-react';

interface TagInputProps {
  value: string;
  onChange: (csv: string) => void;
  placeholder?: string;
  label?: string;
}

export function TagInput({ value, onChange, placeholder = 'Type and press Enter', label }: TagInputProps) {
  const [input, setInput] = useState('');
  const id = useId();

  const tags = value ? value.split(',').map(s => s.trim()).filter(Boolean) : [];

  const addTag = (tag: string) => {
    const trimmed = tag.trim();
    if (!trimmed) return;
    const existing = tags.some(t => t.toLowerCase() === trimmed.toLowerCase());
    if (existing) return;
    const next = [...tags, trimmed].join(', ');
    onChange(next);
  };

  const removeTag = (idx: number) => {
    const next = tags.filter((_, i) => i !== idx).join(', ');
    onChange(next);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      addTag(input);
      setInput('');
    }
    if (e.key === 'Backspace' && !input && tags.length > 0) {
      removeTag(tags.length - 1);
    }
  };

  return (
    <div className="space-y-1.5">
      {label && <label htmlFor={id} className="block text-[13px] font-medium text-primary">{label}</label>}
      <div className="flex flex-wrap items-center gap-1.5 px-2 py-1 rounded-md border border-[var(--border-strong)] bg-input shadow-sm hover:border-[var(--text-tertiary)] focus-within:border-[var(--action-primary)] focus-within:ring-[3px] focus-within:ring-[var(--focus-ring)] transition-colors min-h-8">
        {tags.map((tag, i) => (
          <span key={i} className="inline-flex items-center gap-1 h-6 pl-2 pr-1 text-xs rounded border border-border bg-subtle text-primary">
            {tag}
            <button onClick={() => removeTag(i)} className="p-0.5 rounded text-tertiary hover:text-primary" type="button" aria-label={`Remove ${tag}`}>
              <X className="w-3 h-3" />
            </button>
          </span>
        ))}
        <input
          id={id}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={tags.length === 0 ? placeholder : ''}
          className="flex-1 min-w-[80px] h-6 px-1 bg-transparent text-[13px] text-primary placeholder:text-tertiary focus:outline-none"
        />
      </div>
      <p className="text-xs text-tertiary">Press Enter or comma after each one.</p>
    </div>
  );
}