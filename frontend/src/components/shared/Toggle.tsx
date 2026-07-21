interface ToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
  disabled?: boolean;
  size?: 'sm' | 'md';
}

const trackSizes: Record<string, string> = {
  sm: 'w-9 h-5',
  md: 'w-11 h-6',
};

const thumbSizes: Record<string, string> = {
  sm: 'w-4 h-4',
  md: 'w-5 h-5',
};

export function Toggle({ checked, onChange, label, disabled = false, size = 'md' }: ToggleProps) {
  return (
    <label className={`inline-flex items-center gap-2.5 ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}>
      <button
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => !disabled && onChange(!checked)}
        className={`relative inline-flex shrink-0 rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)] ${trackSizes[size]} ${checked ? 'bg-action-primary' : 'bg-input'}`}
      >
        <span
          className={`pointer-events-none inline-block rounded-full bg-white shadow-sm transition-transform ${thumbSizes[size]} ${size === 'sm' ? 'mt-0.5 ml-0.5' : 'mt-0.5 ml-0.5'} ${checked ? (size === 'sm' ? 'translate-x-4' : 'translate-x-5') : 'translate-x-0'}`}
        />
      </button>
      {label && <span className="text-sm text-primary">{label}</span>}
    </label>
  );
}
