import { Check } from 'lucide-react';

interface CheckboxProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  id?: string;
}

export function Checkbox({ checked, onChange, label, id }: CheckboxProps) {
  const uid = id || `cb-${label.replace(/\s+/g, '-').toLowerCase()}`;

  return (
    <label
      htmlFor={uid}
      className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-sm text-secondary hover:bg-hover cursor-pointer transition-colors group"
    >
      <div className="relative w-4 h-4 shrink-0">
        <input
          id={uid}
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          className="sr-only peer"
        />
        <div className={`w-4 h-4 rounded border-2 transition-colors ${
          checked
            ? 'bg-[#7C3AED] border-[#7C3AED]'
            : 'border-[var(--border-color)] group-hover:border-[#7C3AED]/50'
        }`}>
          {checked && <Check className="w-3 h-3 text-white absolute inset-0 m-auto" strokeWidth={3} />}
        </div>
      </div>
      <span className="select-none">{label}</span>
    </label>
  );
}
