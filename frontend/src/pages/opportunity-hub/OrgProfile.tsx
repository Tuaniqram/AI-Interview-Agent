import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { marketplaceService } from '../../services/marketplaceService';
import { candidateService } from '../../services/candidateService';
import { LoadingSpinner } from '../../components/shared/LoadingSpinner';
import { EmptyState } from '../../components/shared/EmptyState';
import { BookmarkButton } from '../../components/candidate/BookmarkButton';
import { ArrowLeft, Clock, Globe } from 'lucide-react';
import type { OrgListing, PublicInterview } from '../../types/marketplace';

export default function OrgProfile() {
  const { slug } = useParams<{ slug: string }>();
  const [org, setOrg] = useState<OrgListing | null>(null);
  const [interviews, setInterviews] = useState<PublicInterview[]>([]);
  const [savedIds, setSavedIds] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!slug) return;
    setLoading(true);
    Promise.all([
      marketplaceService.getOrgProfile(slug),
      candidateService.getSavedListings().catch(() => [] as any[]),
    ]).then(([data, saved]) => {
      setOrg(data.org);
      setInterviews(data.interviews);
      setSavedIds(new Set(saved.map((s: any) => s.id)));
    }).catch(console.error)
    .finally(() => setLoading(false));
  }, [slug]);

  if (loading) return <LoadingSpinner message="Loading organization..." />;
  if (!org) return <EmptyState title="Organization not found" />;

  return (
    <div className="space-y-8">
      <Link
        to="/opportunity-hub"
        className="inline-flex items-center gap-1.5 text-sm text-secondary hover:text-primary transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to opportunities
      </Link>

      <div className="rounded-2xl bg-gradient-to-br from-[#7C3AED]/5 to-[#A78BFA]/5 border border-[#7C3AED]/10 p-6 sm:p-8">
        <div className="flex items-start gap-5">
          <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-[#7C3AED] to-[#A78BFA] flex items-center justify-center shrink-0 text-white font-bold text-2xl">
            {org.name.charAt(0).toUpperCase()}
          </div>
          <div className="min-w-0">
            <h1 className="text-2xl font-bold text-primary font-heading">{org.name}</h1>
            {org.description && (
              <p className="text-secondary mt-1.5 max-w-2xl">{org.description}</p>
            )}
            <div className="flex items-center gap-4 mt-3">
              {org.website && (
                <a href={org.website} target="_blank" rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-sm text-[#7C3AED] hover:text-[#6D28D9] transition-colors">
                  <Globe className="w-3.5 h-3.5" />
                  {new URL(org.website).hostname}
                </a>
              )}
              <span className="flex items-center gap-1.5 text-sm text-muted">
                <Clock className="w-3.5 h-3.5" />
                {interviews.length} open interview{interviews.length !== 1 ? 's' : ''}
              </span>
            </div>
          </div>
        </div>
      </div>

      <section>
          <h2 className="text-lg font-semibold text-primary mb-4 font-heading">
          Open Positions ({interviews.length})
        </h2>
        {interviews.length === 0 ? (
          <EmptyState title="No open positions right now" description="Check back later for new opportunities" />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {interviews.map((interview) => {
              const skills = interview.skills_required?.split(',').map(s => s.trim()).filter(Boolean) || [];
              const isExpired = interview.expires_at ? new Date(interview.expires_at) < new Date() : false;
              const daysUntil = interview.expires_at
                ? Math.ceil((new Date(interview.expires_at).getTime() - Date.now()) / 86400000)
                : null;

              return (
                <div key={interview.id} className="relative p-5 rounded-xl bg-[var(--bg-section)] border border-[var(--border-color)] hover:border-[#7C3AED]/40 hover:shadow-lg hover:shadow-[#7C3AED]/5 transition-all group">
                  <div className="absolute top-3 right-3">
                    <BookmarkButton
                      listingId={Number(interview.id)}
                      initiallySaved={savedIds.has(Number(interview.id))}
                      onToggle={(s) => {
                        const id = Number(interview.id);
                        if (s) savedIds.add(id);
                        else savedIds.delete(id);
                      }}
                    />
                  </div>
                  <Link to={`/opportunity-hub/interviews/${interview.id}`}>
                    <h3 className="font-semibold text-primary group-hover:text-[#7C3AED] transition-colors font-heading">{interview.title}</h3>
                  {interview.department_name && (
                    <p className="text-xs text-muted mt-0.5">{interview.department_name}</p>
                  )}
                  {interview.description && (
                    <p className="text-sm text-secondary mt-1.5 line-clamp-2">{interview.description}</p>
                  )}
                  <div className="flex items-center gap-2 flex-wrap mt-3">
                    <span className="text-xs px-2.5 py-1 rounded-full bg-[#7C3AED]/10 text-[#7C3AED] font-medium">
                      {interview.interview_mode}
                    </span>
                    {skills.slice(0, 3).map(skill => (
                      <span key={skill} className="text-xs px-2.5 py-1 rounded-full bg-[var(--bg-page)] text-secondary border border-[var(--border-color)]">
                        {skill}
                      </span>
                    ))}
                    {skills.length > 3 && (
                      <span className="text-xs text-muted">+{skills.length - 3} more</span>
                    )}
                    {isExpired ? (
                      <span className="text-xs px-2.5 py-1 rounded-full bg-red-500/15 text-red-500 font-medium">Expired</span>
                    ) : daysUntil !== null && daysUntil <= 7 ? (
                      <span className="text-xs px-2.5 py-1 rounded-full bg-amber-500/15 text-amber-500 font-medium flex items-center gap-1">
                        <Clock className="w-3 h-3" /> {daysUntil}d left
                      </span>
                    ) : null}
                  </div>
                  </Link>
                  </div>
                );
              })}
          </div>
        )}
      </section>
    </div>
  );
}
