/**
 * Fairness and transparency, stated as things the product does. Each line below matches how the engine works:
 * the verdict is computed by fixed rules in code, the AI writes the wording, clarification requests are not
 * scored, and borderline results are flagged for a person.
 */
const STATEMENTS: Array<{ title: string; body: string }> = [
  {
    title: 'One rubric for every candidate',
    body:
      'Each role has a fixed set of competencies and fixed scoring rules. The questions adapt to a candidate’s answers; what is measured, and how, does not.',
  },
  {
    title: 'Rules choose the verdict, not the AI',
    body:
      'The recommendation is computed by fixed scoring rules from the scored answers. The AI writes the explanation; it does not decide the outcome.',
  },
  {
    title: 'Every score points at an answer',
    body:
      'The report shows the question, the candidate’s exact words and what went well or was missing for each answer, so a score can be checked.',
  },
  {
    title: 'Each downgrade has a reason',
    body:
      'When a rule lowers a recommendation, for example because a figure changed between answers, the report lists the rule and why it applied.',
  },
  {
    title: 'A person reviews the uncertain cases',
    body:
      'Results with contradictions or thin evidence are flagged for human review. AURA recommends; the hiring decision stays with your team.',
  },
  {
    title: 'Asking for a repeat is not penalised',
    body:
      'If a candidate asks for a question to be repeated or explained, the interviewer helps and nothing is scored for that message.',
  },
  {
    title: 'Candidates see the rules first',
    body:
      'Before the interview starts, candidates read the conduct rules, including that tab switches and pasted text are recorded as signals for the reviewer.',
  },
];

export function FairnessSection() {
  return (
    <section id="fairness" className="border-t border-border">
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 md:py-24">
        <p className="font-mono text-xs uppercase tracking-wide text-muted">Fairness and transparency</p>
        <h2 className="font-display mt-3 max-w-3xl text-3xl text-primary md:text-4xl">
          A judgement you can check, line by line.
        </h2>

        <dl className="mt-10 grid gap-x-12 gap-y-0 md:grid-cols-2">
          {STATEMENTS.map((s, i) => (
            <div key={s.title} className="grid grid-cols-[2.5rem_1fr] gap-x-3 border-t border-border py-5">
              <dt className="col-start-2 text-sm font-semibold text-primary">
                {s.title}
              </dt>
              <span className="col-start-1 row-start-1 font-mono text-xs text-muted">{String(i + 1).padStart(2, '0')}</span>
              <dd className="col-start-2 mt-1 text-sm leading-relaxed text-secondary">{s.body}</dd>
            </div>
          ))}

          {/* Data handling: the facts are not in the code base, so this is a marked gap, not a claim. */}
          <div className="grid grid-cols-[2.5rem_1fr] gap-x-3 border-t border-dashed border-border-strong py-5 md:col-span-2">
            <span className="font-mono text-xs text-muted">08</span>
            <div>
              <p className="text-sm font-semibold text-primary">Data handling</p>
              <p className="mt-1 text-sm leading-relaxed text-secondary">
                <span className="font-mono text-xs uppercase text-warning-text">To confirm before launch · </span>
                Where CVs and transcripts are stored, how long they are kept, and how a candidate can ask for deletion.
              </p>
            </div>
          </div>
        </dl>
      </div>
    </section>
  );
}
