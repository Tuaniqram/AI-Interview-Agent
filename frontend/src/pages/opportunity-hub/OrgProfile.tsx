import { useEffect, useState } from 'react';
import { useParams, Link, useLocation } from 'react-router-dom';
import { ChevronRight, Briefcase } from 'lucide-react';
import { HubBanner, HubBody } from '../../components/opportunity-hub/HubBanner';
import { marketplaceService } from '../../services/marketplaceService';
import { ContentSkeleton } from '../../components/shared/ContentSkeleton';
import { EmptyState } from '../../components/shared/EmptyState';
import { closingInfo, modeLabel, splitSkills } from '../../components/opportunity-hub/listing';
import type { OrgListing, PublicInterview } from '../../types/marketplace';

const hostname = (url: string) => {
  try { return new URL(url).hostname.replace(/^www\./, ''); } catch { return url; }
};

export default function OrgProfile() {
  const { slug } = useParams<{ slug: string }>();
  const { pathname } = useLocation();
  const [org, setOrg] = useState<OrgListing | null>(null);
  const [interviews, setInterviews] = useState<PublicInterview[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!slug) return;
    setLoading(true);
    marketplaceService.getOrgProfile(slug)
      .then(data => { setOrg(data.org); setInterviews(data.interviews); })
      .catch(() => setOrg(null))
      .finally(() => setLoading(false));
  }, [slug]);

  const back = { to: '/opportunity-hub', label: 'All organizations' };

  if (loading) return <HubBody><ContentSkeleton /></HubBody>;
  if (!org) {
    return (
      <>
        <HubBanner back={back} title="Organization not found" />
        <HubBody>
          <div className="rounded-xl border border-border bg-section">
            <EmptyState title="Nothing to show" description="It may have stopped listing roles, or the link is out of date." />
          </div>
        </HubBody>
      </>
    );
  }

  return (
    <>
      <HubBanner
        back={back}
        leading={
          <span className="w-14 h-14 rounded-xl bg-white/10 border border-white/15 flex items-center justify-center text-xl font-semibold shrink-0" aria-hidden>
            {org.name.charAt(0).toUpperCase()}
          </span>
        }
        eyebrow={org.website ? (
          <a href={org.website} target="_blank" rel="noopener noreferrer" className="text-white/75 hover:text-white underline-offset-2 hover:underline">
            {hostname(org.website)}
          </a>
        ) : undefined}
        title={org.name}
        aside={
          <p className="text-sm text-white/75 tabular">
            <span className="text-2xl font-semibold text-white mr-1.5">{interviews.length}</span>
            open {interviews.length === 1 ? 'role' : 'roles'}
          </p>
        }
      >
        {org.description}
      </HubBanner>

      <HubBody>
      <section aria-labelledby="roles-heading">
        <div className="flex items-baseline justify-between mb-3">
          <h2 id="roles-heading" className="text-sm font-semibold text-primary">Open roles</h2>
          <span className="text-xs text-tertiary tabular">{interviews.length}</span>
        </div>

        {interviews.length === 0 ? (
          <div className="rounded-xl border border-border bg-section">
            <EmptyState icon={<Briefcase />} title="No open roles right now" description="This organization has nothing open to the public at the moment." />
          </div>
        ) : (
          <ul className="rounded-xl border border-border bg-section divide-y divide-[var(--divider)] overflow-hidden">
            {interviews.map(interview => {
              const skills = splitSkills(interview.skills_required);
              const closing = closingInfo(interview.expires_at);
              return (
                <li key={interview.id}>
                  <Link
                    to={`/opportunity-hub/interviews/${interview.id}`}
                    state={{ from: pathname, orgName: org.name }}
                    className="group flex items-center gap-4 px-4 py-3.5 hover:bg-subtle transition-colors"
                  >
                    <span className="flex-1 min-w-0">
                      <span className="block text-sm font-medium text-primary truncate">{interview.title}</span>
                      <span className="block text-xs text-tertiary mt-0.5">
                        {modeLabel(interview.interview_mode)}
                        {closing && (
                          <>
                            <span className="mx-1.5 text-border-strong" aria-hidden>/</span>
                            <span className={closing.tone === 'soon' ? 'text-warning-text' : closing.tone === 'closed' ? 'text-error-text' : ''}>{closing.text}</span>
                          </>
                        )}
                      </span>
                      {interview.description && <span className="block text-[13px] text-secondary mt-1 line-clamp-1">{interview.description}</span>}
                    </span>
                    {skills.length > 0 && (
                      <span className="hidden md:flex items-center gap-1 shrink-0">
                        {skills.slice(0, 3).map(s => (
                          <span key={s} className="text-[11px] h-5 px-1.5 inline-flex items-center rounded border border-border text-secondary">{s}</span>
                        ))}
                        {skills.length > 3 && <span className="text-[11px] text-tertiary">+{skills.length - 3}</span>}
                      </span>
                    )}
                    <ChevronRight className="w-4 h-4 text-tertiary group-hover:text-primary shrink-0" />
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </section>
      </HubBody>
    </>
  );
}
