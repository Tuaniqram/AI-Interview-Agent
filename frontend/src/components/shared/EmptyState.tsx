import { ReactNode } from 'react';

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-14 px-4">
      {icon && <div className="w-11 h-11 mb-4 rounded-xl border border-border bg-subtle text-tertiary flex items-center justify-center [&_svg]:w-5 [&_svg]:h-5">{icon}</div>}
      <h3 className="text-sm font-semibold text-primary">{title}</h3>
      {description && <p className="text-[13px] text-secondary mt-1 max-w-sm">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
