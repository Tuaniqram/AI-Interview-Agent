import type { ReactNode } from 'react';
import { sampleExcerpts, type SampleExcerpt } from './sampleInterview';

/** Wrap each evidence phrase in `.evidence-mark`, in order, leaving the rest of the answer as plain text. */
function markEvidence(answer: string, phrases: string[]): ReactNode[] {
  const nodes: ReactNode[] = [];
  let rest = answer;
  phrases.forEach((phrase, i) => {
    const at = rest.indexOf(phrase);
    if (at < 0) return;
    if (at > 0) nodes.push(rest.slice(0, at));
    nodes.push(<mark key={i} className="evidence-mark">{phrase}</mark>);
    rest = rest.slice(at + phrase.length);
  });
  if (rest) nodes.push(rest);
  return nodes;
}

const score = (n: number | null) => (n == null ? '-' : n.toFixed(1));

/**
 * One answer from a sample interview with the words its score rests on highlighted, and the score,
 * what went well and what was missing underneath. This is the product's promise in one picture:
 * every score points at the answer behind it.
 */
export function EvidenceTranscript({ excerpt }: { excerpt?: SampleExcerpt }) {
  const e = excerpt ?? sampleExcerpts()[0];
  return (
    <figure className="rounded-ui-lg border border-border bg-elevated" aria-label="Sample interview excerpt">
      <figcaption className="flex items-center justify-between gap-3 border-b border-border px-4 py-2 font-mono text-[11px] uppercase tracking-wide text-muted">
        <span>Sample interview · {e.role}</span>
        <span>Anonymised test data</span>
      </figcaption>

      <div className="space-y-4 p-4 sm:p-5">
        <div>
          <p className="mb-1 font-mono text-[11px] uppercase tracking-wide text-muted">
            Question {e.questionNumber} · {e.competency}
          </p>
          <p className="text-sm text-primary">{e.question}</p>
        </div>

        <div>
          <p className="mb-1 font-mono text-[11px] uppercase tracking-wide text-muted">Candidate A</p>
          <p className="text-sm leading-relaxed text-secondary">{markEvidence(e.answer, e.phrases)}</p>
        </div>

        <p className="border-t border-border pt-3 font-mono text-xs text-primary">
          Q{e.questionNumber} · {e.competency} · {score(e.overall)} / 10
          <span className="text-muted"> — technical {score(e.technical)} · communication {score(e.communication)}</span>
        </p>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <p className="mb-1 font-mono text-[11px] uppercase tracking-wide text-success-text">Went well</p>
            <ul className="space-y-0.5 text-xs text-secondary">
              {e.wentWell.map(t => <li key={t}>{t}</li>)}
            </ul>
          </div>
          <div>
            <p className="mb-1 font-mono text-[11px] uppercase tracking-wide text-warning-text">Missing</p>
            <ul className="space-y-0.5 text-xs text-secondary">
              {e.missing.map(t => <li key={t}>{t}</li>)}
            </ul>
          </div>
        </div>

        <p className="text-[11px] text-muted">
          <mark className="evidence-mark">Highlighted words</mark> are the parts of the answer the score is based on.
        </p>
      </div>
    </figure>
  );
}
