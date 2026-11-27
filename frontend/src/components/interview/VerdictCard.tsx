import { AlertCircle, ChevronRight } from 'lucide-react';
import { FlatSurface } from '../shared/FlatSurface';
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

/** The band at the top of the card carries the verdict's tone; the rest of the card stays neutral. */
const TONE_BAND: Record<string, string> = {
  success: 'bg-success-bg text-success-text',
  warning: 'bg-warning-bg text-warning-text',
  error: 'bg-error-bg text-error-text',
  muted: 'bg-subtle text-primary',
};

export function verdictLabel(verdict?: string | null): string {
  if (!verdict) return '';
  return VERDICTS[verdict]?.label ?? verdict.replace(/_/g, ' ');
}

const sentence = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);

interface VerdictCardProps {
  decision: FinalDecision;
  evidenceCount?: number;
  /** A plain bordered surface (no glass, no shadow) for marketing pages. */
  flat?: boolean;
}

/**
 * The recommendation and the reasons behind it. The verdict is computed by fixed rules from the scored
 * answers; each rule that lowered it from its starting point is listed with its reason, so a recruiter can
 * check the result instead of taking it on trust.
 */
export function VerdictCard({ decision, evidenceCount, flat = false }: VerdictCardProps) {
  const tone = VERDICTS[decision.verdict]?.tone ?? 'muted';
  const lowered = !!decision.draft_verdict && decision.draft_verdict !== decision.verdict;

  const figures = [
    decision.score != null && { label: 'Decision score', value: Number(decision.score).toFixed(1), unit: '/ 10' },
    decision.confidence != null && { label: 'Confidence', value: `${Math.round(Number(decision.confidence) * 100)}%` },
    evidenceCount != null && { label: 'Evidence items', value: String(evidenceCount) },
  ].filter(Boolean) as { label: string; value: string; unit?: string }[];

  const body = (
    <>
      <div className={`flex flex-wrap items-end justify-between gap-x-8 gap-y-3 px-5 py-4 ${TONE_BAND[tone]}`}>
        <div>
          <p className="text-[13px] opacity-80">Recommendation</p>
          <p className="text-[28px] leading-9 font-semibold tracking-[-0.02em]">{verdictLabel(decision.verdict)}</p>
        </div>
        {figures.length > 0 && (
          <dl className="flex gap-6">
            {figures.map(f => (
              <div key={f.label}>
                <dt className="text-xs opacity-80">{f.label}</dt>
                <dd className="text-lg font-semibold tabular">
                  {f.value}{f.unit && <span className="text-xs font-normal opacity-70"> {f.unit}</span>}
                </dd>
              </div>
            ))}
          </dl>
        )}
      </div>

      <div className="px-5 py-4 space-y-4">
        {decision.flag_review && (
          <div
            className="flex items-start gap-2 rounded-md border border-warning/40 bg-warning-bg px-3 py-2 text-[13px] text-warning-text"
            role="note"
          >
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>
              A person should review this result before acting on it
              {decision.contradiction_count > 0
                ? ` (${decision.contradiction_count} inconsistent answer${decision.contradiction_count === 1 ? '' : 's'} found).`
                : '.'}
            </span>
          </div>
        )}

        {decision.rationale && <p className="text-sm text-primary leading-relaxed max-w-[70ch]">{decision.rationale}</p>}

        {lowered && decision.adjustments.length > 0 && (
          <div className="border-t border-border pt-4 first:border-t-0 first:pt-0">
            <h3 className="text-[13px] font-semibold text-primary mb-2">Why it was lowered from {verdictLabel(decision.draft_verdict)}</h3>
            <ul className="space-y-2">
              {decision.adjustments.map((a, i) => (
                <li key={i} className="text-[13px] text-secondary">
                  <span className="inline-flex items-center gap-1 font-medium text-primary">
                    {verdictLabel(a.from)} <ChevronRight className="w-3.5 h-3.5 text-tertiary" aria-label="to" /> {verdictLabel(a.to)}
                  </span>
                  <span className="block mt-0.5">{a.reason}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {decision.next_steps.length > 0 && (
          <div className="border-t border-border pt-4 first:border-t-0 first:pt-0">
            <h3 className="text-[13px] font-semibold text-primary mb-2">Suggested next steps</h3>
            <ul className="list-disc pl-4 space-y-1 marker:text-tertiary">
              {decision.next_steps.map((step, i) => (
                <li key={i} className="text-[13px] text-secondary">{sentence(step)}</li>
              ))}
            </ul>
          </div>
        )}

        <p className="text-xs text-tertiary">
          The recommendation comes from fixed scoring rules applied to the answers below. The wording above is written
          by an AI; it does not choose the verdict.
        </p>
      </div>
    </>
  );

  if (flat) return <FlatSurface className="mb-6 !p-0 overflow-hidden">{body}</FlatSurface>;
  return <section className="mb-6 rounded-xl border border-border bg-section overflow-hidden" aria-label="Recommendation">{body}</section>;
}
