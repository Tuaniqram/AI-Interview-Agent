import { InputHTMLAttributes, ReactNode, useId } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
  icon?: ReactNode;
}

const baseInput = 'w-full bg-input text-primary rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)] transition-colors placeholder:text-muted disabled:opacity-50 disabled:cursor-not-allowed';

export function Input({ label, error, hint, icon, className = '', id, ...props }: InputProps) {
  // Link the label to its input (click-to-focus, screen readers, form testing).
  const autoId = useId();
  const inputId = id ?? autoId;
  const describedBy = error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined;
  return (
    <div className="space-y-1">
      {label && (
        <label htmlFor={inputId} className="block text-xs font-medium text-primary">{label}</label>
      )}
      <div className="relative">
        {icon && (
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted">{icon}</span>
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
      {hint && !error && <p id={`${inputId}-hint`} className="text-xs text-muted">{hint}</p>}
    </div>
  );
}




