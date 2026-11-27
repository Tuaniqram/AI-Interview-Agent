import { useEffect, useState } from 'react';
import { adminService } from '../../services/adminService';
import { PageHeader } from '../../components/shared/PageHeader';
import { SearchInput } from '../../components/shared/SearchInput';
import { ContentSkeleton } from '../../components/shared/ContentSkeleton';
import { EmptyState } from '../../components/shared/EmptyState';
import { useToast } from '../../components/shared/Toast';
import type { AdminUser } from '../../types/admin';

export default function UserManagement() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const toast = useToast();

  useEffect(() => {
    setLoading(true);
    adminService.listUsers(search || undefined)
      .then(setUsers)
      .catch(() => toast.error('Failed to load users'))
      .finally(() => setLoading(false));
  }, [search]);

  if (loading) return <ContentSkeleton />;

  return (
    <div className="space-y-6">
      <PageHeader title="Users" description="Every account on the platform, with its organization and role." />
      <SearchInput className="max-w-sm" value={search} onChange={setSearch} placeholder="Search users by name or email" />
      {users.length === 0 ? (
        <EmptyState title="No users found" />
      ) : (
        <div className="overflow-hidden rounded-xl border border-border bg-section">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border bg-page">
                  <th className="text-left px-4 py-3 text-xs font-medium text-secondary">Name</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-secondary">Email</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-secondary">Organization</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-secondary">Role</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-secondary">Status</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-secondary">Joined</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {users.map((user) => (
                  <tr key={user.id} className="hover:bg-hover/50 transition-colors">
                    <td className="px-4 py-3 text-sm font-medium text-primary">{user.name}</td>
                    <td className="px-4 py-3 text-sm text-secondary">{user.email}</td>
                    <td className="px-4 py-3 text-sm text-secondary">{user.org_name || '-'}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`text-xs px-2 py-1 rounded-full font-medium ${
                          user.is_admin
                            ? 'bg-action-primary/10 text-action-primary'
                            : 'bg-input text-secondary'
                        }`}
                      >
                        {user.is_admin ? 'Admin' : 'Owner'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`text-xs px-2 py-1 rounded-full font-medium ${
                          user.is_active
                            ? 'bg-success-bg text-success-text'
                            : 'bg-input text-muted'
                        }`}
                      >
                        {user.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-secondary">
                      {user.created_at ? new Date(user.created_at).toLocaleDateString() : '-'}
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
