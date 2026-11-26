import { Link } from 'react-router-dom';
import { Users } from 'lucide-react';
import type { OrgListing } from '../../types/marketplace';

interface OrgCardProps {
  org: OrgListing;
}

export function OrgCard({ org }: OrgCardProps) {
  return (
    <Link
      to={`/opportunity-hub/organizations/${org.slug}`}
      className="block p-5 rounded-xl bg-[var(--bg-section)] border border-[var(--border-color)] hover:border-border-strong card-hover group"
    >
      <div className="flex items-start gap-4">
        <div className="w-12 h-12 rounded-xl bg-action-primary flex items-center justify-center shrink-0 text-action-primary-text font-semibold text-lg"
          >
          {org.name.charAt(0).toUpperCase()}
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="font-semibold text-primary truncate group-hover:text-[var(--action-primary)] transition-colors font-heading">{org.name}</h3>
          {org.description && (
            <p className="text-sm text-secondary mt-0.5 line-clamp-2">{org.description}</p>
          )}
          <div className="flex items-center gap-3 mt-2.5">
            <span className="flex items-center gap-1 text-xs text-muted">
              <Users className="w-3.5 h-3.5" />
              {org.interview_count} open interview{org.interview_count !== 1 ? 's' : ''}
            </span>
          </div>
        </div>
      </div>
    </Link>
  );
}
