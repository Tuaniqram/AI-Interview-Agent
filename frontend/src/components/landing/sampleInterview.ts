import { REAL_CANDIDATES, type RealCandidate, type RealStep } from '../../data/realInterviews';
import type { FinalDecision } from '../../types/interview';

/**
 * The one sample interview the landing page shows. It comes from `data/realInterviews.ts` (test sessions, not
 * customers) and is anonymised here: the candidate's name and e-mail never reach the page.
 */
const SOURCE: RealCandidate = REAL_CANDIDATES.alice;

/** The data file holds a few broken characters from an old export; show a plain dash instead. */
const clean = (text: string) => text.replace(/�/g, '-').replace(/\s+/g, ' ').trim();

/** "a, b, c" -> ["a", "b", "c"], without repeats. */
const items = (text: string) => Array.from(new Set(text.split(',').map(t => t.trim()).filter(Boolean)));

/**
 * Pick the phrases a score plausibly rests on: the stretches of the answer around a figure ("40k requests per
 * minute", "p95 dropped from 900ms to 210ms"). Each result is a verbatim piece of the answer.
 */
export function pickEvidencePhrases(answer: string, max = 3): string[] {
  const phrases: string[] = [];
  // One sentence at a time, so a highlight never runs across a full stop.
  for (const sentence of answer.match(/[^.!?]+[.!?]*/g) ?? []) {
    const found = sentence.match(/\S+(?:\s+\S+){0,3}\s+\d[\d.,]*\S*(?:\s+\S+){0,4}/g) ?? [];
    for (const piece of found) {
      const phrase = piece.replace(/[.,;!?]+$/, '').replace(/^[\s\-–—]+/, '');
      if (phrase && answer.includes(phrase)) phrases.push(phrase);
    }
  }
  return phrases.slice(0, max);
}

export interface SampleExcerpt {
  role: string;
  competency: string;
  questionNumber: number;
  question: string;
  answer: string;
  phrases: string[];
  overall: number | null;
  technical: number | null;
  communication: number | null;
  wentWell: string[];
  missing: string[];
}

function toExcerpt(step: RealStep, number: number): SampleExcerpt {
  const answer = clean(step.a);
  return {
    role: SOURCE.role,
    competency: step.compLabel,
    questionNumber: number,
    question: clean(step.q),
    answer,
    phrases: pickEvidencePhrases(answer),
    overall: step.score,
    technical: step.tech,
    communication: step.comm,
    wentWell: items(step.strengths).slice(0, 3),
    missing: items(step.weaknesses).slice(0, 3),
  };
}

export const sampleExcerpts = (): SampleExcerpt[] => SOURCE.steps.slice(0, 3).map((s, i) => toExcerpt(s, i + 1));

/** The final decision for the sample, in the shape the recruiter's report uses. */
export function sampleDecision(): FinalDecision {
  return {
    verdict: SOURCE.decision,
    draft_verdict: SOURCE.decision,
    score: SOURCE.decisionScore,
    confidence: null,
    flag_review: false,
    rationale: null,
    adjustments: [],
    next_steps: ['schedule follow-up with the hiring manager'],
    contradiction_count: 0,
  };
}

export function sampleCompetencies() {
  const out: Record<string, { average_score: number; evidence_count: number; gap: number }> = {};
  for (const [id, e] of Object.entries(SOURCE.evidence)) {
    if (e.avg == null) continue;
    out[id] = { average_score: e.avg, evidence_count: e.count ?? 0, gap: e.gap ?? 0 };
  }
  return out;
}

export const sampleRole = SOURCE.role;
