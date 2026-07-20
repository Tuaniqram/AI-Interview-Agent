import { ReactNode } from 'react';

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4">
      {icon && <div className="text-muted mb-4">{icon}</div>}
      <h3 className="text-base font-medium text-primary mb-1">{title}</h3>
      {description && <p className="text-sm text-secondary mb-4 max-w-sm text-center">{description}</p>}
      {action}
    </div>
  );
}
