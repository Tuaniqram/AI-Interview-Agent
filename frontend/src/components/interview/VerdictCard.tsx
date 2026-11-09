import { AlertCircle, ArrowRight } from 'lucide-react';
import { Card } from '../shared/Card';
import type { FinalDecision } from '../../types/interview';

/** Plain-English label and tone for each point on the engine's seven-point decision scale. */
const VERDICTS: Record<string, { label: string; tone: 'success' | 'warning' | 'error' | 'muted' }> = {
  strong_hire: { label: 'Strong hire', tone: 'success' },
  hire: { label: 'Hire', tone: 'success' },
  lean_hire: { label: 'Lean hire', tone: 'success' },
  insufficient_evidence: { label: 'Not enough evidence', tone: 'warning' },
  lean_no_hire: { label: 'Lean no hire', tone: 'error' },
  no_hire: { label: 'No hire', tone: 'error' },
  strong_no_hire: { label: 'Strong no hire', tone: 'error' },
};

const TONE_TEXT: Record<string, string> = {
  success: 'text-success-text',
  warning: 'text-warning-text',
  error: 'text-error-text',
  muted: 'text-secondary',
};

export function verdictLabel(verdict?: string | null): string {
  if (!verdict) return '';
  return VERDICTS[verdict]?.label ?? verdict.replace(/_/g, ' ');
}

const sentence = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);

interface VerdictCardProps {
  decision: FinalDecision;
  evidenceCount?: number;
}

/**
 * The recommendation and the reasons behind it. The verdict is computed by fixed rules from the scored
 * answers; each rule that lowered it from its starting point is listed with its reason, so a recruiter can
 * check the result instead of taking it on trust.
 */
export function VerdictCard({ decision, evidenceCount }: VerdictCardProps) {
  const tone = VERDICTS[decision.verdict]?.tone ?? 'muted';
  const lowered = !!decision.draft_verdict && decision.draft_verdict !== decision.verdict;

  return (
    <Card className="mb-6" data-testid="verdict-card">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs text-muted mb-1">Recommendation</p>
          <p className={`text-2xl font-bold ${TONE_TEXT[tone]}`}>{verdictLabel(decision.verdict)}</p>
        </div>
        <dl className="flex gap-6 text-right">
          {decision.score != null && (
            <div>
              <dt className="text-xs text-muted">Decision score</dt>
              <dd className="font-mono text-lg font-semibold text-primary">
                {Number(decision.score).toFixed(1)}<span className="text-xs text-muted"> / 10</span>
              </dd>
            </div>
          )}
          {decision.confidence != null && (
            <div>
              <dt className="text-xs text-muted">Confidence</dt>
              <dd className="font-mono text-lg font-semibold text-primary">{Math.round(Number(decision.confidence) * 100)}%</dd>
            </div>
          )}
          {evidenceCount != null && (
            <div>
              <dt className="text-xs text-muted">Evidence items</dt>
              <dd className="font-mono text-lg font-semibold text-primary">{evidenceCount}</dd>
            </div>
          )}
        </dl>
      </div>

      {decision.flag_review && (
        <div
          className="mt-4 flex items-start gap-2 rounded-md border border-warning/40 bg-warning-bg px-3 py-2 text-xs text-warning-text"
          role="note"
        >
          <AlertCircle className="w-4 h-4 shrink-0 mt-px" />
          <span>
            A person should review this result before acting on it
            {decision.contradiction_count > 0
              ? ` (${decision.contradiction_count} inconsistent answer${decision.contradiction_count === 1 ? '' : 's'} found).`
              : '.'}
          </span>
        </div>
      )}

      {decision.rationale && <p className="mt-4 text-sm text-secondary leading-relaxed">{decision.rationale}</p>}

      {lowered && decision.adjustments.length > 0 && (
        <div className="mt-4 border-t border-border pt-4">
          <h3 className="text-xs font-medium text-primary mb-2">Why it was lowered from {verdictLabel(decision.draft_verdict)}</h3>
          <ul className="space-y-1.5">
            {decision.adjustments.map((a, i) => (
              <li key={i} className="text-xs text-secondary flex items-start gap-2">
                <ArrowRight className="w-3.5 h-3.5 shrink-0 mt-px text-muted" />
                <span>
                  <span className="font-mono text-muted">
                    {verdictLabel(a.from)} → {verdictLabel(a.to)}
                  </span>
                  {' · '}
                  {a.reason}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {decision.next_steps.length > 0 && (
        <div className="mt-4 border-t border-border pt-4">
          <h3 className="text-xs font-medium text-primary mb-2">Suggested next steps</h3>
          <ul className="list-disc pl-4 space-y-1">
            {decision.next_steps.map((step, i) => (
              <li key={i} className="text-xs text-secondary">{sentence(step)}</li>
            ))}
          </ul>
        </div>
      )}

      <p className="mt-4 text-[11px] text-muted">
        The recommendation comes from fixed scoring rules applied to the answers below. The wording above is written
        by an AI; it does not choose the verdict.
      </p>
    </Card>
  );
}
