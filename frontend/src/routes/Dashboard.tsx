import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Play, AlertCircle } from 'lucide-react';
import { departmentService } from '../services/departmentService';
import { PageHeader } from '../components/shared/PageHeader';
import { StatRow } from '../components/dashboard/StatRow';
import { RecentSessions } from '../components/dashboard/RecentSessions';
import { ScoreDistribution } from '../components/dashboard/ScoreDistribution';
import type { DashboardMetrics, RecentSessionSummary } from '../types/dashboard';

export function Dashboard() {
  const navigate = useNavigate();
  const [metrics, setMetrics] = useState<DashboardMetrics>({ totalDepartments: 0, totalSessions: 0, activeSessions: 0, averageScore: null });
  const [loading, setLoading] = useState(true);
  const [sessions, setSessions] = useState<RecentSessionSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const departments = await departmentService.listDepartments();
        if (cancelled) return;

        setMetrics(prev => ({
          ...prev,
          totalDepartments: departments.length,
        }));

        const scoreData: number[] = [];
        const sessionRows: RecentSessionSummary[] = [];

        const sessionResults = await Promise.allSettled(
          departments.slice(0, 5).map(c => departmentService.listSessions(c.id))
        );
        if (cancelled) return;
        sessionResults.forEach((result, i) => {
          if (result.status === 'fulfilled') {
            for (const s of result.value) {
              sessionRows.push({
                session_id: s.id,
                job_role: s.job_role,
                status: s.status || '',
                final_score: s.final_score,
                started_at: s.started_at || '',
                department_name: departments[i].name,
              });
              if (s.final_score !== null) scoreData.push(s.final_score);
            }
          }
        });

        setSessions(sessionRows.sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime()));
        setMetrics({
          totalDepartments: departments.length,
          totalSessions: sessionRows.length,
          activeSessions: sessionRows.filter(s => s.status === 'active' || s.status === 'in_progress').length,
          averageScore: scoreData.length > 0 ? scoreData.reduce((a, b) => a + b, 0) / scoreData.length : null,
        });
      } catch {
        if (!cancelled) setError('Failed to load dashboard data. Please try again.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, []);

  return (
    <div>
      <PageHeader
        title="Dashboard"
        description="Overview of your AI Interview platform"
      />

      {error && (
        <div className="mb-6 flex items-center gap-3 px-4 py-3 rounded-lg bg-error-bg text-error">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span className="text-sm">{error}</span>
        </div>
      )}

      <StatRow
        totalDepartments={metrics.totalDepartments}
        totalSessions={metrics.totalSessions}
        activeSessions={metrics.activeSessions}
        averageScore={metrics.averageScore}
        loading={loading}
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RecentSessions
          sessions={sessions}
          loading={loading}
          emptyAction={
            <button
              onClick={() => navigate('/new-interview')}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-inverse bg-action-primary rounded-lg hover:bg-action-primary-hover transition-colors"
            >
              <Play className="w-4 h-4" />
              Start Interview
            </button>
          }
        />

        <ScoreDistribution
          data={[
            { label: 'Overall', score: metrics.averageScore },
          ]}
          loading={loading}
        />
      </div>
    </div>
  );
}
