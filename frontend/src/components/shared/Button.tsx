import { ButtonHTMLAttributes, ReactNode } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  icon?: ReactNode;
  iconPosition?: 'left' | 'right';
  loading?: boolean;
}

const base =
  'inline-flex items-center justify-center gap-1.5 font-medium whitespace-nowrap rounded-md transition-colors ' +
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)] focus-visible:ring-offset-1 focus-visible:ring-offset-[var(--bg-section)] ' +
  'disabled:opacity-50 disabled:cursor-not-allowed [&_svg]:w-4 [&_svg]:h-4 [&_svg]:shrink-0';

const variants: Record<string, string> = {
  // The one filled button on a screen: the action the page exists for.
  primary: 'bg-action-primary text-action-primary-text hover:bg-action-primary-hover shadow-sm',
  // Everything else that is still a button.
  secondary: 'bg-action-secondary text-action-secondary-text border border-border-strong hover:bg-action-secondary-hover shadow-sm',
  outline: 'bg-transparent text-primary border border-border-strong hover:bg-hover',
  danger: 'bg-action-danger text-action-danger-text hover:bg-action-danger-hover shadow-sm',
  ghost: 'bg-transparent text-secondary hover:bg-hover hover:text-primary',
};

const sizes: Record<string, string> = {
  sm: 'h-7 px-2.5 text-xs',
  md: 'h-8 px-3 text-[13px]',
  lg: 'h-10 px-4 text-sm',
};

export function Button({
  variant = 'primary',
  size = 'md',
  icon,
  iconPosition = 'left',
  loading = false,
  className = '',
  disabled,
  children,
  ...props
}: ButtonProps) {
  const isDisabled = disabled || loading;

  return (
    <button
      className={`${base} ${variants[variant]} ${sizes[size]} ${className}`}
      disabled={isDisabled}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading && (
        <svg className="animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden>
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      )}
      {!loading && icon && iconPosition === 'left' && icon}
      {children}
      {!loading && icon && iconPosition === 'right' && icon}
    </button>
  );
}
