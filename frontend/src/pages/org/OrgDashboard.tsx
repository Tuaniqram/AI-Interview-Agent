import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useOrg } from '../../contexts/OrgContext';
import { PageHeader } from '../../components/shared/PageHeader';
import { MetricCard } from '../../components/shared/MetricCard';
import { Card } from '../../components/shared/Card';
import { CardSkeleton } from '../../components/shared/Skeleton';
import { analyticsService, type OverviewData } from '../../services/analyticsService';
import { marketplaceService } from '../../services/marketplaceService';
import { Users, ListChecks, Store, TrendingUp, Target, Building2, ArrowRight } from 'lucide-react';

export default function OrgDashboard() {
  const { activeOrg, members } = useOrg();
  const navigate = useNavigate();
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [listingCount, setListingCount] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!activeOrg?.id) return;
    setLoading(true);
    Promise.allSettled([
      analyticsService.getOverview(),
      marketplaceService.listOrgListings(activeOrg.id),
    ]).then(([o, l]) => {
      if (o.status === 'fulfilled') setOverview(o.value);
      if (l.status === 'fulfilled') setListingCount(l.value.length);
    }).finally(() => setLoading(false));
  }, [activeOrg?.id]);

  if (loading) {
    return (
      <div className="space-y-6">
        <PageHeader title={activeOrg?.name || 'Organization'} description="Loading..." />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[1,2,3,4].map(i => <CardSkeleton key={i} />)}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={activeOrg?.name || 'Organization'}
        description="Overview of your organization"
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="Members" value={members.length} icon={<Users className="w-4 h-4" />}
          onClick={() => navigate('/org/members')} />
        <MetricCard label="Total Sessions" value={overview?.total_sessions ?? 0} icon={<ListChecks className="w-4 h-4" />}
          onClick={() => navigate('/sessions')} />
        <MetricCard label="Active Sessions" value={overview?.active_sessions ?? 0} icon={<Target className="w-4 h-4" />} />
        <MetricCard label="Avg Score" value={overview?.average_score != null ? overview.average_score.toFixed(1) : '—'} icon={<TrendingUp className="w-4 h-4" />} />
        <MetricCard label="Departments" value={overview?.total_departments ?? 0} icon={<Building2 className="w-4 h-4" />}
          onClick={() => navigate('/departments')} />
        <MetricCard label="Completion Rate" value={`${overview?.completion_rate ?? 0}%`} icon={<Target className="w-4 h-4" />} />
        <MetricCard label="Marketplace Listings" value={listingCount} icon={<Store className="w-4 h-4" />}
          onClick={() => navigate('/departments')} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card hover onClick={() => navigate('/org/members')}>
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-medium text-primary flex items-center gap-2"><Users className="w-4 h-4" /> Team</h3>
              <p className="text-xs text-muted mt-1">Manage members and roles</p>
            </div>
            <ArrowRight className="w-4 h-4 text-muted" />
          </div>
        </Card>
        <Card hover onClick={() => navigate('/departments')}>
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-medium text-primary flex items-center gap-2"><Building2 className="w-4 h-4" /> Departments</h3>
              <p className="text-xs text-muted mt-1">Configure interview settings</p>
            </div>
            <ArrowRight className="w-4 h-4 text-muted" />
          </div>
        </Card>
        <Card hover onClick={() => navigate('/settings')}>
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-medium text-primary flex items-center gap-2"><TrendingUp className="w-4 h-4" /> Settings</h3>
              <p className="text-xs text-muted mt-1">Organization profile and config</p>
            </div>
            <ArrowRight className="w-4 h-4 text-muted" />
          </div>
        </Card>
      </div>
    </div>
  );
}
