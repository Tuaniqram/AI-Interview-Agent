import type { EmbeddedBrain } from '../components/graph/embedded';
import { REAL_CANDIDATES, type RealCandidate, type RealStep } from './realInterviews';

/* ════════════════════════════════════════════════════════════════════════
   Brain snapshots for the landing demo — built from the real session data
   (realInterviews.ts), so the brain graph shows the same interview the demo
   tab shows. Shape matches EmbeddedBrain (normalize()'s non-live branch).
   ════════════════════════════════════════════════════════════════════════ */

function hashId(seed: string): string {
  let h = 5381;
  for (let i = 0; i < seed.length; i++) h = ((h << 5) + h + seed.charCodeAt(i)) >>> 0;
  return 'h' + h.toString(16).padStart(12, '0');
}

function stepDifficulty(step: RealStep): number {
  const ph = (step.phase || '').toLowerCase();
  if (ph === 'intro' || ph === 'conclusion') return 2;
  const s = step.score;
  if (s == null) return 3;
  if (s >= 7.5) return 3;
  if (s >= 5.5) return 4;
  return 5;
}

function pickHypothesis(step: RealStep, hyps: RealCandidate['hypotheses']): RealCandidate['hypotheses'][number] {
  const same = hyps.filter((h) => h.competency === step.comp);
  if (same.length === 0) return hyps[0];
  const score = step.score ?? 5;
  const positive = same.find((h) => h.status === 'confirmed' && /demonstrates|strong/i.test(h.statement));
  const negative = same.find((h) => /weak|limited|no /i.test(h.statement));
  if (score >= 7 && positive) return positive;
  if (score < 5.5 && negative) return negative;
  return same.sort((a, b) => b.confidence - a.confidence)[0];
}

export function buildBrainSnapshot(cand: RealCandidate): EmbeddedBrain {
  const competencies = Object.entries(cand.evidence).map(([id, e]) => ({
    id,
    avg: e.avg ?? 0,
    count: e.count ?? 0,
    gap: e.gap ?? 0,
    scores: [] as number[],
  }));

  const hyps = cand.hypotheses.map((h) => ({
    id: hashId(h.competency + '|' + h.statement),
    status: h.status,
    confidence: h.confidence,
    competency: h.competency,
    statement: h.statement,
    evidence: 0,
    required: 3,
  }));

  const hypById = new Map(hyps.map((h) => [h.id, h]));
  const evIds: string[] = [];
  const graph_edges: Array<{ from: string; to: string; w: number; support: boolean }> = [];
  const phases = cand.steps.map((step, i) => {
    const hyp = pickHypothesis(step, cand.hypotheses);
    const evId = hashId('ev:' + cand.id + ':' + i);
    evIds.push(evId);
    graph_edges.push({
      from: evId,
      to: hashId(hyp.competency + '|' + hyp.statement),
      w: Math.max(0.2, Math.min(0.95, (step.score ?? 5) / 10)),
      support: (step.score ?? 5) >= 6.5,
    });
    return {
      n: i + 1,
      phase: step.phase || 'technical',
      difficulty: stepDifficulty(step),
      evidence_count: i,
    };
  });

  const outcomes = { confirmed: 0, testing: 0, refuted: 0, unanswered: 0 };
  for (const h of cand.hypotheses) {
    if (h.status === 'confirmed') outcomes.confirmed++;
    else if (h.status === 'refuted') outcomes.refuted++;
    else if (h.status === 'testing') outcomes.testing++;
    else outcomes.unanswered++;
  }

  const details: Record<string, { gap: number; weight: number; covered: boolean; average_score: number; evidence_count: number }> = {};
  let gaps = 0;
  for (const [id, e] of Object.entries(cand.evidence)) {
    const count = e.count ?? 0;
    const gap = e.gap ?? 0;
    if (count === 0 || gap > 0.15) gaps++;
    details[id] = {
      gap,
      weight: Math.round((1 + count * 0.5) * 10) / 10,
      covered: count > 0,
      average_score: e.avg ?? 0,
      evidence_count: count,
    };
  }
  const severity = gaps === 0 ? 'sufficient' : gaps <= 2 ? 'borderline' : 'insufficient';

  void hypById;

  return {
    sid: cand.sessionId,
    role: cand.role,
    verdict: cand.verdict,
    composite: cand.composite ?? 0,
    confidence: cand.confidence ?? 0,
    coverage: cand.coverage ?? 0,
    difficulty_reached: cand.difficulty,
    evidence_total: competencies.reduce((a, c) => a + c.count, 0),
    hypothesis_outcomes: outcomes,
    sufficiency: {
      severity,
      is_sufficient: gaps === 0,
      remaining_gaps: gaps,
      coverage: cand.coverage ?? 0,
      details,
    },
    phases,
    competencies,
    hypotheses: hyps,
    graph_edges,
  };
}

export const BRAIN_SNAPSHOTS: Record<'alice' | 'brian', EmbeddedBrain> = {
  alice: buildBrainSnapshot(REAL_CANDIDATES.alice),
  brian: buildBrainSnapshot(REAL_CANDIDATES.brian),
};