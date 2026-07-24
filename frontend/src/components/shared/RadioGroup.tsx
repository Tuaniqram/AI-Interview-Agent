interface RadioOption {
  value: string;
  label: string;
}

interface RadioGroupProps {
  name: string;
  value: string;
  onChange: (value: string) => void;
  options: RadioOption[];
  label?: string;
}

export function RadioGroup({ name, value, onChange, options, label }: RadioGroupProps) {
  return (
    <div className="space-y-1">
      {label && (
        <p className="px-3 text-xs font-medium text-secondary">{label}</p>
      )}
      {options.map((opt) => {
        const uid = `${name}-${opt.value}`;
        const selected = value === opt.value;
        return (
          <label
            key={opt.value}
            htmlFor={uid}
            className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-sm text-secondary hover:bg-hover cursor-pointer transition-colors group"
          >
            <div className="relative w-4 h-4 shrink-0">
              <input
                id={uid}
                type="radio"
                name={name}
                checked={selected}
                onChange={() => onChange(opt.value)}
                className="sr-only peer"
              />
              <div className={`w-4 h-4 rounded-full border-2 transition-colors ${
                selected
                  ? 'border-[#7C3AED]'
                  : 'border-[var(--border-color)] group-hover:border-[#7C3AED]/50'
              }`}>
                {selected && (
                  <div className="absolute inset-0.5 rounded-full bg-[#7C3AED]" />
                )}
              </div>
            </div>
            <span className="select-none">{opt.label}</span>
          </label>
        );
      })}
    </div>
  );
}
