import { sampleExcerpts } from './sampleInterview';

/**
 * What a candidate sees while answering, built from the product's own wording: the question counter, the
 * topic, the answer box and the keyboard hint. Static, for the landing page.
 */
export function CandidateScreenPreview({ compact = false, index = 1 }: { compact?: boolean; index?: number }) {
  const q = sampleExcerpts()[index];
  return (
    <div
      className="rounded-ui-lg border border-border bg-elevated"
      role="img"
      aria-label="Preview of the candidate's interview screen: one question, an answer box and a hint to ask for the question again"
    >
      <div className="border-b border-border px-4 py-2 font-mono text-[11px] uppercase tracking-wide text-muted">
        Question {q.questionNumber} · up to 14 · {q.competency}
      </div>
      <div className="space-y-4 p-4 sm:p-5">
        <p className={`${compact ? 'text-sm' : 'text-base'} leading-relaxed text-primary`}>{q.question}</p>

        <div className="rounded-ui-md border border-border-strong bg-input px-3 py-3 text-sm text-muted">
          Type your answer...
        </div>
        <p className="font-mono text-[11px] text-muted">Enter to send · Shift+Enter for newline</p>

        {!compact && (
          <p className="border-t border-border pt-3 text-xs leading-relaxed text-secondary">
            Not sure what is being asked? Ask for the question to be repeated or explained. That message is not scored.
          </p>
        )}
      </div>
    </div>
  );
}
