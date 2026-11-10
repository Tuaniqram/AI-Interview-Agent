import { useNavigate } from 'react-router-dom';
import { useMemo } from 'react';
import { Keyboard, Mic, Bot } from 'lucide-react';
import { DataTable, Column } from '../shared/DataTable';
import { StatusBadge } from '../shared/StatusBadge';
import { ScoreDisplay } from '../shared/ScoreDisplay';

interface SessionRecord {
  id: string;
  job_role: string;
  status: string;
  final_score: number | null;
  started_at: string;
  interaction_mode?: string;
}

export function InterviewHistoryTable({ sessions }: { sessions: SessionRecord[] }) {
  const navigate = useNavigate();

  const modeIcon = (m?: string) => {
    if (m === 'typing') return <Keyboard size={14} className="inline" />;
    if (m === 'voice') return <Mic size={14} className="inline" />;
    if (m === 'avatar') return <Bot size={14} className="inline" />;
    return <span className="text-xs">—</span>;
  };

  const columns = useMemo<Column<SessionRecord>[]>(() => [
    { key: 'job_role', header: 'Role' },
    { key: 'interaction_mode', header: 'Mode', render: s => (
      <span className="text-xs">{modeIcon(s.interaction_mode)} {s.interaction_mode ? s.interaction_mode.charAt(0).toUpperCase() + s.interaction_mode.slice(1) : '—'}</span>
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
