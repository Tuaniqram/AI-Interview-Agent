import { useEffect, useState } from 'react';
import { marketplaceService } from '../../services/marketplaceService';
import { OrgCard } from '../../components/marketplace/OrgCard';
import { SearchInput } from '../../components/shared/SearchInput';
import { LoadingSpinner } from '../../components/shared/LoadingSpinner';
import { EmptyState } from '../../components/shared/EmptyState';
import { useDebounce } from '../../hooks/useDebounce';
import type { OrgListing } from '../../types/marketplace';

export default function MarketplaceHome() {
  const [orgs, setOrgs] = useState<OrgListing[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const debouncedSearch = useDebounce(search, 300);

  useEffect(() => {
    setLoading(true);
    marketplaceService.listOrganizations(debouncedSearch ? { search: debouncedSearch } : undefined)
      .then(setOrgs)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [debouncedSearch]);

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--text-primary)]">Interview Marketplace</h1>
        <p className="text-[var(--text-secondary)] mt-1">
          Browse organizations offering public interviews
        </p>
      </div>

      <SearchInput
        value={search}
        onChange={setSearch}
        placeholder="Search organizations..."
      />

      {loading ? (
        <LoadingSpinner message="Loading organizations..." />
      ) : orgs.length === 0 ? (
        <EmptyState
          title="No organizations found"
          description={search ? 'Try a different search term' : 'No organizations are currently listed'}
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {orgs.map((org) => (
            <OrgCard key={org.id} org={org} />
          ))}
        </div>
      )}
    </div>
  );
}
