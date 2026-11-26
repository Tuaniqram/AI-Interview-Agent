import { useEffect, useState } from 'react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Download } from 'lucide-react';
import { PageHeader } from '../components/shared/PageHeader';
import { Card } from '../components/shared/Card';
import { StatStrip } from '../components/shared/StatStrip';
import { Skeleton } from '../components/shared/Skeleton';
import { Button } from '../components/shared/Button';
import {
  analyticsService,
  type OverviewData as Overview,
  type TrendPoint,
  type DistributionPoint,
  type ItRoleData,
  type RoleData,
} from '../services/analyticsService';

/*
 * Every chart here is one series in the accent colour: the title names it, so there is no legend.
 * Two measures never share a chart (no second y-axis): score and volume are separate charts.
 */
const AXIS_TICK = { fontSize: 11, fill: 'var(--text-tertiary)' };
const TOOLTIP = {
  contentStyle: { background: 'var(--bg-elevated)', border: '1px solid var(--border-color)', borderRadius: 8, fontSize: 12, color: 'var(--text-primary)' },
  labelStyle: { color: 'var(--text-secondary)' },
  cursor: { fill: 'var(--bg-hover)', stroke: 'var(--border-strong)' },
};

function ChartCard({ title, text, empty, children }: { title: string; text: string; empty: boolean; children: React.ReactNode }) {
  return (
    <Card padding="lg">
      <h2 className="text-sm font-semibold text-primary">{title}</h2>
      <p className="text-[13px] text-tertiary mt-0.5 mb-4">{text}</p>
      {empty ? <p className="text-[13px] text-tertiary py-10 text-center">No finished interviews yet.</p> : children}
    </Card>
  );
}

/** A ranked list with bars: easier to read than a pie, and the labels never collide. */
function BarList({ rows }: { rows: { label: string; value: number; score: number | null }[] }) {
  const max = Math.max(1, ...rows.map(r => r.value));
  return (
    <ul className="space-y-3">
      {rows.map(r => (
        <li key={r.label} className="group" title={`${r.label}: ${r.value} ${r.value === 1 ? 'interview' : 'interviews'}${r.score != null ? `, average ${r.score.toFixed(1)}` : ''}`}>
          <div className="flex items-baseline justify-between gap-3 text-[13px]">
            <span className="text-primary truncate">{r.label}</span>
            <span className="text-secondary tabular shrink-0">
              {r.value}
              {r.score != null && <span className="text-tertiary"> / avg {r.score.toFixed(1)}</span>}
            </span>
          </div>
          <div className="mt-1.5 h-2 rounded-full bg-hover overflow-hidden" aria-hidden>
            <div className="h-full rounded-full bg-action-primary group-hover:bg-action-primary-hover" style={{ width: `${(r.value / max) * 100}%` }} />
          </div>
        </li>
      ))}
    </ul>
  );
}

export function Analytics() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [trend, setTrend] = useState<TrendPoint[]>([]);
  const [distribution, setDistribution] = useState<DistributionPoint[]>([]);
  const [byItRole, setByItRole] = useState<ItRoleData[]>([]);
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
          analyticsService.getSessionsByItRole(),
          analyticsService.getSessionsByRole(),
        ]);
        if (cancelled) return;
        if (o.status === 'fulfilled') setOverview(o.value);
        if (t.status === 'fulfilled') setTrend(t.value);
        if (d.status === 'fulfilled') setDistribution(d.value);
        if (c.status === 'fulfilled') setByItRole(c.value);
        if (r.status === 'fulfilled') setByRole(r.value);
      } catch {} finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, []);

  function exportCSV() {
    if (trend.length === 0) return;
    const headers = ['Date', 'Avg Score', 'Count'];
    const rows = trend.map(p => `${p.date},${p.avg_score},${p.count}`);
    const csv = [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'analytics-trend.csv';
    a.click();
    URL.revokeObjectURL(url);
  }

  const header = (
    <PageHeader
      title="Analytics"
      description="How your interviews are going: scores over time, how they spread, and which roles they were for."
      actions={
        <Button variant="secondary" icon={<Download />} onClick={exportCSV} disabled={trend.length === 0}>
          Export CSV
        </Button>
      }
    />
  );

  if (loading) {
    return (
      <div className="space-y-6">
        {header}
        <StatStrip loading stats={[{ label: 'Interviews', value: '' }, { label: 'Average score', value: '' }, { label: 'Completion rate', value: '' }, { label: 'Open roles', value: '' }]} />
        <div className="grid gap-4 lg:grid-cols-2">
          <Skeleton variant="rect" height="18rem" />
          <Skeleton variant="rect" height="18rem" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {header}

      <StatStrip stats={[
        { label: 'Interviews', value: String(overview?.total_sessions ?? 0), to: '/sessions' },
        { label: 'Average score', value: overview?.average_score != null ? overview.average_score.toFixed(1) : '—', hint: overview?.average_score != null ? '/ 10' : undefined },
        { label: 'Completion rate', value: `${overview?.completion_rate ?? 0}%` },
        { label: 'Open roles', value: String(overview?.total_it_roles ?? 0), to: '/org/company' },
      ]} />

      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard title="Average score" text="Per day, out of 10." empty={trend.length === 0}>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={trend} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
              <CartesianGrid vertical={false} stroke="var(--divider)" />
              <XAxis dataKey="date" tick={AXIS_TICK} tickLine={false} axisLine={{ stroke: 'var(--border-color)' }} />
              <YAxis domain={[0, 10]} ticks={[0, 2, 4, 6, 8, 10]} tick={AXIS_TICK} tickLine={false} axisLine={false} />
              <Tooltip {...TOOLTIP} formatter={(v) => [Number(v).toFixed(1), 'Average score']} />
              <Line type="monotone" dataKey="avg_score" stroke="var(--action-primary)" strokeWidth={2} dot={{ r: 4, strokeWidth: 2, fill: 'var(--bg-section)' }} activeDot={{ r: 5 }} name="Average score" />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Interviews per day" text="Finished interviews, by the day they started." empty={trend.length === 0}>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={trend} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
              <CartesianGrid vertical={false} stroke="var(--divider)" />
              <XAxis dataKey="date" tick={AXIS_TICK} tickLine={false} axisLine={{ stroke: 'var(--border-color)' }} />
              <YAxis allowDecimals={false} tick={AXIS_TICK} tickLine={false} axisLine={false} />
              <Tooltip {...TOOLTIP} formatter={(v) => [String(v), 'Interviews']} />
              <Bar dataKey="count" fill="var(--action-primary)" radius={[4, 4, 0, 0]} maxBarSize={40} name="Interviews" />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Score spread" text="How many interviews landed in each score band." empty={distribution.every(d => d.count === 0)}>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={distribution} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
              <CartesianGrid vertical={false} stroke="var(--divider)" />
              <XAxis dataKey="range" tick={AXIS_TICK} tickLine={false} axisLine={{ stroke: 'var(--border-color)' }} />
              <YAxis allowDecimals={false} tick={AXIS_TICK} tickLine={false} axisLine={false} />
              <Tooltip {...TOOLTIP} formatter={(v) => [String(v), 'Interviews']} labelFormatter={l => `Score ${l}`} />
              <Bar dataKey="count" fill="var(--action-primary)" radius={[4, 4, 0, 0]} maxBarSize={48} name="Interviews" />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="By role" text="Interviews per job role, with the average score." empty={byRole.length === 0 && byItRole.length === 0}>
          <BarList rows={(byRole.length > 0
            ? byRole.map(r => ({ label: r.job_role, value: r.count, score: r.avg_score }))
            : byItRole.map(r => ({ label: r.name, value: r.session_count, score: r.avg_score }))
          ).sort((a, b) => b.value - a.value).slice(0, 8)} />
          {byItRole.length > 0 && byRole.length > 0 && (
            <>
              <h3 className="text-[13px] font-medium text-primary mt-6 mb-3">By IT role</h3>
              <BarList rows={byItRole.map(r => ({ label: r.name, value: r.session_count, score: r.avg_score }))
                .sort((a, b) => b.value - a.value).slice(0, 8)} />
            </>
          )}
        </ChartCard>
      </div>
    </div>
  );
}
