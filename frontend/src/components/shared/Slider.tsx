interface SliderProps {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  label?: string;
  className?: string;
}

export function Slider({ value, onChange, min = 0, max = 100, step = 1, label, className = '' }: SliderProps) {
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {label && <label className="text-xs text-muted whitespace-nowrap">{label}</label>}
      <input
        type="range"
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        min={min}
        max={max}
        step={step}
        className="flex-1 h-1.5 rounded-full appearance-none cursor-pointer bg-border accent-[var(--action-primary)]
          [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3.5 [&::-webkit-slider-thumb]:h-3.5 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-[var(--action-primary)] [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:transition-transform [&::-webkit-slider-thumb]:hover:scale-125
          [&::-moz-range-thumb]:w-3.5 [&::-moz-range-thumb]:h-3.5 [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:bg-[var(--action-primary)] [&::-moz-range-thumb]:cursor-pointer [&::-moz-range-thumb]:border-0"
      />
      <span className="text-xs text-primary font-medium w-8 text-right tabular-nums">{value}</span>
    </div>
  );
}
