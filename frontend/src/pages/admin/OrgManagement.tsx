import { useEffect, useState } from 'react';
import { adminService } from '../../services/adminService';
import { PageHeader } from '../../components/shared/PageHeader';
import { SearchInput } from '../../components/shared/SearchInput';
import { LoadingSpinner } from '../../components/shared/LoadingSpinner';
import { EmptyState } from '../../components/shared/EmptyState';
import { Button } from '../../components/shared/Button';
import type { AdminOrg } from '../../types/admin';

export default function OrgManagement() {
  const [orgs, setOrgs] = useState<AdminOrg[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  const fetchOrgs = () => {
    setLoading(true);
    adminService.listOrganizations(search || undefined)
      .then(setOrgs)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchOrgs(); }, [search]);

  const handleToggleSuspend = async (orgId: string) => {
    await adminService.toggleSuspend(orgId);
    fetchOrgs();
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      <PageHeader title="Organizations" description="Manage all organizations" />
      <SearchInput value={search} onChange={setSearch} placeholder="Search organizations..." />
      {orgs.length === 0 ? (
        <EmptyState title="No organizations found" />
      ) : (
        <div className="space-y-3">
          {orgs.map((org) => (
            <div
              key={org.id}
              className="p-4 rounded-xl bg-[var(--bg-section)] border border-[var(--border-color)] flex items-center justify-between"
            >
              <div>
                <h3 className="font-semibold text-[var(--text-primary)]">{org.name}</h3>
                <p className="text-sm text-[var(--text-secondary)]">
                  {org.member_count} members · {org.interview_count} interviews
                </p>
              </div>
              <div className="flex items-center gap-3">
                <span
                  className={`text-xs px-2 py-1 rounded-full font-medium ${
                    org.is_active
                      ? 'bg-green-100 dark:bg-green-900/20 text-green-600'
                      : 'bg-red-100 dark:bg-red-900/20 text-red-600'
                  }`}
                >
                  {org.is_active ? 'Active' : 'Suspended'}
                </span>
                <Button
                  variant={org.is_active ? 'danger' : 'primary'}
                  size="sm"
                  onClick={() => handleToggleSuspend(org.id)}
                >
                  {org.is_active ? 'Suspend' : 'Reactivate'}
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
