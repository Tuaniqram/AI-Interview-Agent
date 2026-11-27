import { Link } from 'react-router-dom';
import { Skeleton } from './Skeleton';

export interface Stat { label: string; value: string; hint?: string; to?: string }

const COLS: Record<number, string> = {
  3: 'grid-cols-1 sm:grid-cols-3',
  4: 'grid-cols-2 lg:grid-cols-4',
  6: 'grid-cols-2 md:grid-cols-3 xl:grid-cols-6',
};

/** A row of figures in one bordered strip: read left to right, no card per number. */
export function StatStrip({ stats, loading = false }: { stats: Stat[]; loading?: boolean }) {
  return (
    <div className={`grid ${COLS[stats.length] ?? 'grid-cols-2 lg:grid-cols-4'} gap-px rounded-xl border border-border bg-border overflow-hidden`}>
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
