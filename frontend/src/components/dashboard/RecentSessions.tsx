import { useNavigate } from 'react-router-dom';
import { StatusBadge } from '../shared/StatusBadge';
import { ScoreDisplay } from '../shared/ScoreDisplay';
import { Card } from '../shared/Card';
import { EmptyState } from '../shared/EmptyState';
import { TableSkeleton } from '../shared/Skeleton';
import { ListChecks } from 'lucide-react';

interface SessionRow {
  session_id: string;
  candidate_id?: string;
  job_role: string;
  status: string;
  final_score: number | null;
  started_at: string;
  interview_mode?: string;
}

interface RecentSessionsProps {
  sessions: SessionRow[];
  loading?: boolean;
  emptyAction?: React.ReactNode;
}

export function RecentSessions({ sessions, loading, emptyAction }: RecentSessionsProps) {
  const navigate = useNavigate();

  if (loading) return <Card><TableSkeleton rows={4} /></Card>;

  if (sessions.length === 0) {
    return (
      <Card>
        <EmptyState
          icon={<ListChecks className="w-8 h-8" />}
          title="No sessions yet"
          description="Start your first interview to see results here."
          action={emptyAction}
        />
      </Card>
    );
  }

  return (
    <Card padding="sm">
      <div className="text-sm font-medium text-primary px-2 pt-2 pb-3">Recent Sessions</div>
      <div className="divide-y divide-divider">
        {sessions.slice(0, 5).map(s => (
          <div
            key={s.session_id}
            onClick={() => navigate(`/interview/${s.session_id}`)}
            className="flex items-center gap-4 px-2 py-3 cursor-pointer hover:bg-hover rounded-lg transition-colors"
          >
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-primary truncate">
                {s.candidate_id || 'Anonymous'} · {s.job_role}
              </div>
              <div className="text-xs text-muted mt-0.5">
                {s.started_at ? new Date(s.started_at).toLocaleDateString() : '—'}
              </div>
            </div>
            <span className="text-xs text-muted">{s.interview_mode === 'typing' ? '⌨' : s.interview_mode === 'voice' ? '🎤' : s.interview_mode === 'avatar' ? '🤖' : ''}</span>
            <StatusBadge status={s.status} />
            <ScoreDisplay score={s.final_score} size="sm" showLabel={false} />
          </div>
        ))}
      </div>
    </Card>
  );
}
