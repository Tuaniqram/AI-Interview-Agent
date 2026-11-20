import { useState, KeyboardEvent } from 'react';
import { X } from 'lucide-react';

interface TagInputProps {
  value: string;
  onChange: (csv: string) => void;
  placeholder?: string;
  label?: string;
}

export function TagInput({ value, onChange, placeholder = 'Type and press Enter', label }: TagInputProps) {
  const [input, setInput] = useState('');

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
      {label && <label className="block text-sm font-medium text-primary">{label}</label>}
      <div className="flex flex-wrap gap-1.5 px-3 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-page)] focus-within:ring-2 focus-within:ring-[var(--focus-ring)] transition-colors min-h-[38px]">
        {tags.map((tag, i) => (
          <span key={i} className="inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-md bg-[var(--action-primary)]/10 text-[var(--action-primary)]">
            {tag}
            <button onClick={() => removeTag(i)} className="hover:opacity-70" type="button" aria-label={`Remove ${tag}`}>
              <X className="w-3 h-3" />
            </button>
          </span>
        ))}
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={tags.length === 0 ? placeholder : ''}
          className="flex-1 min-w-[80px] bg-transparent text-sm text-[var(--text-primary)] placeholder:text-muted focus:outline-none"
        />
      </div>
      <p className="text-xs text-muted">Type a skill and press Enter to add</p>
    </div>
  );
}