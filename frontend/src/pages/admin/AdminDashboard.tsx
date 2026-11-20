import { useEffect, useState } from 'react';
import { adminService } from '../../services/adminService';
import { MetricCard } from '../../components/shared/MetricCard';
import { PageHeader } from '../../components/shared/PageHeader';
import { ContentSkeleton } from '../../components/shared/ContentSkeleton';
import { useToast } from '../../components/shared/Toast';
import type { PlatformStats } from '../../types/admin';

export default function AdminDashboard() {
  const [stats, setStats] = useState<PlatformStats | null>(null);
  const [loading, setLoading] = useState(true);
  const toast = useToast();

  useEffect(() => {
    adminService.getStats()
      .then(setStats)
      .catch(() => toast.error('Failed to load admin stats'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <ContentSkeleton />;

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
