import { useNavigate } from 'react-router-dom';
import { useEffect, useState, useMemo } from 'react';
import { ListChecks, AlertCircle, Keyboard, Mic, Bot } from 'lucide-react';
import { orgContentService, type SessionRecord } from '../services/orgContentService';
import { useOrg } from '../contexts/OrgContext';
import { PageHeader } from '../components/shared/PageHeader';
import { Card } from '../components/shared/Card';
import { EmptyState } from '../components/shared/EmptyState';
import { TableSkeleton } from '../components/shared/Skeleton';
import { DataTable, Column } from '../components/shared/DataTable';
import { StatusBadge } from '../components/shared/StatusBadge';
import { ScoreDisplay } from '../components/shared/ScoreDisplay';

export function Sessions() {
  const navigate = useNavigate();
  const { activeOrg } = useOrg();
  const [sessions, setSessions] = useState<SessionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!activeOrg?.id) return;
    const orgId = activeOrg.id;
    let cancelled = false;

    async function load() {
      try {
        const data = await orgContentService.listSessions(orgId);
        if (!cancelled) {
          setSessions([...data].sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime()));
        }
      } catch {
        if (!cancelled) setError('Failed to load sessions. Please try again.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, [activeOrg?.id]);

  const modeIcon = (m?: string) => {
    if (m === 'typing') return <Keyboard size={14} className="inline" />;
    if (m === 'voice') return <Mic size={14} className="inline" />;
    if (m === 'avatar') return <Bot size={14} className="inline" />;
    return <span className="text-xs">-</span>;
  };

  const columns = useMemo<Column<SessionRecord>[]>(() => [
    { key: 'job_role', header: 'Role', render: s => <span className="font-medium">{s.job_role}</span> },
    { key: 'interaction_mode', header: 'Mode', render: s => (
      <span className="inline-flex items-center gap-1.5 text-secondary">{modeIcon(s.interaction_mode)} {s.interaction_mode ? s.interaction_mode.charAt(0).toUpperCase() + s.interaction_mode.slice(1) : '-'}</span>
    ) },
    { key: 'status', header: 'Status', render: s => <StatusBadge status={s.status} /> },
    { key: 'final_score', header: 'Score', render: s => <ScoreDisplay score={s.final_score} size="inline" /> },
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
      <PageHeader title="Sessions" description="Every interview in your organization, newest first. Open a finished one to read its report." />

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
        <Card padding="none" className="overflow-hidden">
          <DataTable columns={columns} data={sessions} keyField="id" onRowClick={handleRowClick} />
        </Card>
      )}
    </div>
  );
}
