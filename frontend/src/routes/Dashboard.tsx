import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Play } from 'lucide-react';
import { apiClient } from '../services/apiClient';
import { PageHeader } from '../components/shared/PageHeader';
import { StatRow } from '../components/dashboard/StatRow';
import { RecentSessions } from '../components/dashboard/RecentSessions';
import { ScoreDistribution } from '../components/dashboard/ScoreDistribution';
import type { DashboardMetrics, RecentSessionSummary } from '../types/dashboard';

export function Dashboard() {
  const navigate = useNavigate();
  const [metrics, setMetrics] = useState<DashboardMetrics>({ totalCompanies: 0, totalSessions: 0, activeSessions: 0, averageScore: null });
  const [loading, setLoading] = useState(true);
  const [sessions, setSessions] = useState<RecentSessionSummary[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const companies = await apiClient.get<Array<{ id: number; name: string }>>('/companies/');
        if (cancelled) return;

        setMetrics(prev => ({
          ...prev,
          totalCompanies: companies.length,
        }));

        const scoreData: number[] = [];
        const sessionRows: RecentSessionSummary[] = [];

        for (const c of companies.slice(0, 5)) {
          try {
            const companySessions = await apiClient.get<RecentSessionSummary[]>(`/companies/${c.id}/sessions`);
            if (cancelled) return;
            for (const s of companySessions) {
              sessionRows.push({ ...s, company_name: c.name });
              if (s.final_score !== null) scoreData.push(s.final_score);
            }
          } catch {
            // endpoint may not exist yet
          }
        }

        setSessions(sessionRows.sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime()));
        setMetrics({
          totalCompanies: companies.length,
          totalSessions: sessionRows.length,
          activeSessions: sessionRows.filter(s => s.status === 'active' || s.status === 'in_progress').length,
          averageScore: scoreData.length > 0 ? scoreData.reduce((a, b) => a + b, 0) / scoreData.length : null,
        });
      } catch {
        // silently handle - UI shows zeros
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

      <StatRow
        totalCompanies={metrics.totalCompanies}
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
            { label: 'Technical', score: sessions.length > 0 ? sessions.reduce((a, b) => a + (b.final_score || 0), 0) / sessions.length : null },
            { label: 'Communication', score: sessions.length > 0 ? sessions.reduce((a, b) => a + (b.final_score || 0), 0) / sessions.length : null },
            { label: 'Overall', score: metrics.averageScore },
          ]}
          loading={loading}
        />
      </div>
    </div>
  );
}
