import { Card } from '../shared/Card';
import { FlatSurface } from '../shared/FlatSurface';
import { humanizePhase } from '../../routes/interview/shared';

interface CompetencyTableProps {
  summary: Record<string, { average_score: number; evidence_count: number; gap: number }>;
  /** A plain bordered surface (no glass, no shadow) for marketing pages. */
  flat?: boolean;
}

/** One row per competency the interview assessed: the average score and how many answers back it. */
export function CompetencyTable({ summary, flat = false }: CompetencyTableProps) {
  const rows = Object.entries(summary)
    .map(([id, s]) => ({ id, score: Number(s.average_score) || 0, evidence: Number(s.evidence_count) || 0 }))
    .sort((a, b) => b.evidence - a.evidence || b.score - a.score);
  if (rows.length === 0) return null;

  const Surface = flat ? FlatSurface : Card;

  return (
    <Surface className="mb-6">
      <h3 className="text-sm font-medium text-primary mb-3">Competencies assessed</h3>
      <table className="w-full text-xs">
        <thead>
          <tr className="text-left text-muted border-b border-border">
            <th className="py-1.5 pr-3 font-medium">Competency</th>
            <th className="py-1.5 pr-3 font-medium w-40">Average score</th>
            <th className="py-1.5 text-right font-medium">Answers</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <tr key={r.id} className="border-b border-border last:border-0">
              <td className="py-2 pr-3 text-primary">{humanizePhase(r.id)}</td>
              <td className="py-2 pr-3">
                <div className="flex items-center gap-2">
                  <div className="h-1.5 flex-1 rounded-sm bg-section overflow-hidden" aria-hidden="true">
                    <div
                      className="h-full bg-[var(--action-primary)]"
                      style={{ width: `${Math.max(0, Math.min(100, r.score * 10))}%` }}
                    />
                  </div>
                  <span className="font-mono text-primary w-8 text-right">{r.score.toFixed(1)}</span>
                </div>
              </td>
              <td className="py-2 text-right font-mono text-secondary">{r.evidence}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Surface>
  );
}
