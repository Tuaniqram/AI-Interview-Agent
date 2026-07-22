import { useNavigate } from 'react-router-dom';
import { useMemo } from 'react';
import { DataTable, Column } from '../shared/DataTable';
import { StatusBadge } from '../shared/StatusBadge';
import { ScoreDisplay } from '../shared/ScoreDisplay';

interface SessionRecord {
  id: string;
  candidate_id?: string;
  job_role: string;
  status: string;
  final_score: number | null;
  started_at: string;
  interview_mode?: string;
}

export function InterviewHistoryTable({ sessions }: { sessions: SessionRecord[] }) {
  const navigate = useNavigate();

  const modeIcon = (m?: string) => {
    if (m === 'typing') return '⌨';
    if (m === 'voice') return '🎤';
    if (m === 'avatar') return '🤖';
    return '—';
  };

  const columns = useMemo<Column<SessionRecord>[]>(() => [
    { key: 'candidate_id', header: 'Candidate', render: s => s.candidate_id || 'Anonymous' },
    { key: 'job_role', header: 'Role' },
    { key: 'interview_mode', header: 'Mode', render: s => (
      <span className="text-xs">{modeIcon(s.interview_mode)} {s.interview_mode ? s.interview_mode.charAt(0).toUpperCase() + s.interview_mode.slice(1) : '—'}</span>
    ) },
    { key: 'status', header: 'Status', render: s => <StatusBadge status={s.status} /> },
    { key: 'final_score', header: 'Score', render: s => <ScoreDisplay score={s.final_score} size="sm" showLabel={false} /> },
    { key: 'started_at', header: 'Date', render: s => new Date(s.started_at).toLocaleDateString(), className: 'text-secondary' },
  ], []);

  return (
    <DataTable
      columns={columns}
      data={sessions}
      keyField="id"
      onRowClick={s => navigate(s.status === 'completed' ? `/interview/${s.id}/report` : `/interview/${s.id}`)}
      emptyMessage="No interview sessions yet"
    />
  );
}
