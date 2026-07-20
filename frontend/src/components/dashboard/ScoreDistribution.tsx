import { Card } from '../shared/Card';

interface ScoreData {
  label: string;
  score: number | null;
}

interface ScoreDistributionProps {
  data: ScoreData[];
  loading?: boolean;
}

export function ScoreDistribution({ data, loading }: ScoreDistributionProps) {
  if (loading) {
    return (
      <Card>
        <div className="animate-pulse space-y-3">
          <div className="h-3 bg-hover rounded w-1/3 mb-4" />
          {[1,2,3].map(i => (
            <div key={i} className="flex items-center gap-3">
              <div className="h-3 bg-hover rounded w-16" />
              <div className="flex-1 h-4 bg-hover rounded" />
              <div className="h-3 bg-hover rounded w-8" />
            </div>
          ))}
        </div>
      </Card>
    );
  }

  if (data.length === 0) return null;

  return (
    <Card>
      <h3 className="text-sm font-medium text-primary mb-4">Score Overview</h3>
      <div className="space-y-3">
        {data.map(d => {
          const pct = d.score !== null ? Math.round((d.score / 10) * 100) : 0;
          const color = pct >= 70 ? 'bg-success' : pct >= 50 ? 'bg-warning' : 'bg-error';
          return (
            <div key={d.label} className="flex items-center gap-3">
              <span className="text-xs text-secondary w-20 shrink-0">{d.label}</span>
              <div className="flex-1 h-2 bg-hover rounded-full overflow-hidden">
                <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${pct}%` }} />
              </div>
              <span className="text-xs font-medium text-secondary w-8 text-end">
                {d.score !== null ? d.score.toFixed(1) : '—'}
              </span>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
