import { Link } from 'react-router-dom';
import type { OrgListing } from '../../types/marketplace';

interface OrgCardProps {
  org: OrgListing;
}

export function OrgCard({ org }: OrgCardProps) {
  return (
    <Link
      to={`/marketplace/organizations/${org.slug}`}
      className="block p-6 rounded-xl bg-[var(--bg-section)] border border-[var(--border-color)] hover:border-[var(--action-primary)] transition-all hover:shadow-md"
    >
      <div className="flex items-start gap-4">
        <div className="w-12 h-12 rounded-lg bg-[var(--action-primary)]/10 flex items-center justify-center text-[var(--action-primary)] font-bold text-lg flex-shrink-0">
          {org.name.charAt(0).toUpperCase()}
        </div>
        <div className="min-w-0">
          <h3 className="font-semibold text-[var(--text-primary)] truncate">{org.name}</h3>
          {org.description && (
            <p className="text-sm text-[var(--text-secondary)] mt-1 line-clamp-2">{org.description}</p>
          )}
          <p className="text-xs text-[var(--text-secondary)] mt-2">
            {org.interview_count} open interview{org.interview_count !== 1 ? 's' : ''}
          </p>
        </div>
      </div>
    </Link>
  );
}
