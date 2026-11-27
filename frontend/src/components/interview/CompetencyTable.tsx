import { Card } from '../shared/Card';
import { FlatSurface } from '../shared/FlatSurface';
import { humanizePhase } from '../../routes/interview/shared';

interface CompetencyTableProps {
  summary: Record<string, { average_score: number; evidence_count: number; gap: number }>;
  /** A plain bordered surface (no glass, no shadow) for marketing pages. */
  flat?: boolean;
}

function barTone(score: number): string {
  if (score >= 7) return 'bg-success';
  if (score >= 5) return 'bg-warning';
  return 'bg-error';
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
      <h3 className="text-sm font-semibold text-primary mb-3">Competencies assessed</h3>
      <table className="w-full text-[13px]">
        <thead>
          <tr className="text-left text-tertiary border-b border-border">
            <th scope="col" className="pb-2 pr-3 font-medium">Competency</th>
            <th scope="col" className="pb-2 pr-3 font-medium w-[45%]">Average score</th>
            <th scope="col" className="pb-2 text-right font-medium">Answers</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--divider)]">
          {rows.map(r => (
            <tr key={r.id}>
              <td className="py-2.5 pr-3 text-primary">{humanizePhase(r.id)}</td>
              <td className="py-2.5 pr-3">
                <div className="flex items-center gap-3">
                  <span className="text-primary font-medium w-8 tabular">{r.score.toFixed(1)}</span>
                  <div className="h-1.5 flex-1 rounded-full bg-hover overflow-hidden" aria-hidden="true">
                    <div
                      className={`h-full rounded-full ${barTone(r.score)}`}
                      style={{ width: `${Math.max(0, Math.min(100, r.score * 10))}%` }}
                    />
                  </div>
                </div>
              </td>
              <td className="py-2.5 text-right text-secondary tabular">{r.evidence}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Surface>
  );
}
