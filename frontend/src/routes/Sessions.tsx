import { useNavigate } from 'react-router-dom';
import { PageHeader } from '../components/shared/PageHeader';
import { Card } from '../components/shared/Card';
import { EmptyState } from '../components/shared/EmptyState';
import { TableSkeleton } from '../components/shared/Skeleton';
import { DataTable, Column } from '../components/shared/DataTable';
import { StatusBadge } from '../components/shared/StatusBadge';
import { ScoreDisplay } from '../components/shared/ScoreDisplay';
import { ListChecks, AlertCircle } from 'lucide-react';
import { useEffect, useState, useMemo } from 'react';
import { apiClient } from '../services/apiClient';

interface SessionRecord {
  id: string;
  candidate_id?: string;
  job_role: string;
  status: string;
  final_score: number | null;
  started_at: string;
  company_name?: string;
  interview_mode?: string;
}

export function Sessions() {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<SessionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const companies = await apiClient.get<Array<{ id: number; name: string }>>('/companies/');
        const all: SessionRecord[] = [];

        const sessionResults = await Promise.allSettled(
          companies.map(c => apiClient.get<SessionRecord[]>(`/companies/${c.id}/sessions`))
        );
        sessionResults.forEach((result, i) => {
          if (result.status === 'fulfilled') {
            for (const s of result.value) {
              all.push({ ...s, company_name: companies[i].name });
            }
          }
        });

        if (!cancelled) {
          setSessions(all.sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime()));
        }
      } catch {
        if (!cancelled) setError('Failed to load sessions. Please try again.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, []);

  const modeIcon = (m?: string) => {
    if (m === 'typing') return '⌨';
    if (m === 'voice') return '🎤';
    if (m === 'avatar') return '🤖';
    return '—';
  };

  const columns = useMemo<Column<SessionRecord>[]>(() => [
    { key: 'company_name', header: 'Company', render: s => s.company_name || '—' },
    { key: 'candidate_id', header: 'Candidate', render: s => s.candidate_id || 'Anonymous' },
    { key: 'job_role', header: 'Role' },
    { key: 'interview_mode', header: 'Mode', render: s => (
      <span className="text-xs">{modeIcon(s.interview_mode)} {s.interview_mode ? s.interview_mode.charAt(0).toUpperCase() + s.interview_mode.slice(1) : '—'}</span>
    ) },
    { key: 'status', header: 'Status', render: s => <StatusBadge status={s.status} /> },
    { key: 'final_score', header: 'Score', render: s => <ScoreDisplay score={s.final_score} size="sm" showLabel={false} /> },
    { key: 'started_at', header: 'Date', render: s => new Date(s.started_at).toLocaleDateString(), className: 'text-secondary' },
  ], []);

  const handleRowClick = (s: SessionRecord) => {
    if (s.status === 'completed') {
      navigate(`/interview/${s.id}/report`);
    } else {
      navigate(`/interview/${s.id}`);
    }
  };

  return (
    <div>
      <PageHeader title="Interview Sessions" description="All interview sessions across companies" />

      {error && (
        <div className="mb-6 flex items-center gap-3 px-4 py-3 rounded-lg bg-error-bg text-error">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span className="text-sm">{error}</span>
        </div>
      )}

      {loading ? (
        <Card><TableSkeleton rows={8} /></Card>
      ) : sessions.length === 0 ? (
        <Card>
          <EmptyState
            icon={<ListChecks className="w-8 h-8" />}
            title="No sessions found"
            description="Sessions will appear here once interviews are conducted."
          />
        </Card>
      ) : (
        <Card padding="sm">
          <DataTable columns={columns} data={sessions} keyField="id" onRowClick={handleRowClick} />
        </Card>
      )}
    </div>
  );
}
