import { ReactNode } from 'react';

interface FlatSurfaceProps {
  children: ReactNode;
  className?: string;
}

/**
 * A plain bordered surface: thin line, no shadow, no blur. For marketing pages, where the product's glass
 * `Card` does not belong.
 */
export function FlatSurface({ children, className = '' }: FlatSurfaceProps) {
  return <div className={`rounded-ui-lg border border-border bg-elevated p-4 ${className}`}>{children}</div>;
}
