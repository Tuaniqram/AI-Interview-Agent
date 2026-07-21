import { ButtonHTMLAttributes, ReactNode } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  icon?: ReactNode;
  iconPosition?: 'left' | 'right';
  loading?: boolean;
}

const base = 'inline-flex items-center justify-center gap-2 font-medium transition-all rounded-lg disabled:opacity-50 disabled:cursor-not-allowed';

const variants: Record<string, string> = {
  primary: 'bg-action-primary text-inverse hover:bg-action-primary-hover active:scale-[0.98]',
  secondary: 'bg-action-ghost-hover text-action-ghost-text hover:bg-action-secondary-hover',
  danger: 'bg-action-danger text-inverse hover:bg-action-danger-hover',
  ghost: 'bg-transparent text-secondary hover:bg-hover',
  outline: 'bg-transparent text-primary border border-strong hover:bg-hover',
};

const sizes: Record<string, string> = {
  sm: 'px-3 py-1.5 text-xs',
  md: 'px-4 py-2 text-sm',
  lg: 'px-6 py-3 text-sm',
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
      {...props}
    >
      {loading && (
        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
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

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
}

const iconSizes: Record<string, string> = {
  sm: 'w-8 h-8',
  md: 'w-10 h-10',
  lg: 'w-12 h-12',
};

const iconInnerSizes: Record<string, string> = {
  sm: 'w-4 h-4',
  md: 'w-5 h-5',
  lg: 'w-6 h-6',
};

export function IconButton({
  variant = 'primary',
  size = 'md',
  className = '',
  disabled,
  children,
  ...props
}: IconButtonProps) {
  return (
    <button
      className={`${base} ${variants[variant]} ${iconSizes[size]} rounded-full shrink-0 disabled:opacity-30 ${className}`}
      disabled={disabled}
      {...props}
    >
      <span className={iconInnerSizes[size]}>{children}</span>
    </button>
  );
}
