import { ReactNode } from 'react';

interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: ReactNode;
}

export function PageHeader({ title, description, actions }: PageHeaderProps) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between mb-6">
      <div className="min-w-0">
        <h1 className="text-[22px] leading-7 font-semibold tracking-[-0.015em] text-primary">{title}</h1>
        {description && <p className="text-sm text-secondary mt-1 max-w-[65ch]">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2 shrink-0">{actions}</div>}
    </div>
  );
}
