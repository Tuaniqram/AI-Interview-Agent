import React, { useEffect, useRef, useState } from "react";
import { EMBEDDED, type EmbeddedBrain } from "./embedded";
import { apiClient } from "../../services/apiClient";

const DEFAULT_SID = "9f025266-26b8-4cbe-8b8c-b883c5436eea";

/* =========================================================================
   AURA V5 · Brain Graph — pure canvas force-layout of an interview brain.
   Ported from frontend/public/brain_graph.html into a React component.
   Renders a three-box card: big graph (center), info side panel (right),
   replay play/timeline bar (bottom).
   ========================================================================= */

type LayerType = "core" | "comp" | "hyp" | "ev" | "q";

interface GNode {
  id: string;
  type: LayerType;
  lvl: number;
  x: number; y: number; vx: number; vy: number;
  r: number; alpha: number; glow: number;
  pulse: number; order: number; phase: number;
  lit: boolean; hidden: boolean;
  neighbors: Set<string>;
  ringR?: number;
  cmeta?: { avg?: number; count?: number; gap?: number; scores?: number[] };
  gapNode?: boolean;
  hmeta?: { status?: string; confidence?: number; statement?: string; evidence?: number; required?: number; competency?: string };
  emeta?: { w: number; sup: number; hyp?: string; comp?: string };
  qmeta?: { n?: number; phase?: string; diff?: number; evcount?: number; delta?: number; turnIdx?: number; newEvs: string[] };
  hypId?: string;
  compId?: string;
  evTurn?: number;
  revealAt?: number;
}

interface GEdge {
  a: GNode; b: GNode; w: number; sup: boolean;
}

interface Phase {
  n?: number;
  phase?: string;
  difficulty?: number;
  evidence_count?: number;
}

interface BrainData {
  sid?: string;
  role?: string;
  verdict?: string;
  composite?: number;
  confidence?: number;
  coverage?: number;
  difficulty?: number;
  evidence_total: number;
  hypotheses: Array<{
    id?: string; status?: string; confidence?: number; competency?: string;
    statement?: string; evidence?: number; required?: number;
  }>;
  competencies: Array<{ id: string; avg?: number; count?: number; gap?: number; scores?: number[] }>;
  gap_competencies?: Array<{ id: string }>;
  graph_edges: Array<{ from?: string; to?: string; w?: number; weight?: number; support?: boolean }>;
  phases: Phase[];
  hypothesis_outcomes?: Record<string, number>;
  sufficiency?: { severity?: string; is_sufficient?: boolean; remaining_gaps?: number; coverage?: number };
  layers?: Record<string, any>;
}

interface SimStore {
  data: BrainData | null;
  nodes: GNode[];
  edges: GEdge[];
  index: Record<string, GNode>;
  core: GNode | null;
  cam: { x: number; y: number; k: number };
  turns: Phase[];
  cur: number;
  hover: GNode | null;
  drag: GNode | null;
  sel: GNode | null;
  WW: number;
  WH: number;
  DPR: number;
  evTotal: number;
  layer: string | null;
}

interface Tip {
  title: string;
  rows: [string, string][];
  x: number;
  y: number;
}

/* =========================================================================
   STYLE — the three-box demo card
   ========================================================================= */
const CSS = `
.bg-card{position:relative;text-align:left;display:grid;gap:14px;
  grid-template-columns:minmax(0,1fr) 320px;grid-template-rows:auto}
.bg-card .bg-panel{background:rgba(16,20,38,.72);border:1px solid rgba(148,163,255,.14);
  border-radius:16px;box-shadow:0 10px 40px rgba(0,0,0,.45)}
.bg-panel.bg-graph{grid-area:1/1;overflow:hidden;position:relative;display:flex;
  align-items:stretch;justify-content:stretch;min-height:min(56vh,500px);
  background:radial-gradient(1100px 700px at 78% -10%, rgba(139,92,246,.16), transparent 60%),
  radial-gradient(900px 620px at 8% 108%, rgba(56,189,248,.10), transparent 60%),#05070f}
.bg-canvas{width:100%;height:100%;display:block;cursor:grab;touch-action:none;min-width:0;min-height:0}
.bg-canvas.bg-dragging{cursor:grabbing}
.bg-aside{grid-area:1/2;align-self:stretch;display:flex;flex-direction:column;gap:14px;min-width:0}
.bg-panel.bg-info{grid-area:auto;padding:13px 16px}
.bg-panel.bg-hiring{grid-area:auto;flex:1;padding:13px 16px}
.bg-role{font-size:12.5px;font-weight:600;color:#e8ecff;margin:4px 0 6px}
.bg-title{font:700 13px/1.35 "Segoe UI",system-ui,sans-serif;letter-spacing:.14em;text-transform:uppercase;margin:0;
  background:linear-gradient(90deg,#c4b5fd,#7dd3fc);-webkit-background-clip:text;background-clip:text;color:transparent}
.bg-sid{font-size:10.5px;color:#8a93ad;margin:2px 0 8px;word-break:break-all}
.bg-verdict{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.bg-chip{font-size:12px;font-weight:700;padding:4px 12px;border-radius:99px;letter-spacing:.05em}
.bg-chip-borderline,.bg-chip-insufficient_evidence{background:rgba(251,191,36,.14);color:#fbbf24;border:1px solid rgba(251,191,36,.4)}
.bg-chip-hire,.bg-chip-strong_hire,.bg-chip-lean_hire{background:rgba(52,211,153,.14);color:#34d399;border:1px solid rgba(52,211,153,.4)}
.bg-chip-no_hire,.bg-chip-lean_no_hire,.bg-chip-strong_no_hire{background:rgba(251,113,133,.14);color:#fb7185;border:1px solid rgba(251,113,133,.4)}
.bg-stats{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:5px 14px;margin-top:10px;align-items:baseline}
.bg-stats .k{font-size:10.5px;color:#8a93ad}
.bg-stats .v{font-size:11.5px;font-weight:600;color:#e6e9f5;text-align:right;word-break:break-word}
.bg-stats .v.hot{color:#fbbf24}
.bg-head{position:absolute;top:0;left:0;right:0;z-index:6;display:flex;align-items:center;gap:16px;
  padding:12px 16px;pointer-events:none;flex-wrap:wrap;
  background:linear-gradient(180deg,rgba(5,7,15,.86),rgba(5,7,15,.35) 72%,transparent);
  border-bottom:1px solid rgba(148,163,255,.1)}
.bg-head-main{display:flex;flex-direction:column;gap:5px;min-width:0;flex:1 1 auto}
.bg-head-title{font:700 14px/1.3 "Segoe UI",system-ui,sans-serif;letter-spacing:.14em;text-transform:uppercase;margin:0;
  background:linear-gradient(90deg,#c4b5fd,#7dd3fc);-webkit-background-clip:text;background-clip:text;color:transparent}
.bg-head-sub{font-size:11px;color:#8a93ad;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bg-legend{display:flex;gap:10px;flex-wrap:wrap}
.bg-legend .lg{font-size:9.5px;letter-spacing:.05em;color:#aab3cc;display:inline-flex;align-items:center;gap:5px;white-space:nowrap}
.bg-legend .lg::before{content:"";width:8px;height:8px;border-radius:50%;background:var(--lg,#888);box-shadow:0 0 6px var(--lg,#888)}
.lg-core{--lg:#fbbf24}
.lg-comp{--lg:#60a5fa}
.lg-hyp{--lg:#a78bfa}
.lg-ev{--lg:#94a3b8}
.lg-q{--lg:#22d3ee}
.lg-gap{--lg:#fda4af}
.bg-play{pointer-events:auto;display:flex;align-items:center;gap:12px;flex:0 0 auto;margin-left:auto;
  background:rgba(10,14,28,.82);border:1px solid rgba(148,163,255,.2);border-radius:99px;
  padding:6px 14px 6px 6px;box-shadow:0 12px 32px rgba(0,0,0,.5);backdrop-filter:blur(6px)}
.bg-ring{position:relative;width:50px;height:50px;flex:0 0 auto;cursor:pointer;border:none;background:none;padding:0}
.bg-ring svg{width:100%;height:100%;display:block;transform:rotate(-90deg)}
.bg-ring .track{fill:none;stroke:rgba(148,163,255,.18);stroke-width:4}
.bg-ring .fill{fill:none;stroke:#c4b5fd;stroke-width:4;stroke-linecap:round;transition:stroke-dashoffset .25s}
.bg-ring .ico{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#e8ecff;font-size:14px}
.bg-play-info{display:flex;flex-direction:column;gap:5px;min-width:0}
.bg-play-row{display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.bg-play-turn{font-size:11px;color:#8a93ad}
.bg-play-turn b{color:#e6e9f5;font-weight:600}
.bg-phase{font-size:10.5px;padding:3px 10px;border-radius:99px;background:rgba(56,189,248,.14);color:#38bdf8;border:1px solid rgba(56,189,248,.35);white-space:nowrap}
.bg-diff{font-size:10.5px;padding:3px 10px;border-radius:99px;background:rgba(139,92,246,.14);color:#a78bfa;border:1px solid rgba(139,92,246,.35);white-space:nowrap}
.bg-diff b{color:#fff;margin-left:4px;font-weight:700}
.bg-diff-d1,.bg-diff-d2{background:rgba(52,211,153,.12);color:#34d399;border-color:rgba(52,211,153,.35)}
.bg-diff-d3{background:rgba(251,191,36,.12);color:#fbbf24;border-color:rgba(251,191,36,.35)}
.bg-diff-d4{background:rgba(251,146,60,.14);color:#fb923c;border-color:rgba(251,146,60,.4)}
.bg-diff-d5{background:rgba(251,113,133,.14);color:#fb7185;border-color:rgba(251,113,133,.4)}
.bg-range{flex:1;accent-color:#8b5cf6;height:4px;cursor:pointer}
.bg-turn{font-size:10.5px;color:#8a93ad;min-width:86px;text-align:right}
.bg-tip{position:fixed;z-index:90;pointer-events:none;max-width:320px;padding:10px 13px;font-size:12px;
  background:rgba(16,20,38,.92);border:1px solid rgba(148,163,184,.14);border-radius:12px;box-shadow:0 10px 30px rgba(0,0,0,.45)}

.bg-tip .tt{font-weight:700;margin-bottom:4px}
.bg-tip .ts{color:#8a93ad;font-size:11px;line-height:1.55}
.bg-tip .ts b{color:#cdd4e8}
.bg-loading{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#8a93ad;font-size:12px;letter-spacing:.1em}
.bg-detail{position:absolute;top:88px;right:14px;width:min(272px,78%);max-height:calc(100% - 104px);overflow:auto;
  background:rgba(10,14,28,.88);border:1px solid rgba(148,163,255,.22);border-radius:14px;
  padding:14px 16px;box-shadow:0 14px 40px rgba(0,0,0,.5);backdrop-filter:blur(8px);z-index:5}
.bg-detail h2{font-size:13px;font-weight:700;color:#e8ecff;margin:0 0 4px;padding-right:20px}
.bg-detail-x{position:absolute;top:8px;right:10px;background:none;border:none;color:#8a93ad;font-size:14px;cursor:pointer;line-height:1}
.bg-detail-x:hover{color:#fff}
.bg-metric{display:flex;justify-content:space-between;gap:10px;font-size:12px;margin:5px 0;color:#cdd4e8}
.bg-metric span{color:#8a93ad;white-space:nowrap}
.bg-metric b{color:#e8ecff;text-align:right;word-break:break-word}
.bg-layerbar{position:absolute;left:0;right:0;bottom:0;z-index:6;display:flex;gap:6px;align-items:center;
  overflow-x:auto;padding:10px 14px 12px;scrollbar-width:none;
  background:linear-gradient(0deg,rgba(5,7,15,.94),rgba(5,7,15,.5) 74%,transparent)}
.bg-layerbar::-webkit-scrollbar{display:none}
.bg-layerbar-title{font-size:9.5px;letter-spacing:.14em;text-transform:uppercase;color:#8a93ad;
  padding-right:4px;flex:0 0 auto}
.bg-layer{display:inline-flex;align-items:center;gap:6px;flex:0 0 auto;font-size:11px;color:#aab3cc;
  padding:5px 11px;border-radius:99px;border:1px solid rgba(148,163,255,.16);background:rgba(10,14,28,.7);
  cursor:pointer;transition:color .15s,border-color .15s,background .15s;white-space:nowrap}
.bg-layer:hover{color:#e8ecff;border-color:rgba(148,163,255,.4)}
.bg-layer.active{color:#0a0e1c;background:#e8ecff;border-color:#e8ecff;font-weight:700}
.bg-layer-dot{width:8px;height:8px;border-radius:50%;box-shadow:0 0 6px var(--ld,#888);background:var(--ld,#888)}
.bg-trail{display:flex;gap:6px;flex-wrap:wrap;margin:10px 0 4px;align-items:center}
.bg-trail-step{display:inline-flex;flex-direction:column;align-items:flex-start;gap:1px;cursor:pointer;
  padding:4px 9px;border-radius:10px;border:1px solid rgba(148,163,255,.16);background:rgba(10,14,28,.6);
  transition:border-color .15s,background .15s}
.bg-trail-step:hover{border-color:rgba(148,163,255,.5);background:rgba(10,14,28,.95)}
.bg-trail-v{font-size:12.5px;font-weight:700;color:#e8ecff}
.bg-trail-k{font-size:9px;letter-spacing:.08em;text-transform:uppercase;color:#8a93ad}
.bg-trail-arrow{color:#4b5478;font-size:12px}
.bg-note{font-size:11px;color:#8a93ad;line-height:1.55;margin:8px 0 2px}
.bg-list-item{font-size:11px;color:#fda4af;padding:4px 0;border-top:1px solid rgba(148,163,255,.08)}
.bg-list-item.ok{color:#86efac}
.bg-list-item::before{content:"— "}
@media (max-width:900px){
  .bg-card{grid-template-columns:minmax(0,1fr);grid-template-rows:auto;height:auto}
  .bg-aside{display:none}
  .bg-graph{grid-area:auto;min-height:420px;height:52vh}
}
`;

/* =========================================================================
   HELPERS
   ========================================================================= */
const r2 = (v: unknown) => Math.round((Number(v) || 0) * 100) / 100;

function normalize(raw: any): BrainData | null {
  if (!raw) return null;
  const hasLive = !!raw.interview_brain;
  let b: any, ds: any, rec: any, es: any, graph: any, hyps: any, summary: any, phases: any, diff: any, rawEdges: any;
  if (hasLive) {
    b = raw.interview_brain || {};
    ds = b.decision_state || {};
    rec = ds.hiring_recommendation || {};
    es = ds.evidence_sufficiency || {};
    graph = raw.evidence_graph || {};
    hyps = b.current_hypotheses || [];
    summary = b.evidence_summary || {};
    diff = (b.difficulty_profile || {}).level;
    phases = (raw.timeline || []).map((t: any) => ({
      n: t.question_number,
      phase: (t.event_data || {}).phase || "technical",
      difficulty: (t.event_data || {}).difficulty_level,
      evidence_count: (t.event_data || {}).evidence_count || 0,
    }));
    const g: any = graph.edges || {};
    rawEdges = Array.isArray(g)
      ? g.map((e: any) => ({ from: e.source, to: e.target, w: e.weight, support: !!e.support }))
      : Object.values(g).map((e: any) => ({ from: e.source, to: e.target, w: e.weight, support: !!e.support }));
  } else {
    rec = raw; es = raw.sufficiency || {};
    hyps = raw.hypotheses || [];
    summary = {};
    for (const c of raw.competencies || []) summary[c.id] = { average_score: c.avg, evidence_count: c.count, gap: c.gap, scores: c.scores || [] };
    diff = raw.difficulty_reached;
    phases = (raw.phases || []).map((t: any) => ({
      n: t.n,
      phase: t.phase || "technical",
      difficulty: t.difficulty != null ? t.difficulty : (t.difficulty_level ?? t.dif),
      evidence_count: t.evcount != null ? t.evcount : (t.evidence_count || 0),
    }));
    rawEdges = Array.isArray(raw.graph_edges) ? raw.graph_edges : [];
  }

  const competencies = Object.keys(summary).map((c: string) => ({
    id: c,
    avg: r2(summary[c].average_score != null ? summary[c].average_score : 0),
    count: summary[c].evidence_count || 0,
    gap: summary[c].gap != null ? r2(summary[c].gap) : 1,
    scores: ((graph && graph.nodes && graph.nodes[c] && graph.nodes[c].scores) || summary[c].scores || []).map((s: unknown) => r2(s)),
  }));

  const hypotheses = hyps.map((h: any) => ({
    id: h.id,
    status: h.status || "untested",
    confidence: !isNaN(Number(h.confidence)) ? Number(h.confidence) : (Number(h.probability) || 0),
    competency: h.competency,
    statement: h.statement || "",
    evidence: h.evidence_count != null ? h.evidence_count : (h.evidence || 0),
    required: h.required_evidence || 3,
  }));

  const evTotal = competencies.reduce((a: number, c: any) => a + (c.count || 0), 0);

  const gapComps: Array<{ id: string }> = [];
  const det = ((es as any).details || {}) as Record<string, any>;
  for (const cid of Object.keys(det)) {
    const dd = det[cid];
    if (!dd || dd.covered === true || dd.evidence_count > 0) continue;
    gapComps.push({ id: cid });
  }

  return {
    sid: raw.session_id || raw.sid,
    role: raw.role || raw.job_title || raw.position || (hasLive ? b.role || b.job_title || undefined : undefined),
    verdict: rec.verdict,
    composite: raw.composite != null ? raw.composite : rec.composite_score,
    confidence: raw.confidence != null ? raw.confidence : rec.confidence,
    coverage: raw.coverage != null ? raw.coverage : rec.coverage_ratio,
    difficulty: diff != null ? diff : rec.difficulty_reached,
    evidence_total: evTotal,
    hypotheses,
    competencies,
    gap_competencies: gapComps,
    graph_edges: rawEdges,
    phases,
    hypothesis_outcomes: raw.hypothesis_outcomes || (hasLive ? b.hypothesis_outcomes || undefined : undefined),
    sufficiency: es,
    layers: (hasLive ? b.brain_layers : (raw as any).brain_layers) || undefined,
  };
}

/* =========================================================================
   MODEL
   ========================================================================= */
function buildModel(m: BrainData) {
  const hypById = new Map((m.hypotheses as Array<{ id?: string }>).map((h) => [h.id, h]));
  const compById = new Map(m.competencies.map((c) => [c.id, c]));
  const nodes: GNode[] = [];
  const edges: GEdge[] = [];
  const index: Record<string, GNode> = {};

  function add(id: string, type: LayerType, level: number): GNode {
    if (index[id]) return index[id];
    const n: GNode = {
      id, type, lvl: level,
      x: 0, y: 0, vx: 0, vy: 0,
      r: 6, alpha: 1, glow: 0, pulse: 0, order: 0, phase: nodes.length * 1.7,
      lit: true, hidden: false, neighbors: new Set(),
    };
    nodes.push(n);
    index[id] = n;
    return n;
  }
  function link(a: GNode, b: GNode, w: number, sup?: boolean) {
    const e: GEdge = { a, b, w: Math.max(0.05, Math.min(1, w || 0.3)), sup: !!sup };
    edges.push(e);
    a.neighbors.add(b.id);
    b.neighbors.add(a.id);
    return e;
  }

  const core = add("__core__", "core", 0);
  core.r = 13;

  for (const c of m.competencies || []) {
    const n = add("comp:" + c.id, "comp", 1);
    n.cmeta = { avg: c.avg, count: c.count, gap: c.gap, scores: c.scores };
    const a = (c.avg || 0) > 1 ? (c.avg || 0) / 10 : (c.avg || 0);
    n.r = 3 + a * 5 + Math.min((c.count || 0) * 0.35, 1.4);
    n.ringR = 115;
    link(n, core, 0.5);
  }
  for (const g of m.gap_competencies || []) {
    if (index["comp:" + g.id]) continue;
    const n = add("comp:" + g.id, "comp", 1);
    n.cmeta = { avg: 0, count: 0, gap: 1, scores: [] };
    n.gapNode = true;
    n.r = 3;
    n.ringR = 115;
    n.alpha = 0.45;
  }
  for (const h of m.hypotheses || []) {
    const n = add("hyp:" + (h.id || "?"), "hyp", 2);
    n.hmeta = {
      status: h.status, confidence: h.confidence, statement: h.statement,
      evidence: h.evidence, required: h.required, competency: h.competency,
    };
    n.r = 3 + (h.confidence || 0) * 5;
    n.ringR = 190 - (h.confidence || 0) * 45;
    const comp = compById.get(h.competency || "");
    if (comp) link(n, index["comp:" + comp.id], 0.7);
  }
  const evByComp: Record<string, GNode[]> = {};
  for (const e of m.graph_edges || []) {
    const hyp = hypById.get(e.to || "");
    if (!hyp) continue;
    const cid: string = (hyp as any).competency || "?";
    let n = index["ev:" + e.from];
    if (!n) {
      n = add("ev:" + e.from, "ev", 3);
      n.emeta = { w: 0, sup: 0, hyp: e.to, comp: cid };
      n.hypId = e.to;
      n.compId = cid;
      (evByComp[cid] = evByComp[cid] || []).push(n);
    }
    n.emeta!.w = Math.max(n.emeta!.w, e.w || 0);
    n.emeta!.sup += e.support ? 1 : 0;
    n.r = 2.5 + (e.w || 0) * 3;
    n.ringR = 285 - (e.w || 0) * 70;
    link(n, index["hyp:" + hyp.id], e.w || 0.5, e.support);
  }
  for (const k in evByComp) evByComp[k].sort((p, q) => q.emeta!.w - p.emeta!.w);

  const evOrder = nodes.filter((x) => x.type === "ev").sort((p, q) => (p.id < q.id ? -1 : 1));
  let prev = 0, evIdx = 0;
  for (let i = 0; i < (m.phases || []).length; i++) {
    const t = m.phases[i];
    const cnt = t.evidence_count || 0;
    if (cnt <= prev) continue;
    const q = add("q:" + i, "q", 4);
    q.qmeta = { n: t.n, phase: t.phase || "technical", diff: t.difficulty, evcount: cnt, delta: cnt - prev, turnIdx: i, newEvs: [] };
    q.r = 3.5; q.ringR = 325;
    for (let k = 0; k < cnt - prev && evIdx < evOrder.length; k++) {
      const ev = evOrder[evIdx++];
      ev.evTurn = i;
      q.qmeta!.newEvs.push(ev.id);
      link(q, ev, 0.35);
    }
    prev = cnt;
  }

  return { nodes, edges, index, core, evTotal: m.evidence_total || 0 };
}

/* =========================================================================
   SIMULATION — circular rings + relaxed force layout
   ========================================================================= */
function placeRing(nodes: GNode[], rMin: number, rMax: number, jitter: number) {
  const n = nodes.length;
  const base = Math.random() * Math.PI * 2;
  nodes.forEach((nd, i) => {
    const r = rMin + (rMax - rMin) * (n <= 1 ? 0 : i / (n - 1));
    const a = (i / Math.max(1, n)) * Math.PI * 2 + base;
    nd.x = Math.cos(a) * r + (Math.random() - 0.5) * jitter;
    nd.y = Math.sin(a) * r + (Math.random() - 0.5) * jitter;
  });
}

const REP = 3800, DAMP = 0.86, SPRING = 0.5, RING_PULL = 0.09, GRAV = 0.006, VMAX = 26, V = VMAX;
const DISP = { node: 0.92, space: 1.0, edge: 0.7 };

function ringOf(lvl: number) {
  if (lvl === 1) return 115;
  if (lvl === 2) return 190;
  if (lvl === 3) return 285;
  return 0;
}

function relax(store: SimStore, elapsed: number, coef: number) {
  const ns = store.nodes, n = ns.length;
  for (let i = 0; i < n; i++) {
    for (let j = i + 1; j < n; j++) {
      const a = ns[i], b = ns[j];
      if (a.hidden || b.hidden) continue;
      let dx = a.x - b.x, dy = a.y - b.y;
      let d2 = dx * dx + dy * dy;
      if (d2 < 4) { const s = Math.random() - 0.5; dx += s; dy += Math.random() - 0.5; d2 = 4; }
      const d = Math.sqrt(d2);
      const minD = (a.r + b.r) * DISP.node + 14 * DISP.space;
      const f = d < minD ? (minD - d) * 6 * REP : REP / d2;
      const fx = dx / d * f, fy = dy / d * f;
      a.vx += fx * elapsed * coef; a.vy += fy * elapsed * coef;
      b.vx -= fx * elapsed * coef; b.vy -= fy * elapsed * coef;
    }
  }
  for (const e of store.edges) {
    if (e.a.hidden || e.b.hidden) continue;
    const dx = e.b.x - e.a.x, dy = e.b.y - e.a.y;
    const d = Math.max(1e-3, Math.sqrt(dx * dx + dy * dy));
    const f = (d - (120 - (e.w - 0.5) * 40) * DISP.space) * SPRING * (0.3 + e.w);
    const cross = e.a.lvl !== e.b.lvl && e.a.lvl > 0 && e.b.lvl > 0;
    if (cross) {
      for (const nd of [e.a, e.b]) {
        const rad = Math.hypot(nd.x, nd.y);
        if (rad < 1) continue;
        const tangX = -nd.y / rad, tangY = nd.x / rad;
        const comp = f * ((dx / d) * tangX + (dy / d) * tangY);
        nd.vx += tangX * comp * elapsed * coef;
        nd.vy += tangY * comp * elapsed * coef;
      }
      continue;
    }
    const fx = dx / d * f, fy = dy / d * f;
    e.a.vx += fx * elapsed * coef; e.a.vy += fy * elapsed * coef;
    e.b.vx -= fx * elapsed * coef; e.b.vy -= fy * elapsed * coef;
  }
  for (let k = 0; k < n; k++) {
    const nd = ns[k];
    if (nd.hidden) continue;
    if (nd === store.drag) { nd.vx = 0; nd.vy = 0; continue; }
    if (nd === store.core) { nd.vx *= DAMP * 0.5; nd.vy *= DAMP * 0.5; nd.x *= 0.85; nd.y *= 0.85; continue; }
    const targetR = (nd.ringR || ringOf(nd.lvl)) * DISP.space;
    const ang = Math.atan2(nd.y, nd.x);
    const rad = Math.sqrt(nd.x * nd.x + nd.y * nd.y) || 1;
    const radial = (targetR - rad) * RING_PULL;
    nd.vx += Math.cos(ang) * radial * elapsed * coef;
    nd.vy += Math.sin(ang) * radial * elapsed * coef;
    nd.vx -= nd.x * GRAV * elapsed * coef;
    nd.vy -= nd.y * GRAV * elapsed * coef;
    if (rad > targetR * 1.5) {
      nd.vx -= Math.cos(ang) * 60 * elapsed * coef;
      nd.vy -= Math.sin(ang) * 60 * elapsed * coef;
    }
    nd.vx *= Math.pow(DAMP, elapsed * 60);
    nd.vy *= Math.pow(DAMP, elapsed * 60);
    const sp = Math.hypot(nd.vx, nd.vy);
    if (sp > V) { nd.vx = nd.vx / sp * V; nd.vy = nd.vy / sp * V; }
    if (!isFinite(nd.vx) || !isFinite(nd.vy)) { nd.vx = 0; nd.vy = 0; }
    nd.x += nd.vx * elapsed;
    nd.y += nd.vy * elapsed;
  }
}

function relaxNow(store: SimStore, iterations: number) {
  for (let i = 0; i < iterations; i++) relax(store, 0.16, 1);
  relax(store, 0, 0);
}

function countLitForHyp(n: GNode, edges: GEdge[]) {
  let c = 0;
  for (const e of edges) if (e.b === n && e.a.type === "ev" && !e.a.hidden && e.a.lit) c++;
  return c;
}

function fitView(store: SimStore) {
  if (!store.nodes.length || !store.core) return;
  if (!store.WW || !store.WH) return;
  let maxR = 0;
  for (const n of store.nodes) {
    if (n.hidden) continue;
    const r = Math.hypot(n.x - store.core.x, n.y - store.core.y) + n.r * DISP.node + 26;
    if (r > maxR) maxR = r;
  }
  const R = Math.max(160, maxR);
  const w = R * 2, h = R * 2;
  const head = Math.min(88, store.WH * 0.28);
  store.cam.k = Math.max(0.12, Math.min(1.3, Math.min(store.WW * 0.78 / w, (store.WH - head) * 0.78 / h)));
  store.cam.x = store.WW / 2 - store.core.x * store.cam.k;
  store.cam.y = head + (store.WH - head) / 2 - store.core.y * store.cam.k;
}

function resetSim(store: SimStore, data: BrainData) {
  store.data = data;
  const model = buildModel(data);
  store.core = model.core;
  store.edges = model.edges;
  store.evTotal = model.evTotal;
  store.nodes = [];
  store.index = {};
  for (const n of model.nodes) {
    store.nodes.push(n);
    store.index[n.id] = n;
  }
  store.core.x = 0; store.core.y = 0;
  placeRing(model.nodes.filter((x) => x.type === "comp"), 95 * DISP.space, 135 * DISP.space, 12);
  placeRing(model.nodes.filter((x) => x.type === "hyp"), 165 * DISP.space, 215 * DISP.space, 22);
  placeRing(model.nodes.filter((x) => x.type === "ev"), 250 * DISP.space, 320 * DISP.space, 30);
  placeRing(model.nodes.filter((x) => x.type === "q"), 300 * DISP.space, 350 * DISP.space, 20);
  store.turns = data.phases || [];
  if (!store.turns.length) store.turns = [{ n: 1, phase: "technical", difficulty: 1, evidence_count: 0 }];
  store.cur = store.turns.length - 1;
}

/* =========================================================================
   TIMELINE
   ========================================================================= */
function applyTurn(store: SimStore, ti: number) {
  store.cur = Math.max(0, Math.min(store.turns.length - 1, ti));
  const t = store.turns[store.cur];
  const cum = t.evidence_count || 0;
  const total = Math.max(1, store.evTotal);
  const litCount = Math.round(store.evTotal * Math.min(1, cum / total));

  const litBy: Record<string, GNode[]> = {};
  const seen = new Set();
  for (const n of store.nodes) {
    if (n.type !== "ev") continue;
    if (seen.has(n.id)) continue;
    seen.add(n.id);
    const group = n.compId && store.index["comp:" + n.compId] ? n.compId : null;
    (litBy[group || "?"] = litBy[group || "?"] || []).push(n);
  }
  for (const k in litBy) {
    litBy[k].sort((p, q) => q.emeta!.w - p.emeta!.w);
    let on = 0;
    for (const n of litBy[k]) { if (on < litCount) { n.lit = true; on++; } else n.lit = false; }
  }

  for (const n of store.nodes) {
    if (n.type === "core") { n.alpha = 1; n.glow = 0.9; continue; }
    if (n.type === "comp") {
      const arr = litBy[n.id] || [];
      if (!arr.length) { n.alpha = 1; continue; }
      const on = arr.filter((x) => x.lit).length;
      n.alpha = Math.max(0.25, Math.min(1, on / arr.length));
      n.glow = n.alpha;
      continue;
    }
    if (n.type === "hyp") {
      const hyp = n.hmeta || {};
      const litEv = countLitForHyp(n, store.edges);
      const need = hyp.required || 3;
      n.alpha = Math.max(0.22, Math.min(1, need ? Math.min(1, litEv / need) : 0.5));
      if (hyp.status === "refuted") n.alpha = Math.min(n.alpha, 0.5);
      n.glow = hyp.status === "confirmed" && litEv >= need ? 0.9 : 0.3;
      n.pulse = hyp.status === "testing" || hyp.status === "untested" ? 1 : 0;
      continue;
    }
  }

  for (const n of store.nodes) {
    if (n.type === "q") {
      const q = n.qmeta || ({} as NonNullable<GNode["qmeta"]>);
      const show = (q.turnIdx ?? 1e9) <= store.cur;
      if (n.hidden !== !show) { n.hidden = !show; if (show) n.revealAt = performance.now() / 1000; }
      n.glow = q.turnIdx === store.cur ? 0.7 : 0.15;
      n.pulse = q.turnIdx === store.cur ? 1 : 0;
      continue;
    }
    if (n.type === "ev") {
      const show = (n.evTurn ?? 1e9) <= store.cur;
      if (n.hidden !== !show) { n.hidden = !show; if (show) n.revealAt = performance.now() / 1000; }
    }
  }
}

/* =========================================================================
   DRAW
   ========================================================================= */
const STAT_COLORS: Record<string, string> = {
  confirmed: "#34d399", refuted: "#fb7185", testing: "#38bdf8", untested: "#a78bfa",
};

function nodeColor(n: GNode) {
  if (n.type === "core") return "#fbbf24";
  if (n.type === "comp") return "#60a5fa";
  if (n.type === "q") return "#22d3ee";
  if (n.type === "hyp") return STAT_COLORS[(n.hmeta || {}).status || ""] || "#a78bfa";
  return "#94a3b8";
}

function toWorld(store: SimStore, x: number, y: number) {
  return { x: (x - store.cam.x) / store.cam.k, y: (y - store.cam.y) / store.cam.k };
}

function nodeAt(store: SimStore, wx: number, wy: number) {
  for (let i = store.nodes.length - 1; i >= 0; i--) {
    const n = store.nodes[i];
    if (n.hidden) continue;
    const dx = n.x - wx, dy = n.y - wy;
    if (dx * dx + dy * dy <= (n.r * DISP.node + 8 / store.cam.k) * (n.r * DISP.node + 8 / store.cam.k)) return n;
  }
  return null;
}

const compName = (id: string) => String(id || "").replace(/^(tech_|behav_)/, "").replace(/_/g, " ");
const label = (statement?: string) => {
  let s = String(statement || "").trim();
  s = s.replace(/^Candidate (has |demonstrates |is |was |uses? |communicates |shows |provides |builds |leads? )/i, "");
  s = s.replace(/\.?$/, "");
  return s.length > 46 ? s.slice(0, 45) + "…" : s;
};

/* =========================================================================
   THE 13 LAYERS — one connected graph viewed through thirteen lenses.
   Every layer is keyed to the same evidence / hypothesis / competency ids,
   so selecting a layer only re-focuses the existing graph (see layerFocus /
   edgeFocus) — it never opens a disconnected view.
   ========================================================================= */
interface LayerDef {
  key: string;
  name: string;
  desc: string;
  color: string;
}

const LAYER_DEFS: LayerDef[] = [
  { key: "decision_state", name: "Decision", desc: "verdict, confidence, review flags", color: "#fbbf24" },
  { key: "hypotheses", name: "Hypotheses", desc: "claims tested across the interview", color: "#a78bfa" },
  { key: "evidence_graph", name: "Evidence graph", desc: "supports / contradicts edges", color: "#94a3b8" },
  { key: "evidence_reading", name: "Answer reading", desc: "per-answer verifiability & specificity", color: "#38bdf8" },
  { key: "competency_graph", name: "Competency graph", desc: "scores, skills, coverage gaps", color: "#60a5fa" },
  { key: "calibration_state", name: "Calibration", desc: "raw vs calibrated score", color: "#34d399" },
  { key: "difficulty_state", name: "Difficulty", desc: "depth reached vs role floor", color: "#fb923c" },
  { key: "uncertainty_map", name: "Uncertainty", desc: "missing evidence per competency", color: "#fda4af" },
  { key: "contradiction_state", name: "Contradictions", desc: "conflicting evidence flags", color: "#fb7185" },
  { key: "question_strategy", name: "Question strategy", desc: "which competencies were probed", color: "#22d3ee" },
  { key: "candidate_memory", name: "Candidate memory", desc: "carried strengths & weaknesses", color: "#a3e635" },
  { key: "role_brain", name: "Role context", desc: "the job being evaluated", color: "#e2e8f0" },
  { key: "company_brain", name: "Company context", desc: "org, culture, tech stack", color: "#c4b5fd" },
];

/* Per-node dim factor for the active layer — everything else falls away so
   the chosen layer's slice of the one graph reads clearly. */
function layerFocus(store: SimStore, type: LayerType): number {
  const lk = store.layer;
  if (!lk) return 1;
  switch (lk) {
    case "decision_state":
    case "calibration_state":
      return type === "core" ? 1 : 0.3;
    case "hypotheses":
      return type === "hyp" ? 1 : 0.18;
    case "evidence_graph":
    case "evidence_reading":
      return type === "ev" ? 1 : type === "hyp" ? 0.5 : 0.18;
    case "competency_graph":
      return type === "comp" ? 1 : 0.18;
    case "difficulty_state":
    case "question_strategy":
      return type === "q" ? 1 : type === "ev" ? 0.4 : 0.2;
    case "uncertainty_map":
      return type === "comp" ? 1 : 0.2;
    case "contradiction_state":
      return type === "ev" ? 0.7 : 0.25;
    case "candidate_memory":
    case "role_brain":
    case "company_brain":
      return 0.45;
    default:
      return 1;
  }
}

function edgeFocus(store: SimStore, e: GEdge): number {
  const lk = store.layer;
  if (!lk) return 1;
  switch (lk) {
    case "contradiction_state":
      return e.sup ? 0.12 : 1;
    case "evidence_graph":
    case "evidence_reading":
      return e.a.type === "ev" || e.b.type === "ev" ? 1 : 0.25;
    case "hypotheses":
      return e.a.type === "hyp" || e.b.type === "hyp" ? 1 : 0.15;
    case "competency_graph":
      return e.a.type === "comp" || e.b.type === "comp" ? 1 : 0.2;
    case "difficulty_state":
    case "question_strategy":
      return e.a.type === "q" || e.b.type === "q" ? 1 : 0.15;
    case "decision_state":
    case "calibration_state":
      return 0.3;
    case "candidate_memory":
    case "role_brain":
    case "company_brain":
    case "uncertainty_map":
      return 0.3;
    default:
      return 1;
  }
}

/* Verdict trail — how the hiring summary was reached, step by step. Each step
   maps back to the layer that produced it. */
interface TrailStep {
  label: string;
  value: string;
  layer: string;
}

function buildTrail(d: BrainData | null): TrailStep[] {
  if (!d) return [];
  const layers = d.layers || {};
  const st: TrailStep[] = [];
  const s = (label: string, value: string, layer: string) => st.push({ label, value, layer });
  const confirmed = d.hypothesis_outcomes?.confirmed ?? d.hypotheses?.filter((h) => h.status === "confirmed").length ?? 0;
  s("evidence", String(d.evidence_total), "evidence_graph");
  s("confirmed", String(confirmed), "hypotheses");
  s("coverage", d.coverage != null ? Math.round(d.coverage * 100) + "%" : "—", "uncertainty_map");
  const cal: any = layers.calibration_state;
  s("calibrated", cal?.calibrated_score != null ? Number(cal.calibrated_score).toFixed(1) : (d.composite != null ? Number(d.composite).toFixed(1) : "—"), "calibration_state");
  const cs: any = layers.contradiction_state;
  const nContr = Array.isArray(cs?.contradictions) ? cs.contradictions.length : 0;
  if (nContr) s("contradictions", "−" + nContr, "contradiction_state");
  s("verdict", String(d.verdict ?? "—"), "decision_state");
  return st;
}

function draw(store: SimStore, ctx: CanvasRenderingContext2D, time: number) {
  const WW = store.WW, WH = store.WH;
  ctx.clearRect(0, 0, WW, WH);
  ctx.save();
  ctx.translate(store.cam.x, store.cam.y);
  ctx.scale(store.cam.k, store.cam.k);

  const hoverId = store.hover ? store.hover.id : null;
  const gx = store.core ? store.core.x : 0, gy = store.core ? store.core.y : 0;
  const cglow = ctx.createRadialGradient(gx, gy, 0, gx, gy, 760);
  cglow.addColorStop(0, "rgba(139,92,246,0.08)");
  cglow.addColorStop(0.45, "rgba(139,92,246,0.035)");
  cglow.addColorStop(1, "rgba(0,0,0,0)");
  ctx.fillStyle = cglow;
  ctx.beginPath(); ctx.arc(gx, gy, 760, 0, Math.PI * 2); ctx.fill();

  ctx.lineCap = "round";
  for (const e of store.edges) {
    if (e.a.hidden || e.b.hidden) continue;
    const hl = hoverId === e.a.id || hoverId === e.b.id;
    const isEv = e.a.type === "ev" || e.b.type === "ev";
    let c: string, al: number, dash: number[];
    if (isEv) {
      if (e.sup) { c = "52,211,153"; al = 0.8; dash = []; }
      else { c = "251,113,133"; al = 0.45; dash = [6, 5]; }
    } else {
      c = "148,163,190"; al = 0.4; dash = [];
    }
    ctx.setLineDash(dash);
    ctx.strokeStyle = "rgba(" + c + "," + al * (hl ? 1.25 : 1) * edgeFocus(store, e) + ")";
    ctx.lineWidth = Math.max(0.35, Math.min(1.5, (0.35 + e.w * 0.5) * (hl ? 1.3 : 1) * DISP.edge * Math.min(1 / store.cam.k, 1.4)));
    ctx.beginPath();
    ctx.moveTo(e.a.x, e.a.y);
    ctx.lineTo(e.b.x, e.b.y);
    ctx.stroke();
  }
  ctx.setLineDash([]);

  for (const n of store.nodes) {
    if (n.hidden) continue;
    const px = n.x, py = n.y;
    if (!isFinite(px) || !isFinite(py)) continue;
    const col = nodeColor(n);
    const r = n.r * DISP.node * (hoverId === n.id ? 1.45 : 1);
    const pulse = n.pulse ? (0.7 + 0.3 * Math.sin(time * 2.2 + (n.phase || 0))) : 0;
    const A = n.alpha * (hoverId === n.id ? 1 : 0.85) * layerFocus(store, n.type) * (n.revealAt != null ? Math.min(1, Math.max(0, (time - n.revealAt) / 0.35)) : 1);

    ctx.save();
    ctx.globalAlpha = A;
    const halo = r * (2.6 + pulse);
    if (!isFinite(halo)) { ctx.restore(); continue; }
    const grd = ctx.createRadialGradient(px, py, r * 0.2, px, py, halo);
    grd.addColorStop(0, col + "66");
    grd.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = grd;
    ctx.beginPath(); ctx.arc(px, py, halo, 0, Math.PI * 2); ctx.fill();
    ctx.shadowColor = col; ctx.shadowBlur = 14 + n.glow * 22;
    ctx.fillStyle = col;
    ctx.beginPath(); ctx.arc(px, py, r, 0, Math.PI * 2); ctx.fill();
    ctx.shadowBlur = 0;
    if (n.type === "core") {
      ctx.strokeStyle = "rgba(139,92,246,.5)";
      for (let i = 1; i <= 2; i++) {
        ctx.beginPath();
        ctx.arc(px, py, r + 9 * i + Math.sin(time * 0.8 + i) * 2.5, 0, Math.PI * 2);
        ctx.stroke();
      }
      ctx.fillStyle = "#fff";
      ctx.beginPath(); ctx.arc(px, py, r * 0.35, 0, Math.PI * 2); ctx.fill();
    }
    if (n.type === "comp" && n.cmeta && (n.cmeta.gap || 0) >= 0.3) {
      ctx.strokeStyle = "rgba(251,113,133,.65)";
      ctx.lineWidth = Math.max(0.4, Math.min(1.3, 0.5 * DISP.edge * Math.min(1 / store.cam.k, 1.4)));
      ctx.beginPath(); ctx.arc(px, py, r + 3.5, 0, Math.PI * 2); ctx.stroke();
    }
    ctx.restore();

    if (store.hover === n) {
      const nodeLabel =
        n.type === "comp" ? compName(n.id.replace("comp:", "")) :
          n.type === "hyp" ? (n.hmeta ? label(n.hmeta.statement) : "") :
            n.type === "core" ? "AURA" : "";
      if (nodeLabel) {
        ctx.save();
        ctx.globalAlpha = Math.min(1, n.alpha + 0.25);
        ctx.font = (n.type === "core" ? "700 " : "500 ") + Math.max(10, 12 / store.cam.k) + "px Segoe UI, sans-serif";
        ctx.fillStyle = n.type === "core" ? "#fcd34d" : "#b9c1da";
        ctx.textAlign = "center";
        ctx.fillText(nodeLabel, px, py + r + 16 / store.cam.k);
        ctx.restore();
      }
    }
  }

  if (store.sel && !store.sel.hidden) {
    const s = store.sel;
    ctx.save();
    ctx.strokeStyle = "rgba(251,191,36,.9)";
    ctx.lineWidth = 2 / store.cam.k;
    ctx.setLineDash([6 / store.cam.k, 4 / store.cam.k]);
    ctx.beginPath();
    ctx.arc(s.x, s.y, s.r * DISP.node + 12 / store.cam.k, 0, Math.PI * 2);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.restore();
  }
  ctx.restore();
}

/* =========================================================================
   TOOLTIP
   ========================================================================= */
function updateTip(store: SimStore, n: GNode | null, cx: number, cy: number): Tip | null {
  if (!n || !store.data) return null;
  let title = "", rows: [string, string][] = [];
  const d = store.data;
  if (n.type === "core") {
    title = "AURA decision";
    rows.push(
      ["verdict", String(d.verdict ?? "—")],
      ["composite", d.composite != null ? Number(d.composite).toFixed(1) : "—"],
      ["confidence", d.confidence != null ? Math.round(Number(d.confidence) * 100) + "%" : "—"],
      ["coverage", d.coverage != null ? Math.round(Number(d.coverage) * 100) + "%" : "—"],
      ["difficulty", d.difficulty != null ? "lvl " + d.difficulty + " / 5" : "—"],
    );
  } else if (n.type === "comp") {
    const c = n.cmeta || {};
    title = compName(n.id.replace("comp:", ""));
    if (n.gapNode) {
      rows.push(
        ["status", "not probed"],
        ["evidence", "0"],
        ["gap", "uncovered competency"],
      );
    } else {
      rows.push(
        ["avg score", String(c.avg ?? "—")],
        ["evidence", String(c.count ?? "—")],
        ["gap", String(c.gap ?? "—")],
        ["scores", (c.scores || []).join(" · ") || "—"],
      );
    }
  } else if (n.type === "hyp") {
    const h = n.hmeta || {};
    title = h.statement || "hypothesis";
    rows.push(
      ["status", h.status || "—"],
      ["confidence", String(h.confidence ?? "—")],
      ["evidence", (h.evidence ?? 0) + " / " + (h.required || 3) + " req"],
    );
  } else if (n.type === "ev") {
    const m = n.emeta || { w: 0, sup: 0 };
    title = "evidence " + n.id.slice(3, 9);
    rows.push(
      ["weight", String(m.w)],
      ["support", m.sup > 0 ? "supporting" : "against"],
    );
  } else if (n.type === "q") {
    const q = n.qmeta || ({} as NonNullable<GNode["qmeta"]>);
    title = "question " + (q.n || "—");
    rows.push(
      ["phase", q.phase || "—"],
      ["difficulty", q.diff != null ? "lvl " + q.diff + " / 5" : "—"],
      ["evidence so far", String(q.evcount ?? "—")],
      ["new evidence", String(q.delta ?? "—")],
    );
  }
  const w = Math.min(window.innerWidth - 96, Math.max(180, cx + 14));
  const h = Math.min(window.innerHeight - 96, Math.max(140, cy + 14));
  return { title, rows, x: w, y: h };
}

/* =========================================================================
   NODE DETAIL (click to select → extra info panel on the graph)
   ========================================================================= */
const detailTitle = (n: GNode): string => {
  if (n.type === "core") return "AURA decision";
  if (n.type === "comp") return compName(n.id.replace(/^comp:/, ""));
  if (n.type === "hyp") return "Hypothesis";
  if (n.type === "q") return "Question " + (n.qmeta?.n ?? "—");
  return "Evidence " + n.id.slice(3, 9);
};

function detailRows(n: GNode, store: SimStore): [string, string][] {
  const mRow = (k: string, v: unknown): [string, string] => [k, v != null ? String(v) : "—"];
  const d = store.data;
  if (n.type === "core") {
    return [
      mRow("verdict", d?.verdict),
      mRow("composite score", d?.composite != null ? Number(d.composite).toFixed(1) : null),
      mRow("confidence", d?.confidence != null ? Math.round(Number(d.confidence) * 100) + "%" : null),
      mRow("coverage ratio", d?.coverage != null ? Math.round(Number(d.coverage) * 100) + "%" : null),
      mRow("difficulty reached", d?.difficulty != null ? "lvl " + d.difficulty + " / 5" : null),
      mRow("evidence total", store.evTotal),
      mRow("hypotheses", store.nodes.filter(x => x.type === "hyp").length),
      mRow("phases", store.turns.map(t => t.phase).filter(Boolean).join(" → ")),
    ];
  }
  if (n.type === "comp") {
    const c = n.cmeta || {};
    if (n.gapNode) {
      return [
        ["status", "not probed"],
        ["evidence items", "0"],
        ["gap", "uncovered competency"],
        ["suggestion", "add a question for this competency"],
      ];
    }
    return [
      mRow("average score", c.avg),
      mRow("evidence items", c.count),
      mRow("gap", c.gap),
      mRow("scores", (c.scores || []).join(" · ")),
    ];
  }
  if (n.type === "hyp") {
    const h = n.hmeta || {};
    const qs = new Set<string>();
    for (const e of store.edges) {
      if (e.b !== n || e.a.type !== "ev") continue;
      const qe = store.edges.find(x => (x.a === e.a && x.b.type === "q") || (x.b === e.a && x.a.type === "q"));
      if (qe) {
        const qn = (qe.a.type === "q" ? qe.a : qe.b).qmeta;
        if (qn && qn.n != null) qs.add("Q" + qn.n);
      }
    }
    return [
      ["statement", h.statement || "—"],
      mRow("status", h.status),
      mRow("confidence", h.confidence),
      mRow("evidence", (h.evidence ?? 0) + " / " + (h.required || 3) + " required"),
      mRow("competency", compName(h.competency || "")),
      mRow("questions tested", [...qs].sort((a, b) => Number(a.slice(1)) - Number(b.slice(1))).join(" · ")),
    ];
  }
  if (n.type === "q") {
    const q = n.qmeta || ({} as NonNullable<GNode["qmeta"]>);
    return [
      mRow("phase", q.phase),
      mRow("difficulty", q.diff != null ? "lvl " + q.diff + " / 5" : null),
      mRow("evidence at this point", q.evcount),
      mRow("new evidence", q.delta),
      mRow("evidence ids", (q.newEvs || []).map(id => id.slice(3, 9)).join(" · ")),
    ];
  }
  const m = n.emeta || { w: 0, sup: 0 };
  return [
    mRow("weight", m.w),
    mRow("support", m.sup > 0 ? "supporting" : "against"),
  ];
}

/* =========================================================================
   LAYER DETAIL — what each of the 13 layers contains, rendered as a card.
   Keyed to the same ids as the graph nodes; each section ends with a short
   "so what" note tying it into the hiring summary.
   ========================================================================= */
interface LayerSection {
  rows: Array<[string, string]>;
  notes: string[];
}

function layerSections(key: string, d: BrainData | null): LayerSection[] {
  if (!d) return [];
  const L: any = (d.layers || {})[key];
  const scalar = (v: unknown): string | null => {
    if (v == null || v === "") return null;
    if (typeof v === "string" || typeof v === "number" || typeof v === "boolean") return String(v);
    try { return JSON.stringify(v); } catch { return null; }
  };
  const pct = (v: unknown) => (v != null && !isNaN(Number(v)) ? Math.round(Number(v) * 100) + "%" : "—");
  const n = (v: unknown) => scalar(v) ?? "—";
  const sects: LayerSection[] = [];
  const sec = (rows: Array<[string, string]>, notes: string[] = []) => sects.push({ rows, notes });

  if (!L) {
    sec([["source", "embedded snapshot"]], ["This layer streams in with the live brain — open /brain-graph to see it."]);
    return sects;
  }

  switch (key) {
    case "decision_state":
      sec([
        ["decision", n(L.decision)],
        ["decision score", n(L.decision_score)],
        ["calibrated score", n(L.calibrated_score)],
        ["confidence", pct(L.confidence)],
        ["recommendation", n(L.recommendation_verdict)],
      ], Array.isArray(L.risk_flags) ? L.risk_flags.map((f: unknown) => String(f)) : []);
      break;
    case "hypotheses": {
      const hyps = d.hypotheses || [];
      const cnt = (s: string) => hyps.filter((h) => h.status === s).length;
      sec([
        ["total", n(hyps.length)],
        ["confirmed", n(cnt("confirmed"))],
        ["testing", n(cnt("testing"))],
        ["untested", n(cnt("untested"))],
      ], ["Each claim needs enough supporting evidence to be confirmed; untested claims stay dim."]);
      break;
    }
    case "evidence_graph": {
      const edges = (L.edges && typeof L.edges === "object" ? Object.values(L.edges) : []) as any[];
      const isSup = (e: any) => e.relation === "supports" || e.support === true;
      const isCon = (e: any) => e.relation === "contradicts" || e.support === false;
      const sup = edges.filter(isSup).length;
      const con = edges.filter(isCon).length;
      sec([
        ["evidence items", n(d.evidence_total)],
        ["supporting edges", n(sup)],
        ["contradicting edges", n(con)],
      ], ["The spine of the brain — every score traces to the evidence that supports or contradicts it."]);
      break;
    }
    case "evidence_reading": {
      const pa = (L.per_answer && typeof L.per_answer === "object" ? Object.values(L.per_answer) : []) as any[];
      const v = pa.filter((a: any) => a.verifiable).length;
      const demo = pa.filter((a: any) => a.claim_classification === "demonstrated").length;
      const off = L.off_rubric || {};
      const flags = [...(off.red_flags || []), ...(off.hidden_strengths || [])];
      sec([
        ["answers read", n(pa.length)],
        ["verifiable", n(v)],
        ["demonstrated", n(demo)],
      ], flags.length ? flags.map((f: unknown) => String(f)) : ["The engine reads each answer for verifiability and specificity — vague claims get flagged, not trusted."]);
      break;
    }
    case "competency_graph": {
      const cg = d.competencies || [];
      const gap = cg.filter((c) => (c.gap ?? 1) >= 0.3 || !c.count).length;
      sec([
        ["competencies", n(cg.length)],
        ["with gaps", n(gap)],
        ["avg score", d.composite != null ? Number(d.composite).toFixed(1) : "—"],
      ], ["Gaps are competencies with little or no evidence — they hold the verdict back."]);
      break;
    }
    case "calibration_state": {
      const er: any = ((d.layers || {}).evidence_reading || {}).per_answer || {};
      const pa = (typeof er === "object" ? Object.values(er) : []) as any[];
      const cc = (s: string) => pa.filter((a: any) => a.claim_classification === s).length;
      sec([
        ["raw composite", n(L.raw_composite)],
        ["calibrated score", n(L.calibrated_score)],
        ["calibrated verdict", n(L.calibrated_verdict)],
        ["proof ratio", pct(L.proof_ratio)],
        ["claims", cc("proven") + " proven · " + cc("demonstrated") + " demonstrated · " + cc("mentioned") + " mentioned"],
        ["contradiction penalty", n(L.contradiction_penalty)],
        ["decision confidence", pct(L.decision_confidence)],
      ], ["Proof ratio counts only claims that clear the deterministic floor — the semantic read can confirm or downgrade, never inflate. " + cc("demonstrated") + " of " + pa.length + " answers read as demonstrated but carried no first-person ownership signal."]);
      break;
    }
    case "difficulty_state":
      sec([
        ["role floor", n(L.role_floor)],
        ["difficulty reached", n(L.difficulty_reached)],
        ["evidence total", n(L.evidence_total)],
        ["floor satisfied", n(L.floor_satisfied)],
      ], ["The interview only scores depth up to what the role demands. Evidence depth (low/medium/high) is reported by the calibration layer."]);
      break;
    case "uncertainty_map": {
      const rows: Array<[string, string]> = [];
      for (const [cid, vv] of Object.entries(L)) {
        const v = vv as any;
        if (typeof v !== "object" || !v) continue;
        rows.push([compName(cid), pct(v.uncertainty) + " · miss " + ((v.missing_evidence || []).length || 0)]);
      }
      sec(rows, ["Competencies with high uncertainty or missing evidence are where the graph stays unlit."]);
      break;
    }
    case "contradiction_state": {
      const list = Array.isArray(L.contradictions) ? L.contradictions : [];
      const sev: Record<string, number> = {};
      for (const c of list) sev[c.severity] = (sev[c.severity] || 0) + 1;
      const sr: any = L.seniority_risk || {};
      const riskLabel = [n(sr.level), n(sr.action), sr.proven_claims != null ? "proven " + sr.proven_claims + "/" + (d.evidence_total || "—") : null].filter(Boolean).join(" · ") || "—";
      sec([
        ["flags", n(list.length)],
        ["severities", n(Object.entries(sev).map(([k, v]) => k + "×" + v).join(", "))],
        ["seniority risk", riskLabel],
        ["needs challenge", n(L.needs_challenge)],
      ], ["Contradicting evidence is the red dashed edges — it triggers the review step that trims confidence."]);
      break;
    }
    case "question_strategy":
      sec([
        ["planned competency", n(L.planned_competency)],
      ], [n(L.rationale || L.next_question_strategy || "Questions target the competencies with the largest open gaps.")]);
      break;
    case "candidate_memory": {
      const rows: Array<[string, string]> = [["interviews", n(L.interview_count)]];
      sec(rows, [...(L.learned_strengths || []).map((s: unknown) => "strength: " + s), ...(L.learned_weaknesses || []).map((s: unknown) => "weakness: " + s)]);
      break;
    }
    case "role_brain":
      sec([
        ["role", n(L.role)],
        ["seniority", n(L.seniority)],
        ["floor", n(L.seniority_floor)],
        ["competencies", n((L.critical_competencies || []).length)],
      ], [String(L.mission || "")]);
      break;
    case "company_brain":
      sec([
        ["job role", n(L.job_role)],
        ["tech stack", n((L.tech_stack || []).join(", "))],
      ], [String(L.summary || L.mission || "")]);
      break;
    default:
      sec([["layer", n(key)]], []);
  }
  return sects;
}

function renderLayerPanel(key: string, d: BrainData | null) {
  if (!d) return null;
  const def = LAYER_DEFS.find((x) => x.key === key);
  const sects = layerSections(key, d);
  return (
    <>
      <h2>{def?.name || key}</h2>
      <div className="bg-note">{def?.desc}</div>
      {sects.map((s, i) => (
        <div key={i}>
          {s.rows.map(([k, v]) => (
            <div className="bg-metric" key={k}><span>{k}</span><b>{v}</b></div>
          ))}
          {s.notes.map((note, j) => (
            <div className="bg-list-item" key={j}>{note}</div>
          ))}
        </div>
      ))}
    </>
  );
}

/* =========================================================================
   COMPONENT
   ========================================================================= */
export default function BrainGraph({ sid, title, snapshot }: { sid?: string; title?: string; snapshot?: EmbeddedBrain } = {}) {
  const liveSid = sid || DEFAULT_SID;
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const cardRef = useRef<HTMLDivElement>(null);
  const storeRef = useRef<SimStore | null>(null);
  const [ready, setReady] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [bar, setBar] = useState({ cur: 1, total: 1, phase: "", ev: "—", diff: "—" });
  const [hud, setHud] = useState<BrainData | null>(null);
  const [tip, setTip] = useState<Tip | null>(null);
  const [sel, setSel] = useState<GNode | null>(null);
  const [layer, setLayer] = useState<string | null>(null);

  const playTimer = useRef<number | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const store: SimStore = {
      data: null, nodes: [], edges: [], index: {}, core: null,
      cam: { x: 0, y: 0, k: 1 }, turns: [], cur: 0, hover: null, drag: null, sel: null,
      WW: 0, WH: 0, DPR: 1, evTotal: 0, layer: null,
    };
    storeRef.current = store;

    const resize = () => {
      const parent = canvas.parentElement;
      store.WW = canvas.clientWidth || (parent ? parent.clientWidth : 0);
      store.WH = canvas.clientHeight || (parent ? parent.clientHeight : 0);
      store.DPR = Math.min(2, window.devicePixelRatio || 1);
      canvas.width = Math.max(1, Math.round(store.WW * store.DPR));
      canvas.height = Math.max(1, Math.round(store.WH * store.DPR));
      ctx.setTransform(store.DPR, 0, 0, store.DPR, 0, 0);
    };
    resize();

    let raf = 0;

    let cancelled = false;
    const load = async () => {
      let data: BrainData | null;
      if (snapshot) {
        data = normalize(snapshot);
      } else {
        data = normalize(EMBEDDED);
        try {
          const raw = await apiClient.get(`/api/v1/intelligence/brain/${encodeURIComponent(liveSid)}`);
          const live = normalize(raw);
          /* only trust live data when it actually carries a brain — an empty
             session (no hypotheses / timeline / edges) must not blank out the
             embedded snapshot */
          if (live && (live.hypotheses?.length > 0 || live.competencies?.length > 0) &&
              (live.phases?.length > 0 || live.graph_edges?.length > 0)) data = live;
        } catch {
          /* fall back to the embedded snapshot of the same session */
        }
      }
      if (cancelled || !data) return;
      resetSim(store, data);
      relaxNow(store, 60);
      setHud(data);
      setReady(true);
      applyTurn(store, store.cur);
      syncBar();

      /* fit the graph centered in the box — retry until the canvas actually has
         layout size (on the very first mount it can still be 0×0) */
      const fitCentered = () => {
        resize();
        if (store.WW > 20 && store.WH > 20 && store.nodes.length) fitView(store);
        else raf = requestAnimationFrame(fitCentered);
      };
      fitCentered();
    };
    load();

    const ro = new ResizeObserver(() => {
      resize();
      fitView(store);
    });
    ro.observe(canvas);
    const onWinResize = () => {
      resize();
      fitView(store);
    };
    window.addEventListener("resize", onWinResize);

    let last = performance.now();
    const loop = (now: number) => {
      raf = requestAnimationFrame(loop);
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      relax(store, dt, 0.06);
      draw(store, ctx, now / 1000);
    };
    raf = requestAnimationFrame(loop);

    return () => {
      cancelled = true;
      cancelAnimationFrame(raf);
      ro.disconnect();
      window.removeEventListener("resize", onWinResize);
      if (playTimer.current != null) { clearInterval(playTimer.current); playTimer.current = null; }
      storeRef.current = null;
    };
  }, [liveSid]);

  /* keep React bar state in sync with the sim's current turn */
  const syncBar = () => {
    const store = storeRef.current;
    if (!store || !store.turns.length) return;
    const t = store.turns[store.cur];
    setBar({
      cur: store.cur + 1,
      total: store.turns.length,
      phase: t.phase || "technical",
      ev: t.evidence_count + " / " + store.evTotal,
      diff: t.difficulty != null ? String(t.difficulty) : "—",
    });
  };

  const togglePlay = () => {
    const store = storeRef.current;
    if (!store) return;
    if (playTimer.current != null) {
      clearInterval(playTimer.current);
      playTimer.current = null;
      setPlaying(false);
      return;
    }
    setPlaying(true);
    playTimer.current = window.setInterval(() => {
      const s = storeRef.current;
      if (!s) { clearInterval(playTimer.current!); playTimer.current = null; setPlaying(false); return; }
      if (s.cur >= s.turns.length - 1) {
        s.cur = 0;
      } else {
        s.cur++;
      }
      applyTurn(s, s.cur);
      syncBar();
    }, 1600);
  };

  const pointer = useRef<{ mode: "idle" | "drag" | "pan"; sx: number; sy: number; cx: number; cy: number; hit: GNode | null; moved: boolean }>({ mode: "idle", sx: 0, sy: 0, cx: 0, cy: 0, hit: null, moved: false });

  const canvasPoint = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current!;
    const rect = canvas.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  };

  const selectNode = (n: GNode | null) => {
    const store = storeRef.current;
    if (store) { store.sel = n; if (n) store.layer = null; }
    setSel(n);
    if (n) setLayer(null);
  };

  const selectLayer = (key: string | null) => {
    const store = storeRef.current;
    if (store) { store.layer = key; if (key) store.sel = null; }
    setLayer(key);
    if (key) setSel(null);
  };

  const closeOverlay = () => {
    selectNode(null);
    selectLayer(null);
  };

  const onPointerDown = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const store = storeRef.current;
    const cv = canvasRef.current;
    if (!store || !cv) return;
    const p = canvasPoint(e);
    const w = toWorld(store, p.x, p.y);
    const n = nodeAt(store, w.x, w.y);
    pointer.current = { mode: n ? "drag" : "pan", sx: p.x, sy: p.y, cx: store.cam.x, cy: store.cam.y, hit: n, moved: false };
    if (n) {
      store.drag = n;
    }
    cv.classList.add("bg-dragging");
  };

  const onPointerMove = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const store = storeRef.current;
    if (!store) return;
    const p = canvasPoint(e);
    const w = toWorld(store, p.x, p.y);
    const pr = pointer.current;
    if (pr.mode !== "idle" && Math.hypot(p.x - pr.sx, p.y - pr.sy) > 5) pr.moved = true;
    if (pr.mode === "drag" && store.drag) {
      const nd = store.drag;
      nd.x = w.x; nd.y = w.y; nd.vx = 0; nd.vy = 0;
      return;
    }
    if (pr.mode === "pan") {
      store.cam.x = pr.cx + (p.x - pr.sx);
      store.cam.y = pr.cy + (p.y - pr.sy);
      return;
    }
    const n = nodeAt(store, w.x, w.y);
    if (n !== store.hover) {
      store.hover = n;
      setTip(updateTip(store, n, e.clientX, e.clientY));
    } else if (n) {
      setTip(updateTip(store, n, e.clientX, e.clientY));
    }
  };

  const onPointerUp = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const store = storeRef.current;
    if (!store) return;
    const pr = pointer.current;
    const p = canvasPoint(e);
    const moved = pr.moved || Math.hypot(p.x - pr.sx, p.y - pr.sy) > 5;
    const wasIdle = pr.mode === "idle";
    pointer.current = { mode: "idle", sx: pr.sx, sy: pr.sy, cx: 0, cy: 0, hit: null, moved: false };
    store.drag = null;
    const canvas = canvasRef.current;
    if (canvas) canvas.classList.remove("bg-dragging");
    if (wasIdle || moved) return;
    if (pr.hit) {
      selectNode(store.sel === pr.hit ? null : pr.hit);
    } else {
      selectNode(null);
    }
  };

  const onPointerLeave = () => {
    const store = storeRef.current;
    if (!store) return;
    store.hover = null;
    setTip(null);
  };

  const hudText = (v: unknown, suffix = "") => (v != null ? String(v) + suffix : "—");

  const circ = 2 * Math.PI * 19;
  const progress = bar.total > 1 ? Math.min(1, Math.max(0, (bar.cur - 1) / (bar.total - 1))) : 1;
  const ringCol = { "1": "#34d399", "2": "#34d399", "3": "#fbbf24", "4": "#fb923c", "5": "#fb7185" }[bar.diff] || "#c4b5fd";

  return (
    <div className="bg-card" ref={cardRef}>
      <style>{CSS}</style>
      <div className="bg-panel bg-graph">
      <div className="bg-head">
        <div className="bg-head-main">
          <div className="bg-head-title">{title || "Interview Evidence Graph"}</div>
          <div className="bg-head-sub">
            {hud
              ? hud.competencies.length + " competencies · " + (hud.gap_competencies || []).length + " uncovered · " + hud.hypotheses.length + " hypotheses · " + hud.evidence_total + " evidence · " + hud.phases.length + " turns"
              : "building the graph…"}
          </div>
          <div className="bg-legend">
            <span className="lg lg-core">core</span>
            <span className="lg lg-comp">competency</span>
            <span className="lg lg-hyp">hypothesis</span>
            <span className="lg lg-ev">evidence</span>
            <span className="lg lg-q">question</span>
            <span className="lg lg-gap">uncovered</span>
          </div>
        </div>
        <div className="bg-play">
          <button className="bg-ring" onClick={togglePlay} title="play / pause replay">
            <svg viewBox="0 0 44 44">
              <circle className="track" cx="22" cy="22" r="19" />
              <circle
                className="fill"
                cx="22" cy="22" r="19"
                strokeDasharray={circ}
                strokeDashoffset={circ * (1 - progress)}
                style={{ stroke: ringCol }}
              />
            </svg>
            <span className="ico">{playing ? "⏸" : "▶"}</span>
          </button>
          <div className="bg-play-info">
            <div className="bg-play-row">
              <span className="bg-phase">{bar.phase}</span>
              <span className={"bg-diff" + (bar.diff !== "—" ? " bg-diff-d" + bar.diff : "")}>d{bar.diff}</span>
            </div>
            <span className="bg-play-turn">turn <b>{bar.cur}</b> / {bar.total}</span>
          </div>
        </div>
      </div>
      <canvas
          ref={canvasRef}
          className="bg-canvas"
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerLeave={onPointerLeave}
        />
        {!ready && <div className="bg-loading">LOADING BRAIN…</div>}
        {(sel || layer) && (
          <div className="bg-detail">
            <button className="bg-detail-x" onClick={closeOverlay} title="close">✕</button>
            {sel ? (
              <>
                <h2>{detailTitle(sel)}</h2>
                {detailRows(sel, storeRef.current!).map(([k, v], i) => (
                  <div className="bg-metric" key={i}>
                    <span>{k}</span>
                    <b>{v}</b>
                  </div>
                ))}
              </>
            ) : layer ? (
              renderLayerPanel(layer, hud)
            ) : null}
          </div>
        )}
        <div className="bg-layerbar">
          <span className="bg-layerbar-title">13 layers</span>
          {LAYER_DEFS.map((l) => (
            <button
              key={l.key}
              className={"bg-layer" + (layer === l.key ? " active" : "")}
              onClick={() => selectLayer(layer === l.key ? null : l.key)}
              title={l.desc}
            >
              <span className="bg-layer-dot" style={{ "--ld": l.color } as React.CSSProperties} />
              {l.name}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-aside">
        <aside className="bg-panel bg-info">
          <h1 className="bg-title">AURA V5 · Interview Brain</h1>
          <div className="bg-role">{hud?.role || "Role not specified"}</div>
          <div className="bg-sid">session {hud?.sid || "—"}</div>
          <div className="bg-verdict">
            <span className={"bg-chip bg-chip-" + String(hud?.verdict || "borderline").toLowerCase().replace(/\s+/g, "_")}>
              {hud?.verdict || "—"}
            </span>
            <span style={{ fontSize: 12, color: "#8a93ad" }}>final verdict</span>
          </div>
          <div className="bg-stats">
            <span className="k">composite</span><b className="v">{hudText(hud?.composite != null ? Number(hud.composite).toFixed(1) : null)}</b>
            <span className="k">confidence</span><b className="v">{hudText(hud?.confidence != null ? Math.round(Number(hud.confidence) * 100) + "%" : null)}</b>
            <span className="k">coverage</span><b className="v">{hudText(hud?.coverage != null ? Math.round(Number(hud.coverage) * 100) + "%" : null)}</b>
            <span className="k">difficulty</span><b className="v hot">{hudText(hud?.difficulty != null ? "lvl " + hud.difficulty + " / 5" : null)}</b>
            <span className="k">evidence</span><b className="v">{hud?.evidence_total || 0} / {hud?.evidence_total || 0}</b>
            <span className="k">hyps</span><b className="v">{hud?.hypotheses?.length || 0}</b>
          </div>
        </aside>

        <aside className="bg-panel bg-hiring">
          <h1 className="bg-title">Hiring Summary</h1>
          <div className="bg-trail">
            {buildTrail(hud).map((s, i) => (
              <React.Fragment key={s.layer + "-" + i}>
                {i > 0 && <span className="bg-trail-arrow">→</span>}
                <button className="bg-trail-step" onClick={() => selectLayer(s.layer)} title={"focus the " + s.label + " layer"}>
                  <span className="bg-trail-v">{s.value}</span>
                  <span className="bg-trail-k">{s.label}</span>
                </button>
              </React.Fragment>
            ))}
          </div>
          <div className="bg-verdict">
            <span className={"bg-chip bg-chip-" + String(hud?.sufficiency?.severity || "borderline").toLowerCase().replace(/\s+/g, "_")}>
              {hud?.sufficiency?.severity || "—"}
            </span>
            <span style={{ fontSize: 12, color: "#8a93ad" }}>evidence sufficiency</span>
          </div>
          <div className="bg-stats">
            <span className="k">hiring verdict</span><b className="v">{hud?.verdict || "—"}</b>
            <span className="k">sufficient</span><b className="v">{hud?.sufficiency?.is_sufficient != null ? (hud.sufficiency.is_sufficient ? "yes" : "no") : "—"}</b>
            <span className="k">remaining gaps</span><b className="v">{hud?.sufficiency?.remaining_gaps ?? "—"}</b>
            <span className="k">coverage</span><b className="v">{hudText(hud?.coverage != null ? Math.round(Number(hud.coverage) * 100) + "%" : null)}</b>
            <span className="k">hyps confirmed</span><b className="v">{hud?.hypothesis_outcomes?.confirmed ?? "—"}</b>
            <span className="k">hyps refuted</span><b className="v">{hud?.hypothesis_outcomes?.refuted ?? "—"}</b>
            <span className="k">hyps unanswered</span><b className="v">{hud?.hypothesis_outcomes?.unanswered ?? "—"}</b>
          </div>
        </aside>
      </div>

      {tip && (
        <div className="bg-tip" style={{ left: tip.x, top: tip.y }}>
          <div className="tt">{tip.title}</div>
          <div className="ts">
            {tip.rows.map(([k, v], i) => (
              <span key={i}>
                {i > 0 && " · "}
                <b>{k}:</b> {v}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
