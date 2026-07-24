import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { X } from 'lucide-react';
import { marketplaceService } from '../../services/marketplaceService';
import { EmptyState } from '../../components/shared/EmptyState';
import { HeroSection } from '../../components/opportunity-hub/HeroSection';
import { CategoryCard } from '../../components/opportunity-hub/CategoryCard';
import { OrgCard } from '../../components/opportunity-hub/OrgCard';
import { useDebounce } from '../../hooks/useDebounce';
import type { OrgListing } from '../../types/marketplace';

const CATEGORIES = [
  { name: 'Engineering', icon: 'engineering', keywords: ['engineer', 'developer', 'software', 'backend', 'frontend', 'full-stack', 'react', 'python', 'javascript', 'typescript', 'java', 'go', 'rust'] },
  { name: 'AI & ML', icon: 'machine-learning', keywords: ['machine learning', 'ai', 'data science', 'deep learning', 'nlp', 'computer vision', 'llm', 'ml'] },
  { name: 'Data', icon: 'data', keywords: ['data', 'analytics', 'database', 'sql', 'data engineer', 'data analyst'] },
  { name: 'Design', icon: 'design', keywords: ['design', 'ui', 'ux', 'figma', 'product design', 'graphic'] },
  { name: 'Product', icon: 'product', keywords: ['product', 'pm', 'product manager', 'product management'] },
  { name: 'Security', icon: 'security', keywords: ['security', 'cyber', 'infosec', 'security engineer'] },
  { name: 'Marketing', icon: 'marketing', keywords: ['marketing', 'growth', 'seo', 'content', 'social media'] },
  { name: 'Writing', icon: 'writing', keywords: ['writing', 'content', 'copywriting', 'technical writer'] },
];

export default function OpportunityHubHome() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [orgs, setOrgs] = useState<OrgListing[]>([]);
  const [loading, setLoading] = useState(true);

  const search = searchParams.get('search') || '';
  const activeModes = searchParams.get('modes')?.split(',').filter(Boolean) || [];
  const activeExpiry = searchParams.get('expiry') || '';

  const hasFilters = search || activeModes.length > 0 || activeExpiry;

  const debouncedSearch = useDebounce(search, 300);

  useEffect(() => {
    const params = new URLSearchParams(searchParams);
    if (debouncedSearch) params.set('search', debouncedSearch);
    else params.delete('search');
    if (searchParams.get('modes')) params.set('modes', searchParams.get('modes')!);
    if (searchParams.get('expiry')) params.set('expiry', searchParams.get('expiry')!);
    setSearchParams(params, { replace: true });
  }, [debouncedSearch]);

  useEffect(() => {
    setLoading(true);
    const apiParams: { search?: string; modes?: string; expiry?: string } = {};
    if (debouncedSearch) apiParams.search = debouncedSearch;
    if (activeModes.length) apiParams.modes = activeModes.join(',');
    if (activeExpiry && activeExpiry !== 'any') apiParams.expiry = activeExpiry;
    marketplaceService.listOrganizations(Object.keys(apiParams).length ? apiParams : undefined)
      .then(setOrgs)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [debouncedSearch, activeModes.join(','), activeExpiry]);

  const handleCategoryClick = (keywords: string[]) => {
    const params = new URLSearchParams(searchParams);
    params.set('search', keywords.join(' '));
    setSearchParams(params, { replace: true });
  };

  const clearFilter = (key: string) => {
    const params = new URLSearchParams(searchParams);
    params.delete(key);
    setSearchParams(params, { replace: true });
  };

  const clearAll = () => {
    setSearchParams({}, { replace: true });
  };

  const expiryLabel = activeExpiry === '7d' ? 'Within 7 days' : activeExpiry === '30d' ? 'Within 30 days' : '';

  return (
    <div className="space-y-6">
      <HeroSection
        search={search}
        onSearchChange={(v) => {
          const params = new URLSearchParams(searchParams);
          if (v) params.set('search', v);
          else params.delete('search');
          setSearchParams(params, { replace: true });
        }}
      />

      {hasFilters && (
        <div className="flex items-center gap-2 flex-wrap animate-fade-in">
          <span className="text-xs text-muted font-medium">Active filters:</span>
          {search && (
            <span className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-[#7C3AED]/10 text-[#7C3AED] font-medium">
              Search: “{search}”
              <button onClick={() => clearFilter('search')} className="hover:bg-[#7C3AED]/20 rounded-full p-0.5 -mr-0.5" aria-label="Clear search">
                <X className="w-3 h-3" />
              </button>
            </span>
          )}
          {activeModes.map(m => (
            <span key={m} className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-[#7C3AED]/10 text-[#7C3AED] font-medium">
              {m}
              <button onClick={() => {
                const next = activeModes.filter(x => x !== m);
                const params = new URLSearchParams(searchParams);
                if (next.length) params.set('modes', next.join(','));
                else params.delete('modes');
                setSearchParams(params, { replace: true });
              }} className="hover:bg-[#7C3AED]/20 rounded-full p-0.5 -mr-0.5" aria-label={`Remove ${m}`}>
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}
          {expiryLabel && (
            <span className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-[#7C3AED]/10 text-[#7C3AED] font-medium">
              {expiryLabel}
              <button onClick={() => clearFilter('expiry')} className="hover:bg-[#7C3AED]/20 rounded-full p-0.5 -mr-0.5" aria-label="Clear expiry">
                <X className="w-3 h-3" />
              </button>
            </span>
          )}
          <button onClick={clearAll} className="text-xs text-muted hover:text-secondary underline ml-1">
            Clear all
          </button>
        </div>
      )}

      {!hasFilters && orgs.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold text-primary mb-4 font-heading">Browse by Category</h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {CATEGORIES.map((cat, i) => {
              const count = orgs.filter(o =>
                o.description?.toLowerCase().includes(cat.keywords[0])
              ).length;
              if (count === 0) return null;
              return (
                <div key={cat.name} className={`animate-stagger animate-stagger-${Math.min(i + 1, 6)}`}>
                  <CategoryCard
                    name={cat.name}
                    icon={cat.icon}
                    count={count}
                    onClick={() => handleCategoryClick(cat.keywords)}
                  />
                </div>
              );
            })}
          </div>
        </section>
      )}

      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-primary font-heading">
            {search ? `Results for "${search}"` : hasFilters ? 'Filtered Results' : 'All Organizations'}
          </h2>
          <span className="text-xs text-muted">{orgs.length} found</span>
        </div>

        {loading ? (
          <div className="grid gap-4 sm:grid-cols-2">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="animate-pulse p-5 rounded-xl bg-section border border-border">
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 rounded-xl bg-hover" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 bg-hover rounded w-3/4" />
                    <div className="h-3 bg-hover rounded w-full" />
                    <div className="h-3 bg-hover rounded w-1/2" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : orgs.length === 0 ? (
          <div className="animate-fade-in">
            <EmptyState
              title="No opportunities found"
              description={hasFilters ? 'Try adjusting your filters' : 'No organizations are currently listed'}
            />
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {orgs.map((org, i) => (
              <div key={org.id} className={`animate-stagger animate-stagger-${Math.min(i + 1, 6)}`}>
                <OrgCard org={org} />
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
