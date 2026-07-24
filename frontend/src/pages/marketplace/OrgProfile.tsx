import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { marketplaceService } from '../../services/marketplaceService';
import { LoadingSpinner } from '../../components/shared/LoadingSpinner';
import { EmptyState } from '../../components/shared/EmptyState';
import { Clock } from 'lucide-react';
import type { OrgListing, PublicInterview } from '../../types/marketplace';

export default function OrgProfile() {
  const { slug } = useParams<{ slug: string }>();
  const [org, setOrg] = useState<OrgListing | null>(null);
  const [interviews, setInterviews] = useState<PublicInterview[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!slug) return;
    setLoading(true);
    marketplaceService.getOrgProfile(slug)
      .then((data) => {
        setOrg(data.org);
        setInterviews(data.interviews);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [slug]);

  if (loading) return <LoadingSpinner message="Loading organization..." />;
  if (!org) return <EmptyState title="Organization not found" />;

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div className="flex items-start gap-6">
        <div className="w-16 h-16 rounded-xl bg-[var(--action-primary)]/10 flex items-center justify-center text-[var(--action-primary)] font-bold text-2xl flex-shrink-0">
          {org.name.charAt(0).toUpperCase()}
        </div>
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">{org.name}</h1>
          {org.description && (
            <p className="text-[var(--text-secondary)] mt-2">{org.description}</p>
          )}
          {org.website && (
            <a href={org.website} target="_blank" rel="noopener noreferrer"
              className="inline-block mt-2 text-sm text-[var(--action-primary)] hover:underline">
              {org.website}
            </a>
          )}
        </div>
      </div>

      <div>
        <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-4">
          Open Interviews ({interviews.length})
        </h2>
        {interviews.length === 0 ? (
          <EmptyState title="No open interviews" />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {interviews.map((interview) => {
              const skills = interview.skills_required?.split(',').map(s => s.trim()).filter(Boolean) || [];
              const isExpired = interview.expires_at ? new Date(interview.expires_at) < new Date() : false;
              const daysUntil = interview.expires_at
                ? Math.ceil((new Date(interview.expires_at).getTime() - Date.now()) / 86400000)
                : null;
              return (
                <Link
                  key={interview.id}
                  to={`/marketplace/interviews/${interview.id}`}
                  className="p-4 rounded-xl bg-[var(--bg-section)] border border-[var(--border-color)] hover:border-[var(--action-primary)] transition-colors"
                >
                  <h3 className="font-semibold text-[var(--text-primary)]">{interview.title}</h3>
                  {interview.department_name && (
                    <p className="text-xs text-[var(--text-muted)] mt-0.5">{interview.department_name}</p>
                  )}
                  {interview.description && (
                    <p className="text-sm text-[var(--text-secondary)] mt-1 line-clamp-2">{interview.description}</p>
                  )}
                  <div className="flex items-center gap-2 flex-wrap mt-3">
                    <span className="text-xs px-2 py-0.5 rounded bg-[var(--action-primary)]/10 text-[var(--action-primary)]">
                      {interview.interview_mode}
                    </span>
                    {skills.slice(0, 2).map(skill => (
                      <span key={skill} className="text-xs px-2 py-0.5 rounded bg-[var(--bg-page)] text-[var(--text-muted)] border border-[var(--border-color)]">
                        {skill}
                      </span>
                    ))}
                    {skills.length > 2 && (
                      <span className="text-xs text-[var(--text-muted)]">+{skills.length - 2} more</span>
                    )}
                    {isExpired ? (
                      <span className="text-xs px-2 py-0.5 rounded bg-red-500/15 text-red-500">Expired</span>
                    ) : daysUntil !== null && daysUntil <= 7 ? (
                      <span className="text-xs px-2 py-0.5 rounded bg-yellow-500/15 text-yellow-500 flex items-center gap-1">
                        <Clock className="w-3 h-3" /> {daysUntil}d
                      </span>
                    ) : null}
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
