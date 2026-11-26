import { useEffect, useState } from 'react';
import { adminService } from '../../services/adminService';
import { PageHeader } from '../../components/shared/PageHeader';
import { SearchInput } from '../../components/shared/SearchInput';
import { ContentSkeleton } from '../../components/shared/ContentSkeleton';
import { EmptyState } from '../../components/shared/EmptyState';
import { Button } from '../../components/shared/Button';
import { useToast } from '../../components/shared/Toast';
import type { AdminOrg } from '../../types/admin';

export default function OrgManagement() {
  const [orgs, setOrgs] = useState<AdminOrg[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const toast = useToast();

  const fetchOrgs = () => {
    setLoading(true);
    adminService.listOrganizations(search || undefined)
      .then(setOrgs)
      .catch(() => toast.error('Failed to load organizations'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchOrgs(); }, [search]);

  const handleToggleSuspend = async (orgId: string) => {
    try {
      await adminService.toggleSuspend(orgId);
      toast.success('Organization status updated');
      fetchOrgs();
    } catch {
      toast.error('Failed to update organization status');
    }
  };

  if (loading) return <ContentSkeleton />;

  return (
    <div className="space-y-6">
      <PageHeader title="Organizations" description="Every organization on the platform." />
      <SearchInput className="max-w-sm" value={search} onChange={setSearch} placeholder="Search organizations" />
      {orgs.length === 0 ? (
        <EmptyState title="No organizations found" />
      ) : (
        <div className="overflow-hidden rounded-xl border border-border bg-section">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border bg-page">
                  <th className="text-left px-4 py-3 text-xs font-medium text-secondary">Organization</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-secondary">Owner</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-secondary">Interviews</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-secondary">Status</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-secondary">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {orgs.map((org) => (
                  <tr key={org.id} className="hover:bg-hover/50 transition-colors">
                    <td className="px-4 py-3">
                      <h3 className="text-sm font-medium text-primary">{org.name}</h3>
                      <p className="text-xs text-muted">{org.slug}</p>
                    </td>
                    <td className="px-4 py-3">
                      {org.owner_name ? (
                        <>
                          <p className="text-sm text-primary">{org.owner_name}</p>
                          <p className="text-xs text-muted">{org.owner_email}</p>
                        </>
                      ) : (
                        <span className="text-sm text-muted">No owner</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-secondary">{org.interview_count}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`text-xs px-2 py-1 rounded-full font-medium ${
                          org.is_active
                            ? 'bg-success-bg text-success-text'
                            : 'bg-error-bg text-error-text'
                        }`}
                      >
                        {org.is_active ? 'Active' : 'Suspended'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Button
                        variant="secondary"
                        className={org.is_active ? '!text-error-text' : ''}
                        size="sm"
                        onClick={() => handleToggleSuspend(org.id)}
                      >
                        {org.is_active ? 'Suspend' : 'Reactivate'}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
