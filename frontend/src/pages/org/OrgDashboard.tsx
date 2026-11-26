import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useOrg } from '../../contexts/OrgContext';
import { PageHeader } from '../../components/shared/PageHeader';
import { Card } from '../../components/shared/Card';
import { Button } from '../../components/shared/Button';
import { Skeleton } from '../../components/shared/Skeleton';
import { DataTable, type Column } from '../../components/shared/DataTable';
import { StatusBadge } from '../../components/shared/StatusBadge';
import { ScoreDisplay } from '../../components/shared/ScoreDisplay';
import { EmptyState } from '../../components/shared/EmptyState';
import { analyticsService, type OverviewData } from '../../services/analyticsService';
import { marketplaceService } from '../../services/marketplaceService';
import { orgContentService, type SessionRecord } from '../../services/orgContentService';
import { Building2, ChevronRight, Inbox, ListChecks, Settings, Trophy } from 'lucide-react';
import { useToast } from '../../components/shared/Toast';

interface Stat { label: string; value: string; hint?: string; to?: string }

/** The figures as one strip: read left to right, no card per number. */
function StatStrip({ stats, loading }: { stats: Stat[]; loading: boolean }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-px rounded-xl border border-border bg-border overflow-hidden">
      {stats.map(s => {
        const body = (
          <>
            <p className="text-[13px] text-secondary truncate">{s.label}</p>
            {loading
              ? <Skeleton width="40%" height="1.75rem" className="mt-2" />
              : (
                <p className="mt-1 flex items-baseline gap-1">
                  <span className="text-2xl font-semibold tracking-[-0.02em] text-primary tabular">{s.value}</span>
                  {s.hint && <span className="text-[13px] text-tertiary">{s.hint}</span>}
                </p>
              )}
          </>
        );
        return s.to
          ? <Link key={s.label} to={s.to} className="bg-section px-4 py-3.5 hover:bg-subtle transition-colors">{body}</Link>
          : <div key={s.label} className="bg-section px-4 py-3.5">{body}</div>;
      })}
    </div>
  );
}

const SHORTCUTS = [
  { to: '/org/applications', icon: Inbox, title: 'Review applications', text: 'Applicants waiting for an invitation' },
  { to: '/org/candidates', icon: Trophy, title: 'Compare candidates', text: 'Ranked results by role' },
  { to: '/org/company', icon: Building2, title: 'Company and roles', text: 'Documents, listings and interview settings' },
  { to: '/settings', icon: Settings, title: 'Organization settings', text: 'Profile, members and defaults' },
];

export default function OrgDashboard() {
  const { activeOrg } = useOrg();
  const navigate = useNavigate();
  const toast = useToast();
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [listingCount, setListingCount] = useState(0);
  const [sessions, setSessions] = useState<SessionRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!activeOrg?.id) return;
    setLoading(true);
    Promise.allSettled([
      analyticsService.getOverview(),
      marketplaceService.listOrgListings(activeOrg.id),
      orgContentService.listSessions(activeOrg.id),
    ]).then(([o, l, s]) => {
      if (o.status === 'fulfilled') setOverview(o.value);
      else toast.error('Could not load the overview figures. Reload the page to try again.');
      if (l.status === 'fulfilled') setListingCount(l.value.length);
      if (s.status === 'fulfilled') {
        setSessions([...s.value].sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime()).slice(0, 6));
      }
    }).finally(() => setLoading(false));
  }, [activeOrg?.id]);

  const stats: Stat[] = [
    { label: 'Interviews', value: String(overview?.total_sessions ?? 0), to: '/sessions' },
    { label: 'In progress', value: String(overview?.active_sessions ?? 0) },
    { label: 'Average score', value: overview?.average_score != null ? overview.average_score.toFixed(1) : '—', hint: overview?.average_score != null ? '/ 10' : undefined },
    { label: 'Completion rate', value: `${overview?.completion_rate ?? 0}%` },
    { label: 'Open roles', value: String(overview?.total_it_roles ?? 0), to: '/org/company' },
    { label: 'Public listings', value: String(listingCount), to: '/org/company' },
  ];

  const columns = useMemo<Column<SessionRecord>[]>(() => [
    { key: 'job_role', header: 'Role', render: s => <span className="font-medium">{s.job_role}</span> },
    { key: 'status', header: 'Status', render: s => <StatusBadge status={s.status} /> },
    { key: 'final_score', header: 'Score', render: s => <ScoreDisplay score={s.final_score} size="inline" /> },
    {
      key: 'started_at', header: 'Started', className: 'text-secondary whitespace-nowrap',
      render: s => new Date(s.started_at).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }),
    },
  ], []);

  const openSession = (s: SessionRecord) =>
    navigate(s.status === 'completed' ? `/interview/${s.id}/report` : `/interview/${s.id}`);

  return (
    <div className="space-y-8">
      <PageHeader
        title={activeOrg?.name || 'Organization'}
        description="Your hiring at a glance: who was interviewed, how they did, and what needs you next."
        actions={<Button variant="secondary" icon={<ListChecks />} onClick={() => navigate('/sessions')}>All sessions</Button>}
      />

      <StatStrip stats={stats} loading={loading} />

      <div className="grid gap-6 lg:grid-cols-3">
        <section className="lg:col-span-2 min-w-0" aria-labelledby="recent-heading">
          <div className="flex items-center justify-between mb-3">
            <h2 id="recent-heading" className="text-sm font-semibold text-primary">Recent interviews</h2>
            {sessions.length > 0 && (
              <Link to="/sessions" className="text-[13px] text-secondary hover:text-primary">View all</Link>
            )}
          </div>
          <Card padding="none" className="overflow-hidden">
            {loading ? (
              <div className="p-4 space-y-3">{[0, 1, 2].map(i => <Skeleton key={i} height="1.25rem" />)}</div>
            ) : sessions.length === 0 ? (
              <EmptyState
                icon={<ListChecks />}
                title="No interviews yet"
                description="Invite an applicant or publish a listing. Finished interviews show up here with their score."
                action={<Button variant="secondary" onClick={() => navigate('/org/applications')}>Go to applications</Button>}
              />
            ) : (
              <DataTable columns={columns} data={sessions} keyField="id" onRowClick={openSession} />
            )}
          </Card>
        </section>

        <section aria-labelledby="next-heading">
          <h2 id="next-heading" className="text-sm font-semibold text-primary mb-3">Next steps</h2>
          <Card padding="none">
            <ul className="divide-y divide-[var(--divider)]">
              {SHORTCUTS.map(({ to, icon: Icon, title, text }) => (
                <li key={to}>
                  <Link to={to} className="group flex items-center gap-3 px-4 py-3 hover:bg-subtle transition-colors first:rounded-t-xl">
                    <span className="w-8 h-8 rounded-lg border border-border bg-subtle flex items-center justify-center text-secondary shrink-0">
                      <Icon className="w-4 h-4" />
                    </span>
                    <span className="flex-1 min-w-0">
                      <span className="block text-[13px] font-medium text-primary">{title}</span>
                      <span className="block text-xs text-tertiary truncate">{text}</span>
                    </span>
                    <ChevronRight className="w-4 h-4 text-tertiary group-hover:text-primary" />
                  </Link>
                </li>
              ))}
            </ul>
          </Card>
        </section>
      </div>
    </div>
  );
}
