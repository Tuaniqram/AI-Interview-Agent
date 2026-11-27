import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Check, Minus, Printer } from 'lucide-react';
import { apiClient } from '../services/apiClient';
import { Card } from '../components/shared/Card';
import { Button } from '../components/shared/Button';
import { StatusBadge } from '../components/shared/StatusBadge';
import { Skeleton } from '../components/shared/Skeleton';
import { VerdictCard } from '../components/interview/VerdictCard';
import { CompetencyTable } from '../components/interview/CompetencyTable';
import { EvidenceText, countHighlights } from '../components/shared/EvidenceText';
import { humanizePhase } from './interview/shared';
import type { InterviewReport as InterviewReportType } from '../types/interview';

interface Message {
  id: string;
  role: string;
  message_type: string;
  content: string;
  question_number: number;
  phase: string;
  score: number | null;
  created_at: string;
}

interface Evaluation {
  id: string;
  message_id: string;
  technical_score: number | null;
  communication_score: number | null;
  strengths: string | null;
  weaknesses: string | null;
  /** The same points as clean sentences (sent by the summary endpoint). */
  strengths_items?: string[];
  weaknesses_items?: string[];
  feedback: string | null;
  overall_score: number | null;
}

/** "Core technical 7.0 · Problem solving 6.5": the competencies an answer was scored on, with the average score. */
function scoredOn(items: Array<{ competency: string | null; score: number | null }> | undefined): string {
  if (!items?.length) return '';
  const byCompetency = new Map<string, number[]>();
  for (const item of items) {
    if (!item.competency || item.score == null) continue;
    byCompetency.set(item.competency, [...(byCompetency.get(item.competency) ?? []), item.score]);
  }
  return Array.from(byCompetency.entries())
    .map(([id, scores]) => `${humanizePhase(id)} ${(scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1)}`)
    .join(', ');
}

type Tone = 'success' | 'warning' | 'error' | 'none';
function tone(score: number | null | undefined): Tone {
  if (score == null || Number.isNaN(score)) return 'none';
  if (score >= 7) return 'success';
  if (score >= 5) return 'warning';
  return 'error';
}
const TONE_TEXT: Record<Tone, string> = { success: 'text-success-text', warning: 'text-warning-text', error: 'text-error-text', none: 'text-tertiary' };
const TONE_BAR: Record<Tone, string> = { success: 'bg-success', warning: 'bg-warning', error: 'bg-error', none: 'bg-hover' };
const TONE_CHIP: Record<Tone, string> = {
  success: 'bg-success-bg text-success-text', warning: 'bg-warning-bg text-warning-text',
  error: 'bg-error-bg text-error-text', none: 'bg-hover text-secondary',
};

/** A labelled score with a bar under it, for the side column. */
function ScoreRow({ label, score, emphasis = false }: { label: string; score: number | null | undefined; emphasis?: boolean }) {
  const value = score == null ? null : Number(score);
  const t = tone(value);
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className={emphasis ? 'text-[13px] font-medium text-primary' : 'text-[13px] text-secondary'}>{label}</span>
        <span className={`tabular font-semibold ${emphasis ? 'text-2xl tracking-[-0.02em]' : 'text-sm'} ${value == null ? 'text-tertiary' : 'text-primary'}`}>
          {value != null ? value.toFixed(1) : '—'}
          {emphasis && value != null && <span className="text-xs font-normal text-tertiary"> / 10</span>}
        </span>
      </div>
      <div className="mt-1.5 h-1.5 rounded-full bg-hover overflow-hidden" aria-hidden>
        {value != null && <div className={`h-full rounded-full ${TONE_BAR[t]}`} style={{ width: `${Math.max(0, Math.min(100, value * 10))}%` }} />}
      </div>
    </div>
  );
}

function ReportSkeleton() {
  return (
    <div className="space-y-6" aria-busy="true" aria-label="Loading report">
      <div className="space-y-2"><Skeleton width="30%" height="1.75rem" /><Skeleton width="45%" /></div>
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_300px]">
        <div className="space-y-4">
          <Skeleton variant="rect" height="9rem" />
          <Skeleton variant="rect" height="14rem" />
        </div>
        <Skeleton variant="rect" height="16rem" />
      </div>
    </div>
  );
}

export function InterviewReportPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [report, setReport] = useState<InterviewReportType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await apiClient.get<InterviewReportType>(`/interviews/${id}/summary`);
        if (!cancelled) setReport(data);
      } catch {
        if (!cancelled) setError('This report could not be loaded. Check your connection and reload the page.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, [id]);

  if (loading) return <ReportSkeleton />;

  if (error || !report) {
    return (
      <div>
        <Button variant="ghost" size="sm" icon={<ArrowLeft />} onClick={() => navigate(-1)} className="-ml-2 mb-4">Back</Button>
        <Card><p className="py-8 text-center text-sm text-secondary">{error || 'There is no report for this interview.'}</p></Card>
      </div>
    );
  }

  const messages = (report.messages || []) as unknown as Message[];
  const evaluations = (report.evaluations || []) as unknown as Evaluation[];

  // Pair questions with answers
  const questions = messages.filter(m => m.role === 'assistant' || m.role === 'interviewer' || m.message_type.endsWith('question'));
  const answers = messages.filter(m => m.role === 'user' || m.role === 'candidate' || m.message_type.endsWith('answer'));

  // What each score rests on, grouped by question number.
  const evidenceByQuestion = new Map<number, NonNullable<InterviewReportType['evidence_items']>>();
  for (const item of report.evidence_items ?? []) {
    evidenceByQuestion.set(item.question_number, [...(evidenceByQuestion.get(item.question_number) ?? []), item]);
  }
  const highlightedAnswers = questions.filter(q => {
    const answer = answers.find(a => a.question_number === q.question_number);
    return answer && countHighlights(answer.content, (evidenceByQuestion.get(q.question_number) ?? []).map(e => e.quote)) > 0;
  }).length;

  const title = report.candidate_name || 'Interview report';
  const meta = [
    report.job_role,
    report.org_name,
    report.started_at && new Date(report.started_at).toLocaleDateString(undefined, { day: 'numeric', month: 'long', year: 'numeric' }),
  ].filter(Boolean) as string[];

  const facts: [string, string][] = [
    ['Questions answered', `${report.total_questions_answered} of ${report.total_questions}`],
    ['Answer rate', `${Math.round(report.answered_ratio * 100)}%`],
    ['Messages', String(report.messages_count)],
    ['Interview', report.interview_complete ? 'Complete' : 'Ended early'],
  ];

  return (
    <div>
      {/* Header: who, for what, when. */}
      <header className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between mb-8">
        <div className="min-w-0">
          <div className="flex items-center gap-2.5 flex-wrap">
            <h1 className="text-[22px] leading-7 font-semibold tracking-[-0.015em] text-primary" title={report.candidate_email || undefined}>
              {title}
            </h1>
            <StatusBadge status={report.status} />
          </div>
          {meta.length > 0 && (
            <p className="mt-1 text-sm text-secondary">
              {meta.map((m, i) => <span key={i}>{i > 0 && <span className="text-border-strong mx-2" aria-hidden>/</span>}{m}</span>)}
            </p>
          )}
          {report.candidate_email && report.candidate_name && (
            <p className="mt-0.5 text-[13px] text-tertiary">{report.candidate_email}</p>
          )}
        </div>
        <div className="flex gap-2 shrink-0 print:hidden">
          <Button variant="secondary" icon={<ArrowLeft />} onClick={() => navigate(-1)}>Back</Button>
          <Button variant="secondary" icon={<Printer />} onClick={() => window.print()}>Print</Button>
        </div>
      </header>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_300px] items-start">
        {/* Main column: the decision first, then what it rests on. */}
        <div className="min-w-0">
          {report.final_decision && (
            <VerdictCard decision={report.final_decision} evidenceCount={report.v4_evidence_count} />
          )}

          {report.v4_competency_summary && <CompetencyTable summary={report.v4_competency_summary} />}

          {(report.strengths?.length || report.weaknesses?.length) ? (
            <div className="grid gap-4 sm:grid-cols-2 mb-6">
              {report.strengths && report.strengths.length > 0 && (
                <Card>
                  <h3 className="text-sm font-semibold text-primary mb-3">Strengths</h3>
                  <ul className="space-y-2">
                    {report.strengths.map((s, i) => (
                      <li key={i} className="flex gap-2 text-[13px] text-secondary">
                        <Check className="w-4 h-4 shrink-0 mt-px text-success" aria-hidden />{s}
                      </li>
                    ))}
                  </ul>
                </Card>
              )}
              {report.weaknesses && report.weaknesses.length > 0 && (
                <Card>
                  <h3 className="text-sm font-semibold text-primary mb-3">Areas to probe</h3>
                  <ul className="space-y-2">
                    {report.weaknesses.map((w, i) => (
                      <li key={i} className="flex gap-2 text-[13px] text-secondary">
                        <Minus className="w-4 h-4 shrink-0 mt-px text-warning" aria-hidden />{w}
                      </li>
                    ))}
                  </ul>
                </Card>
              )}
            </div>
          ) : null}

          {/* The transcript, question by question, with the words each score rests on marked. */}
          <section aria-labelledby="transcript-heading">
            <div className="flex flex-wrap items-baseline justify-between gap-2 mb-3">
              <h2 id="transcript-heading" className="text-sm font-semibold text-primary">Questions and answers</h2>
              {highlightedAnswers > 0 && (
                <p className="text-xs text-tertiary">
                  <mark className="evidence-mark">Highlighted words</mark> are the parts of an answer a score is based on.
                </p>
              )}
            </div>

            {questions.length === 0 ? (
              <Card><p className="text-[13px] text-tertiary py-6 text-center">No questions were recorded for this interview.</p></Card>
            ) : (
              <ol className="rounded-xl border border-border bg-section divide-y divide-[var(--divider)]">
                {questions.map((q, i) => {
                  const matchingAnswer = answers.find(a => a.question_number === q.question_number);
                  const evalData = evaluations.find(e => e.message_id === matchingAnswer?.id);
                  const scored = scoredOn(evidenceByQuestion.get(q.question_number));
                  const t = tone(evalData?.overall_score);
                  return (
                    <li key={q.id || i} className="p-5 break-inside-avoid">
                      <div className="flex items-start gap-3">
                        <span className="w-6 h-6 rounded-md bg-hover text-secondary text-xs font-semibold flex items-center justify-center shrink-0 tabular" aria-label={`Question ${q.question_number}`}>
                          {q.question_number}
                        </span>
                        <p className="flex-1 text-sm font-medium text-primary leading-relaxed">{q.content}</p>
                        {evalData?.overall_score != null && (
                          <span className={`shrink-0 h-6 px-2 rounded-md text-xs font-semibold flex items-center tabular ${TONE_CHIP[t]}`}>
                            {Number(evalData.overall_score).toFixed(1)}
                          </span>
                        )}
                      </div>

                      <div className="ml-9 mt-3 space-y-3">
                        {matchingAnswer ? (
                          <blockquote className="rounded-lg bg-subtle border border-border px-4 py-3 text-[13px] text-primary leading-relaxed whitespace-pre-line">
                            <EvidenceText text={matchingAnswer.content} quotes={(evidenceByQuestion.get(q.question_number) ?? []).map(e => e.quote)} />
                          </blockquote>
                        ) : (
                          <p className="text-[13px] text-tertiary">Not answered.</p>
                        )}

                        {(evalData?.technical_score != null || evalData?.communication_score != null || scored) && (
                          <p className="text-xs text-tertiary">
                            {evalData?.technical_score != null && <>Technical <span className="text-secondary font-medium tabular">{evalData.technical_score}</span></>}
                            {evalData?.communication_score != null && <>{evalData?.technical_score != null && <span className="mx-2" aria-hidden>/</span>}Communication <span className="text-secondary font-medium tabular">{evalData.communication_score}</span></>}
                            {scored && (
                              <span className="block mt-0.5" data-testid="scored-on">Scored on: {scored}</span>
                            )}
                          </p>
                        )}

                        {evalData?.feedback && <p className="text-[13px] text-secondary leading-relaxed">{evalData.feedback}</p>}

                        {(evalData?.strengths_items?.length || evalData?.weaknesses_items?.length) ? (
                          <div className="grid gap-3 sm:grid-cols-2" data-testid="answer-feedback">
                            {evalData?.strengths_items?.length ? (
                              <div>
                                <p className="text-xs font-medium text-success-text mb-1">Went well</p>
                                <ul className="space-y-1">
                                  {evalData.strengths_items.map((s, k) => (
                                    <li key={k} className="flex gap-1.5 text-[13px] text-secondary"><Check className="w-3.5 h-3.5 shrink-0 mt-0.5 text-success" aria-hidden />{s}</li>
                                  ))}
                                </ul>
                              </div>
                            ) : null}
                            {evalData?.weaknesses_items?.length ? (
                              <div>
                                <p className="text-xs font-medium text-warning-text mb-1">Missing or unclear</p>
                                <ul className="space-y-1">
                                  {evalData.weaknesses_items.map((w, k) => (
                                    <li key={k} className="flex gap-1.5 text-[13px] text-secondary"><Minus className="w-3.5 h-3.5 shrink-0 mt-0.5 text-warning" aria-hidden />{w}</li>
                                  ))}
                                </ul>
                              </div>
                            ) : null}
                          </div>
                        ) : null}
                      </div>
                    </li>
                  );
                })}
              </ol>
            )}
          </section>
        </div>

        {/* Side column: the figures, kept in view while reading the evidence. */}
        <aside className="space-y-4 xl:sticky xl:top-4">
          <Card>
            <h2 className="text-sm font-semibold text-primary mb-4">Scores</h2>
            <div className="space-y-4">
              <ScoreRow label="Overall" score={report.final_score} emphasis />
              <ScoreRow label="Technical" score={report.technical_score} />
              <ScoreRow label="Communication" score={report.communication_score} />
            </div>
          </Card>

          {report.scorecard && (
            <Card>
              <div className="flex items-start justify-between gap-3 mb-3">
                <div className="min-w-0">
                  <h2 className="text-sm font-semibold text-primary">Scorecard</h2>
                  <p className="text-xs text-tertiary mt-0.5 truncate">{report.scorecard.template_name || 'Built-in rubric'}</p>
                </div>
                {report.scorecard.weighted_score != null && (
                  <p className={`text-lg font-semibold tabular ${TONE_TEXT[tone(Number(report.scorecard.weighted_score))]}`}>
                    {Number(report.scorecard.weighted_score).toFixed(2)}
                  </p>
                )}
              </div>
              {Object.keys(report.scorecard.scores || {}).length > 0 && (
                <dl className="divide-y divide-[var(--divider)]">
                  {Object.entries(report.scorecard.scores).map(([sid, s]) => {
                    const value = Number(s.normalized ?? s.score ?? 0);
                    return (
                      <div key={sid} className="flex items-center justify-between gap-3 py-2">
                        <dt className="text-[13px] text-secondary truncate">{s.name || humanizePhase(sid)}</dt>
                        <dd className={`text-[13px] font-semibold tabular ${TONE_TEXT[tone(value)]}`}>{value.toFixed(1)}</dd>
                      </div>
                    );
                  })}
                </dl>
              )}
            </Card>
          )}

          <Card>
            <h2 className="text-sm font-semibold text-primary mb-2">Interview</h2>
            <dl className="divide-y divide-[var(--divider)]">
              {facts.map(([k, v]) => (
                <div key={k} className="flex items-center justify-between py-2">
                  <dt className="text-[13px] text-secondary">{k}</dt>
                  <dd className="text-[13px] font-medium text-primary tabular">{v}</dd>
                </div>
              ))}
            </dl>
          </Card>
        </aside>
      </div>
    </div>
  );
}
