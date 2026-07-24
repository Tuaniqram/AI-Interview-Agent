import { useEffect, useState } from 'react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { PageHeader } from '../components/shared/PageHeader';
import { Card } from '../components/shared/Card';
import { MetricCard } from '../components/shared/MetricCard';
import { CardSkeleton } from '../components/shared/Skeleton';
import { Building2, ListChecks, TrendingUp, Target } from 'lucide-react';
import {
  analyticsService,
  type OverviewData as Overview,
  type TrendPoint,
  type DistributionPoint,
  type DepartmentData,
  type RoleData,
} from '../services/analyticsService';

const COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];

export function Analytics() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [trend, setTrend] = useState<TrendPoint[]>([]);
  const [distribution, setDistribution] = useState<DistributionPoint[]>([]);
  const [byDepartment, setByDepartment] = useState<DepartmentData[]>([]);
  const [byRole, setByRole] = useState<RoleData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const [o, t, d, c, r] = await Promise.allSettled([
          analyticsService.getOverview(),
          analyticsService.getScoreTrend(),
          analyticsService.getScoreDistribution(),
          analyticsService.getSessionsByDepartment(),
          analyticsService.getSessionsByRole(),
        ]);
        if (cancelled) return;
        if (o.status === 'fulfilled') setOverview(o.value);
        if (t.status === 'fulfilled') setTrend(t.value);
        if (d.status === 'fulfilled') setDistribution(d.value);
        if (c.status === 'fulfilled') setByDepartment(c.value);
        if (r.status === 'fulfilled') setByRole(r.value);
      } catch {} finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return (
      <div>
        <PageHeader title="Analytics" description="Interview performance insights" />
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 mb-6">
          {[1,2,3,4].map(i => <CardSkeleton key={i} />)}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <CardSkeleton />
          <CardSkeleton />
        </div>
      </div>
    );
  }

  return (
    <div>
      <PageHeader title="Analytics" description="Interview performance insights" />

      {/* Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 mb-6">
        <MetricCard label="Total Sessions" value={overview?.total_sessions ?? 0} icon={<ListChecks className="w-4 h-4" />} />
        <MetricCard label="Avg Score" value={overview?.average_score != null ? overview.average_score.toFixed(1) : '—'} icon={<TrendingUp className="w-4 h-4" />} />
        <MetricCard label="Completion Rate" value={`${overview?.completion_rate ?? 0}%`} icon={<Target className="w-4 h-4" />} />
        <MetricCard label="Departments" value={overview?.total_departments ?? 0} icon={<Building2 className="w-4 h-4" />} />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        {/* Score Trend */}
        <Card>
          <h3 className="text-sm font-medium text-primary mb-4">Score Trend</h3>
          {trend.length === 0 ? (
            <p className="text-xs text-muted text-center py-8">No score data yet</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--divider)" />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <YAxis domain={[0, 10]} tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <Tooltip contentStyle={{ background: 'var(--bg-section)', borderRadius: 8, fontSize: 12 }} />
                <Line type="monotone" dataKey="avg_score" stroke="#6366f1" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </Card>

        {/* Score Distribution */}
        <Card>
          <h3 className="text-sm font-medium text-primary mb-4">Score Distribution</h3>
          {distribution.every(d => d.count === 0) ? (
            <p className="text-xs text-muted text-center py-8">No score data yet</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={distribution}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--divider)" />
                <XAxis dataKey="range" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <YAxis tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <Tooltip contentStyle={{ background: 'var(--bg-section)', borderRadius: 8, fontSize: 12 }} />
                <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>
      </div>

      {/* Second Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Sessions by Department */}
        <Card>
          <h3 className="text-sm font-medium text-primary mb-4">Sessions by Department</h3>
          {byDepartment.length === 0 ? (
            <p className="text-xs text-muted text-center py-8">No data yet</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={byDepartment.slice(0, 8)} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="var(--divider)" />
                <XAxis type="number" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <YAxis dataKey="name" type="category" width={100} tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <Tooltip contentStyle={{ background: 'var(--bg-section)', borderRadius: 8, fontSize: 12 }} />
                <Bar dataKey="session_count" fill="#22c55e" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>

        {/* Sessions by Role */}
        <Card>
          <h3 className="text-sm font-medium text-primary mb-4">Sessions by Role</h3>
          {byRole.length === 0 ? (
            <p className="text-xs text-muted text-center py-8">No data yet</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={byRole.slice(0, 6)} dataKey="count" nameKey="job_role" cx="50%" cy="50%" outerRadius={80} labelLine={false} style={{ fontSize: 10 }}>
                  {byRole.slice(0, 6).map((_entry, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={{ background: 'var(--bg-section)', borderRadius: 8, fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </Card>
      </div>
    </div>
  );
}
