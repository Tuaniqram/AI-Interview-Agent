import { MetricCard } from '../shared/MetricCard';
import { Building2, ListChecks, Activity, Brain } from 'lucide-react';

interface StatRowProps {
  totalCompanies: number;
  totalSessions: number;
  activeSessions: number;
  averageScore: number | null;
  loading?: boolean;
}

export function StatRow({ totalCompanies, totalSessions, activeSessions, averageScore, loading }: StatRowProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {[1,2,3,4].map(i => (
          <div key={i} className="bg-elevated rounded-xl p-4 animate-pulse">
            <div className="h-3 bg-hover rounded w-1/2 mb-3" />
            <div className="h-6 bg-hover rounded w-1/3" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      <MetricCard label="Companies" value={totalCompanies} icon={<Building2 className="w-4 h-4" />} />
      <MetricCard label="Total Sessions" value={totalSessions} icon={<ListChecks className="w-4 h-4" />} />
      <MetricCard label="Active" value={activeSessions} icon={<Activity className="w-4 h-4" />} />
      <MetricCard
        label="Avg Score"
        value={averageScore !== null ? averageScore.toFixed(1) : '—'}
        icon={<Brain className="w-4 h-4" />}
        trend={averageScore !== null && averageScore >= 6 ? 'up' : averageScore !== null ? 'down' : undefined}
      />
    </div>
  );
}
