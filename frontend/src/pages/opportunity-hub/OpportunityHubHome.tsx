import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Building2, ChevronRight, Search } from 'lucide-react';
import { marketplaceService } from '../../services/marketplaceService';
import { EmptyState } from '../../components/shared/EmptyState';
import { HubBanner, HubBody } from '../../components/opportunity-hub/HubBanner';
import { useDebounce } from '../../hooks/useDebounce';
import type { OrgListing } from '../../types/marketplace';

const CLOSING = [
  { value: '', label: 'Any time' },
  { value: '7d', label: 'Closing in 7 days' },
  { value: '30d', label: 'Closing in 30 days' },
];

function OrgInitial({ name }: { name: string }) {
  return (
    <span className="w-9 h-9 rounded-lg border border-border bg-subtle flex items-center justify-center text-sm font-semibold text-secondary shrink-0" aria-hidden>
      {name.charAt(0).toUpperCase()}
    </span>
  );
}

export default function OpportunityHubHome() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [orgs, setOrgs] = useState<OrgListing[]>([]);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);

  // The box is local so typing stays smooth; the URL follows once typing pauses.
  const [query, setQuery] = useState(searchParams.get('search') || '');
  const search = useDebounce(query.trim(), 300);
  const closing = searchParams.get('expiry') || '';

  useEffect(() => {
    const params = new URLSearchParams(searchParams);
    if (search) params.set('search', search); else params.delete('search');
    setSearchParams(params, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setFailed(false);
    const params: { search?: string; expiry?: string } = {};
    if (search) params.search = search;
    if (closing) params.expiry = closing;
    marketplaceService.listOrganizations(Object.keys(params).length ? params : undefined)
      .then(data => { if (!cancelled) setOrgs(data); })
      .catch(() => { if (!cancelled) { setOrgs([]); setFailed(true); } })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [search, closing]);

  const setClosing = (v: string) => {
    const params = new URLSearchParams(searchParams);
    if (v) params.set('expiry', v); else params.delete('expiry');
    setSearchParams(params, { replace: true });
  };

  const filtered = !!search || !!closing;
  const total = orgs.reduce((n, o) => n + o.interview_count, 0);

  return (
    <>
      <HubBanner
        title="Open interviews"
        aside={
          <div className="relative w-full md:w-80">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#5b6b66] pointer-events-none" />
            <input
              type="search"
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Search organizations"
              aria-label="Search organizations by name"
              className="w-full h-10 pl-9 pr-3 text-sm bg-white text-[#14201c] rounded-lg border border-transparent shadow-sm focus:outline-none focus:ring-[3px] focus:ring-white/40 placeholder:text-[#6b7a75]"
            />
          </div>
        }
      >
        Organizations hiring through AI interviews. Open one to see its roles, apply with your CV, and take the interview if they invite you.
      </HubBanner>

      <HubBody>
      <div className="flex items-center justify-between gap-3 mb-4 flex-wrap">
        <h2 className="text-sm font-semibold text-primary">Organizations</h2>
        <div role="radiogroup" aria-label="Closing date" className="inline-flex p-0.5 rounded-md bg-hover border border-border self-start">
          {CLOSING.map(o => (
            <button
              key={o.value}
              role="radio"
              aria-checked={closing === o.value}
              onClick={() => setClosing(o.value)}
              className={`h-7 px-2.5 rounded text-xs font-medium whitespace-nowrap transition-colors ${
                closing === o.value ? 'bg-section text-primary shadow-sm' : 'text-secondary hover:text-primary'
              }`}
            >
              {o.label}
            </button>
          ))}
        </div>
      </div>

      {!loading && !failed && orgs.length > 0 && (
        <p className="text-xs text-tertiary mb-2 tabular" aria-live="polite">
          {orgs.length} {orgs.length === 1 ? 'organization' : 'organizations'}, {total} open {total === 1 ? 'role' : 'roles'}
        </p>
      )}

      {loading ? (
        <ul className="rounded-xl border border-border bg-section divide-y divide-[var(--divider)] overflow-hidden" aria-busy>
          {[0, 1, 2, 3].map(i => (
            <li key={i} className="flex items-center gap-4 px-4 py-3.5 animate-pulse">
              <span className="w-9 h-9 rounded-lg bg-hover" />
              <span className="flex-1 space-y-2">
                <span className="block h-3.5 w-40 rounded bg-hover" />
                <span className="block h-3 w-3/4 rounded bg-hover" />
              </span>
            </li>
          ))}
        </ul>
      ) : failed ? (
        <div className="rounded-xl border border-border bg-section">
          <EmptyState title="Could not load the list" description="Check your connection and reload the page." />
        </div>
      ) : orgs.length === 0 ? (
        <div className="rounded-xl border border-border bg-section">
          <EmptyState
            icon={<Building2 />}
            title={filtered ? 'Nothing matches' : 'No open interviews right now'}
            description={filtered
              ? search ? `No organization named like "${search}" has an open role${closing ? ' closing in that window' : ''}.` : 'No open role closes in that window.'
              : 'Organizations appear here when they open a role to the public.'}
            action={filtered ? (
              <button onClick={() => { setQuery(''); setSearchParams({}, { replace: true }); }} className="text-[13px] font-medium text-action-primary hover:underline">
                Clear the search
              </button>
            ) : undefined}
          />
        </div>
      ) : (
        <ul className="rounded-xl border border-border bg-section divide-y divide-[var(--divider)] overflow-hidden">
          {orgs.map(org => (
            <li key={org.id}>
              <Link
                to={`/opportunity-hub/organizations/${org.slug}`}
                className="group flex items-center gap-4 px-4 py-3.5 hover:bg-subtle transition-colors"
              >
                <OrgInitial name={org.name} />
                <span className="flex-1 min-w-0">
                  <span className="block text-sm font-medium text-primary truncate">{org.name}</span>
                  {org.description && <span className="block text-[13px] text-secondary truncate">{org.description}</span>}
                </span>
                <span className="text-xs text-tertiary tabular whitespace-nowrap">
                  {org.interview_count} open {org.interview_count === 1 ? 'role' : 'roles'}
                </span>
                <ChevronRight className="w-4 h-4 text-tertiary group-hover:text-primary shrink-0" />
              </Link>
            </li>
          ))}
        </ul>
      )}
      </HubBody>
    </>
  );
}
