import { useEffect, useState } from 'react';
import { adminService } from '../../services/adminService';
import { PageHeader } from '../../components/shared/PageHeader';
import { SearchInput } from '../../components/shared/SearchInput';
import { LoadingSpinner } from '../../components/shared/LoadingSpinner';
import { EmptyState } from '../../components/shared/EmptyState';
import type { AdminUser } from '../../types/admin';

export default function UserManagement() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    setLoading(true);
    adminService.listUsers(search || undefined)
      .then(setUsers)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [search]);

  if (loading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      <PageHeader title="Users" description="Manage all platform users" />
      <SearchInput value={search} onChange={setSearch} placeholder="Search users..." />
      {users.length === 0 ? (
        <EmptyState title="No users found" />
      ) : (
        <div className="overflow-hidden rounded-xl border border-[var(--border-color)]">
          <table className="w-full">
            <thead>
              <tr className="bg-[var(--bg-section)]">
                <th className="text-left px-4 py-3 text-sm font-medium text-[var(--text-secondary)]">Name</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-[var(--text-secondary)]">Email</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-[var(--text-secondary)]">Role</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-[var(--text-secondary)]">Status</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-[var(--text-secondary)]">Joined</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-color)]">
              {users.map((user) => (
                <tr key={user.id} className="hover:bg-[var(--bg-section)]/50">
                  <td className="px-4 py-3 text-sm text-[var(--text-primary)]">{user.name}</td>
                  <td className="px-4 py-3 text-sm text-[var(--text-secondary)]">{user.email}</td>
                  <td className="px-4 py-3">
                    {user.is_admin && (
                      <span className="text-xs px-2 py-1 rounded-full bg-purple-100 dark:bg-purple-900/20 text-purple-600">
                        Admin
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`text-xs px-2 py-1 rounded-full font-medium ${
                        user.is_active
                          ? 'bg-green-100 dark:bg-green-900/20 text-green-600'
                          : 'bg-gray-100 dark:bg-gray-900/20 text-gray-600'
                      }`}
                    >
                      {user.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-[var(--text-secondary)]">
                    {user.created_at ? new Date(user.created_at).toLocaleDateString() : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
