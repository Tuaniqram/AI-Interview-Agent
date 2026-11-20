import { Link } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';

interface Crumb {
  label: string;
  to?: string;
}

export function Breadcrumb({ crumbs }: { crumbs: Crumb[] }) {
  return (
    <nav className="flex items-center gap-1.5 text-xs text-muted mb-4" aria-label="Breadcrumb">
      {crumbs.map((crumb, i) => {
        const isLast = i === crumbs.length - 1;
        return (
          <span key={i} className="flex items-center gap-1.5">
            {i > 0 && <ChevronRight className="w-3 h-3" />}
            {crumb.to && !isLast ? (
              <Link to={crumb.to} className="hover:text-secondary transition-colors">{crumb.label}</Link>
            ) : (
              <span className={isLast ? 'text-secondary font-medium' : ''}>{crumb.label}</span>
            )}
          </span>
        );
      })}
    </nav>
  );
}