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
      className="block p-5 rounded-xl bg-[var(--bg-section)] border border-[var(--border-color)] hover:border-[#7C3AED]/40 card-hover group"
    >
      <div className="flex items-start gap-4">
        <div className="w-12 h-12 rounded-xl flex items-center justify-center shrink-0 text-white font-bold text-lg"
          style={{ background: `linear-gradient(135deg, #7C3AED, #A78BFA)` }}>
          {org.name.charAt(0).toUpperCase()}
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="font-semibold text-primary truncate group-hover:text-[#7C3AED] transition-colors font-heading">{org.name}</h3>
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
