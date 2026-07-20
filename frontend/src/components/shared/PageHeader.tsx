import { ReactNode } from 'react';

interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: ReactNode;
}

export function PageHeader({ title, description, actions }: PageHeaderProps) {
  return (
    <div className="flex items-start justify-between mb-6">
      <div>
        <h1 className="text-xl font-semibold text-primary">{title}</h1>
        {description && <p className="text-sm text-secondary mt-1">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-3 shrink-0 ml-4">{actions}</div>}
    </div>
  );
}
