import { ReactNode, KeyboardEvent } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
  hover?: boolean;
  padding?: 'none' | 'sm' | 'md' | 'lg';
  onClick?: () => void;
}

const paddings = { none: '', sm: 'p-3', md: 'p-4', lg: 'p-6' };

/** A bordered surface. Flat: the line separates it, not a shadow. Clickable cards are keyboard-reachable. */
export function Card({ children, className = '', hover = false, padding = 'md', onClick }: CardProps) {
  const interactive = !!onClick;
  const onKeyDown = interactive
    ? (e: KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick?.(); } }
    : undefined;
  return (
    <div
      onClick={onClick}
      onKeyDown={onKeyDown}
      role={interactive ? 'button' : undefined}
      tabIndex={interactive ? 0 : undefined}
      className={`bg-section border border-border rounded-xl ${paddings[padding]} ${
        hover || interactive ? 'transition-colors hover:border-border-strong hover:bg-subtle' : ''
      } ${interactive ? 'cursor-pointer' : ''} ${className}`}
    >
      {children}
    </div>
  );
}

/** A titled section inside a card: a header row with an optional action, then the body. */
export function CardHeader({ title, description, action }: { title: ReactNode; description?: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 mb-3">
      <div className="min-w-0">
        <h3 className="text-sm font-semibold text-primary">{title}</h3>
        {description && <p className="text-[13px] text-tertiary mt-0.5">{description}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}
