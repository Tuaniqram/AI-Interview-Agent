import { useEffect, useState } from 'react';
import { adminService } from '../../services/adminService';
import { MetricCard } from '../../components/shared/MetricCard';
import { PageHeader } from '../../components/shared/PageHeader';
import { LoadingSpinner } from '../../components/shared/LoadingSpinner';
import type { PlatformStats } from '../../types/admin';

export default function AdminDashboard() {
  const [stats, setStats] = useState<PlatformStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    adminService.getStats()
      .then(setStats)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      <PageHeader title="Admin Dashboard" description="Platform-wide statistics" />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="Organizations" value={stats?.total_orgs ?? 0} />
        <MetricCard label="Users" value={stats?.total_users ?? 0} />
        <MetricCard label="Total Interviews" value={stats?.total_interviews ?? 0} />
        <MetricCard label="Active Sessions" value={stats?.active_sessions ?? 0} />
      </div>
    </div>
  );
}
