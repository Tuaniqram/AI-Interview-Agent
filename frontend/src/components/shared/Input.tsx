import { InputHTMLAttributes, ReactNode, useId } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
  icon?: ReactNode;
}

const baseInput = 'h-8 w-full bg-input text-primary border border-[var(--border-strong)] hover:border-[var(--text-tertiary)] focus:border-[var(--action-primary)] rounded-md px-3 text-[13px] shadow-sm focus:outline-none focus:ring-[3px] focus:ring-[var(--focus-ring)] transition-colors placeholder:text-tertiary disabled:opacity-50 disabled:cursor-not-allowed';

export function Input({ label, error, hint, icon, className = '', id, ...props }: InputProps) {
  // Link the label to its input (click-to-focus, screen readers, form testing).
  const autoId = useId();
  const inputId = id ?? autoId;
  const describedBy = error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined;
  return (
    <div className="space-y-1.5">
      {label && (
        <label htmlFor={inputId} className="block text-[13px] font-medium text-primary">{label}</label>
      )}
      <div className="relative">
        {icon && (
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-tertiary [&_svg]:w-4 [&_svg]:h-4">{icon}</span>
        )}
        <input
          id={inputId}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          className={`${baseInput} ${icon ? 'pl-9' : ''} ${className}`}
          {...props}
        />
      </div>
      {error && <p id={`${inputId}-error`} className="text-xs text-error">{error}</p>}
      {hint && !error && <p id={`${inputId}-hint`} className="text-xs text-tertiary">{hint}</p>}
    </div>
  );
}




