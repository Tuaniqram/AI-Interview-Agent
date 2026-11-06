import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Layers, Play, Brain, GitBranch, ShieldCheck, ListChecks, Sparkles, Workflow, MessageSquare, Building2, UserRound, BarChart3 } from 'lucide-react';
import BrainGraph from '../components/graph/BrainGraph';
import { REAL_CANDIDATES, type RealCandidate, type RealStep } from '../data/realInterviews';
import { BRAIN_SNAPSHOTS } from '../data/brainSnapshots';

/* ════════════════════════════════════════════════════════════════════════
   Landing - AURA evidence-first interviews + the live Brain Graph.
   Glass UI: aurora orbs behind frosted panels (backdrop blur + saturate),
   hairline borders with an inner highlight, layered translucency.
   Scoped styles: every selector is prefixed with .engine-landing.
   ════════════════════════════════════════════════════════════════════════ */

const EL = '.engine-landing';

const styles = `
${EL} {
  --el-page: #f6f7f4; --el-text: #17201d; --el-secondary: #3d4a44; --el-muted: #5a6660;
  --el-accent: #0c6b58; --el-accent-hover: #085244; --el-accent-soft: rgba(12,107,88,0.10);
  --el-success: #0c7a54; --el-warning: #b45309; --el-error: #dc2626; --el-info: #2563eb;
  --el-glass: #ffffff; --el-glass-2: #fbfcfa;
  --el-glass-border: #e2e6e1; --el-glass-border-hi: #c9d1cb;
  --el-blur: none;
  --el-glass-shadow: 0 1px 2px rgba(23,32,29,0.05), 0 8px 24px rgba(23,32,29,0.06);
  --el-radius: 12px;
  background: var(--el-page); color: var(--el-text); line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}
body.engine-landing { margin: 0; background: var(--el-page); }
html:has(body.engine-landing) { background: var(--el-page); }
${EL} h1, ${EL} h2, ${EL} h3, ${EL} h4 { font-family: 'Archivo', sans-serif; }
${EL} a { color: var(--el-accent); text-decoration: none; }
${EL} a:hover { color: var(--el-accent-hover); }

/* paper texture grid */
${EL} .el-glow { display: none; }
${EL} .el-orb { position: fixed; z-index: 0; pointer-events: none; border-radius: 50%;
  display: none; will-change: transform; }
${EL} .el-orb-1 { width: 560px; height: 560px; left: -160px; top: -130px;
  background: radial-gradient(circle, rgba(12,107,88,0.28), transparent 65%);
  animation: elOrb1 26s ease-in-out infinite alternate; }
${EL} .el-orb-2 { width: 500px; height: 500px; right: -140px; top: 200px;
  background: radial-gradient(circle, rgba(180,83,9,0.18), transparent 65%);
  animation: elOrb2 32s ease-in-out infinite alternate; }
${EL} .el-orb-3 { width: 640px; height: 640px; left: 28%; bottom: -280px;
  background: radial-gradient(circle, rgba(100,116,139,0.16), transparent 65%);
  animation: elOrb3 38s ease-in-out infinite alternate; }
${EL} .el-orb-4 { width: 380px; height: 380px; right: 14%; top: 66%;
  background: radial-gradient(circle, rgba(12,107,88,0.20), transparent 65%);
  animation: elOrb2 29s ease-in-out infinite alternate-reverse; }
@keyframes elOrb1 { to { transform: translate(90px, 60px) scale(1.12); } }
@keyframes elOrb2 { to { transform: translate(-70px, 90px) scale(1.08); } }
@keyframes elOrb3 { to { transform: translate(60px, -80px) scale(1.15); } }
${EL} .el-grid { position: fixed; inset: 0; z-index: 0; pointer-events: none; opacity: 0.30;
  background-image: linear-gradient(to bottom, rgba(23,32,29,0.05) 1px, transparent 1px),
    linear-gradient(to right, rgba(23,32,29,0.05) 1px, transparent 1px);
  background-size: 46px 46px; }
${EL} .el-wrap { position: relative; z-index: 1; max-width: 1180px; margin: 0 auto; padding: 0 24px; }

/* nav - floating glass pill, slides away on scroll */
${EL} .el-nav { display: flex; align-items: center; justify-content: space-between; gap: 18px;
  padding: 12px 16px; margin: 16px 0 0; border-radius: 18px; position: sticky; top: 14px; z-index: 30;
  background: var(--el-glass); border: 1px solid var(--el-glass-border);
  backdrop-filter: var(--el-blur); -webkit-backdrop-filter: var(--el-blur);
  box-shadow: var(--el-glass-shadow);
  transition: opacity .35s ease, transform .35s ease; }
${EL} .el-nav.hide { opacity: 0; transform: translateY(-140%); pointer-events: none; }
${EL} .el-brand { display: flex; align-items: center; gap: 10px; font-family: 'Archivo', sans-serif;
  font-weight: 800; font-size: 22px; letter-spacing: .18em; color: var(--el-text); }
${EL} .el-logo { width: 30px; height: 30px; border-radius: 9px; flex: none;
  box-shadow: 0 4px 14px rgba(12,107,88,0.25); }
${EL} .el-nav-links { display: flex; gap: 26px; font-size: 13px; color: var(--el-muted); }
${EL} .el-nav-links a { color: var(--el-muted); }
${EL} .el-nav-links a:hover { color: var(--el-text); }
${EL} .el-nav-cta { display: flex; gap: 10px; }

/* side tools nav - fades in once the top nav leaves */
${EL} .el-rail { position: fixed; right: 14px; top: 50%; transform: translateY(-50%) translateX(140%);
  z-index: 40; display: flex; flex-direction: column; gap: 4px; padding: 8px; border-radius: 16px;
  background: var(--el-glass-2); border: 1px solid var(--el-glass-border);
  backdrop-filter: var(--el-blur); -webkit-backdrop-filter: var(--el-blur);
  box-shadow: var(--el-glass-shadow); max-height: calc(100vh - 32px); overflow-y: auto;
  opacity: 0; transition: opacity .35s ease, transform .35s ease; }
${EL} .el-rail.show { opacity: 1; transform: translateY(-50%) translateX(0); }
${EL} .el-rail-item { display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: 11px;
  border: none; background: transparent; cursor: pointer; color: var(--el-muted); font-family: inherit;
  transition: background .15s, color .15s; }
${EL} .el-rail-icon { display: grid; place-items: center; width: 20px; height: 20px; flex: none; }
${EL} .el-rail-label { font-family: 'Archivo', sans-serif; font-size: 11.5px; font-weight: 600;
  opacity: 0; max-width: 0; white-space: nowrap; overflow: hidden; transition: opacity .2s, max-width .2s; }
${EL} .el-rail-item:hover { background: rgba(23,32,29,0.07); color: var(--el-text); }
${EL} .el-rail-item:hover .el-rail-label, ${EL} .el-rail-item.active .el-rail-label { opacity: 1; max-width: 140px; }
${EL} .el-rail-item.active { color: #fff; background: var(--el-accent);
  box-shadow: 0 6px 18px rgba(12,107,88,0.45); }
${EL} .el-rail-div { height: 1px; margin: 6px 4px; background: var(--el-glass-border); }
@media (max-width: 860px){ ${EL} .el-rail { display: none; } }
${EL} .el-btn { display: inline-flex; align-items: center; gap: 8px; padding: 10px 18px; border-radius: 12px;
  font-size: 13px; font-weight: 600; text-decoration: none; border: 1px solid transparent; cursor: pointer;
  transition: all 0.2s; }
${EL} .el-btn-primary { background: #0c6b58; color: #fff;
  box-shadow: 0 8px 24px rgba(12,107,88,0.22); }
${EL} .el-btn-primary:hover { background: #085244; color: #fff;
  box-shadow: 0 10px 30px rgba(12,107,88,0.22); }
${EL} .el-btn-ghost { background: var(--el-glass); color: var(--el-text); border-color: var(--el-glass-border);
  backdrop-filter: var(--el-blur); -webkit-backdrop-filter: var(--el-blur); }
${EL} .el-btn-ghost:hover { border-color: var(--el-glass-border-hi); color: var(--el-accent-hover);
  background: var(--el-glass-2); }

/* hero */
${EL} .el-hero { padding: 44px 0 64px; text-align: center; }
${EL} .el-badge { display: inline-flex; align-items: center; gap: 8px; padding: 6px 14px; border-radius: 999px;
  background: var(--el-glass); color: var(--el-accent-hover); font-size: 12px; font-weight: 500;
  border: 1px solid var(--el-glass-border); margin-bottom: 20px; }
${EL} .el-hero-copy { max-width: 780px; margin: 0 auto 44px; }
${EL} .el-hero-copy h1 { font-size: 44px; line-height: 1.12; letter-spacing: -0.02em; margin-bottom: 18px;
  color: var(--el-text); }
${EL} .el-hero-copy p { color: var(--el-secondary); font-size: 16px; max-width: 560px; margin: 0 auto 26px; }
${EL} .el-hero-btns { display: flex; gap: 12px; flex-wrap: wrap; justify-content: center; }
${EL} .el-hero-stats { display: flex; gap: 32px; margin-top: 42px; flex-wrap: wrap; justify-content: center; }
${EL} .el-num { font-size: 26px; font-weight: 700; }
${EL} .el-stat-label { font-size: 11px; color: var(--el-muted); text-transform: uppercase; letter-spacing: .08em; }

/* graph stage - glass halo behind the demo card */
${EL} .el-stage-cap { margin-top: 14px; text-align: center; color: var(--el-muted); font-size: 12px; }
${EL} .el-stage-cap b { color: var(--el-secondary); font-weight: 600; }

/* brain flip-in inside the real-interviews demo */
${EL} .el-brain-btn { display: inline-flex; align-items: center; gap: 8px; padding: 9px 16px;
  border-radius: 12px; font-size: 12.5px; font-weight: 600; cursor: pointer;
  background: var(--el-glass-2); border: 1px solid var(--el-glass-border); color: var(--el-accent-hover);
  backdrop-filter: var(--el-blur); -webkit-backdrop-filter: var(--el-blur);
  transition: border-color .2s, transform .2s, background .2s; }
${EL} .el-brain-btn:hover { border-color: var(--el-glass-border-hi); transform: translateY(-2px);
  background: var(--el-accent-soft); }
${EL} .el-brain { background: var(--el-glass); border: 1px solid var(--el-glass-border);
  border-radius: 22px; padding: 20px; backdrop-filter: var(--el-blur); -webkit-backdrop-filter: var(--el-blur);
  box-shadow: var(--el-glass-shadow); }
${EL} .el-brain-top { display: flex; align-items: center; justify-content: space-between;
  flex-wrap: wrap; gap: 12px; margin-bottom: 16px; }
${EL} .el-brain-title { font-family: 'Archivo', sans-serif; font-size: 15px; font-weight: 700;
  color: var(--el-text); letter-spacing: .02em; }
${EL} .el-brain-sub { font-size: 12px; color: var(--el-muted); margin-top: 2px; }
@keyframes elFlipIn { from { opacity: 0; transform: translateY(14px) scale(0.975); }
  to { opacity: 1; transform: none; } }
${EL} .el-flip-in { animation: elFlipIn .4s ease both; }

/* problem stats band */
${EL} .el-band { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
@media (max-width: 860px) { ${EL} .el-band { grid-template-columns: 1fr 1fr; } }
@media (max-width: 520px) { ${EL} .el-band { grid-template-columns: 1fr; } }
${EL} .el-band-item { background: var(--el-glass); border: 1px solid var(--el-glass-border);
  border-radius: 18px; padding: 22px 20px; text-align: left;
  backdrop-filter: var(--el-blur); -webkit-backdrop-filter: var(--el-blur);
  box-shadow: var(--el-glass-shadow); }
${EL} .el-band-num { font-family: 'Archivo', sans-serif; font-size: 30px; font-weight: 800;
  letter-spacing: -0.02em; color: var(--el-accent); }
${EL} .el-band-label { font-size: 13px; color: var(--el-text); margin-top: 4px; line-height: 1.5; }
${EL} .el-band-src { font-size: 10.5px; color: var(--el-muted); margin-top: 8px; line-height: 1.5; }

/* ethics / explainability */
${EL} .el-ethos { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; text-align: left; margin-top: 34px; }
@media (max-width: 860px) { ${EL} .el-ethos { grid-template-columns: 1fr; } }

/* comparison table */
${EL} .el-table-wrap { margin-top: 34px; overflow-x: auto; }
${EL} .el-table { width: 100%; border-collapse: separate; border-spacing: 0; text-align: left; min-width: 640px; }
${EL} .el-table th, ${EL} .el-table td { padding: 15px 18px; font-size: 13px; line-height: 1.55;
  border-bottom: 1px solid var(--el-glass-border); }
${EL} .el-table thead th { background: var(--el-glass-2); font-family: 'Archivo', sans-serif;
  font-size: 12px; letter-spacing: .08em; text-transform: uppercase; color: var(--el-secondary);
  border-bottom: 1px solid var(--el-glass-border-hi); }
${EL} .el-table thead th:first-child { border-radius: 14px 0 0 0; }
${EL} .el-table thead th:last-child { border-radius: 0 14px 0 0; }
${EL} .el-table td:first-child { color: var(--el-muted); font-weight: 600; }
${EL} .el-table td.bad { color: var(--el-secondary); }
${EL} .el-table td.good { color: var(--el-success); font-weight: 600; }
${EL} .el-table tbody tr:last-child td { border-bottom: none; }
${EL} .el-table tbody tr { background: var(--el-glass); transition: background .15s; }
${EL} .el-table tbody tr:hover { background: var(--el-glass-2); }

/* sections */
${EL} .el-sec { padding: 60px 0; }
${EL} .el-kicker { font-size: 11px; text-transform: uppercase; letter-spacing: .16em; color: var(--el-accent);
  font-weight: 700; margin-bottom: 10px; }
${EL} .el-h2 { font-size: 29px; font-weight: 700; letter-spacing: -0.01em; margin-bottom: 12px; }
${EL} .el-sub { color: var(--el-secondary); max-width: 660px; margin-bottom: 34px; font-size: 15px; }

/* glass cards */
${EL} .el-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; }
${EL} .el-card { background: var(--el-glass); border: 1px solid var(--el-glass-border); border-radius: var(--el-radius);
  padding: 24px; transition: border-color .2s, transform .2s, background .2s;
  backdrop-filter: var(--el-blur); -webkit-backdrop-filter: var(--el-blur);
  box-shadow: var(--el-glass-shadow); }
${EL} .el-card:hover { border-color: var(--el-glass-border-hi); transform: translateY(-3px);
  background: var(--el-glass-2); }
${EL} .el-ic { width: 40px; height: 40px; border-radius: 12px; display: flex; align-items: center; justify-content: center;
  background: var(--el-accent-soft); color: var(--el-accent-hover); margin-bottom: 14px;
  }
${EL} .el-ic svg { width: 20px; height: 20px; }

/* problem / solution - one clear message per audience */
${EL} .el-ic.cand { background: rgba(37,99,235,0.10); color: #0369a1; }
${EL} .el-probs { display: grid; grid-template-columns: 1fr 1fr; gap: 22px; text-align: left; margin-top: 34px; }
@media (max-width: 860px) { ${EL} .el-probs { grid-template-columns: 1fr; } }
${EL} .el-prob { background: var(--el-glass); border: 1px solid var(--el-glass-border); border-radius: 20px;
  padding: 28px; display: flex; flex-direction: column; gap: 22px;
  backdrop-filter: var(--el-blur); -webkit-backdrop-filter: var(--el-blur); box-shadow: var(--el-glass-shadow); }
${EL} .el-prob-head { display: flex; align-items: center; gap: 13px; padding-bottom: 18px;
  border-bottom: 1px solid var(--el-glass-border); }
${EL} .el-prob-head .el-ic { margin-bottom: 0; }
${EL} .el-prob-head h3 { margin: 0; font-size: 18px; }
${EL} .el-prob-head p { margin: 2px 0 0; font-size: 12.5px; color: var(--el-muted); }
${EL} .el-prob-item { display: flex; flex-direction: column; gap: 6px; }
${EL} .el-problem { font-size: 14px; font-weight: 600; color: var(--el-text); line-height: 1.45; }
${EL} .el-problem::before { content: '“'; color: var(--el-error); font-weight: 700; margin-right: 2px; }
${EL} .el-problem::after { content: '”'; color: var(--el-error); font-weight: 700; margin-left: 2px; }
${EL} .el-sol { font-size: 13px; color: var(--el-secondary); line-height: 1.6; }
${EL} .el-sol::before { content: 'AURA: '; color: var(--el-accent-hover); font-weight: 600; }
${EL} .el-prob-cta { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 4px; }
${EL} .el-card h3 { font-size: 15px; margin-bottom: 7px; }
${EL} .el-card p { font-size: 13px; color: var(--el-secondary); }

/* pipeline strip */
${EL} .el-pipe { display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; margin-bottom: 34px; }
${EL} .el-pipe-step { background: var(--el-glass); border: 1px solid var(--el-glass-border); border-radius: 14px;
  padding: 16px 18px; position: relative; backdrop-filter: var(--el-blur); -webkit-backdrop-filter: var(--el-blur);
  box-shadow: var(--el-glass-shadow); transition: border-color .2s, transform .2s; }
${EL} .el-pipe-step:hover { border-color: var(--el-glass-border-hi); transform: translateY(-2px); }
${EL} .el-pipe-step::after { content: '→'; position: absolute; right: -12px; top: 50%; transform: translateY(-50%);
  color: var(--el-muted); font-size: 14px; z-index: 2; }
${EL} .el-pipe-step:last-child::after { content: ''; }
${EL} .el-pipe-n { font-size: 10px; font-weight: 800; color: var(--el-accent); letter-spacing: .14em; margin-bottom: 6px; }
${EL} .el-pipe-step h3 { font-size: 13.5px; margin-bottom: 4px; }
${EL} .el-pipe-step p { font-size: 11.5px; color: var(--el-muted); }

/* legend */
${EL} .el-legend { display: flex; gap: 16px; flex-wrap: wrap; align-items: center;
  background: var(--el-glass); border: 1px solid var(--el-glass-border); border-radius: 14px; padding: 12px 18px;
  font-size: 12px; color: var(--el-secondary); margin-bottom: 14px;
  backdrop-filter: var(--el-blur); -webkit-backdrop-filter: var(--el-blur); box-shadow: var(--el-glass-shadow); }
${EL} .el-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; vertical-align: -1px; }
${EL} .el-line { display: inline-block; width: 22px; height: 2px; margin-right: 6px; vertical-align: 3px; }

/* real-interview demo */
${EL} .el-tabs { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; margin-bottom: 26px; }
${EL} .el-tab { font-family: 'Archivo', sans-serif; font-weight: 600; font-size: 13px; padding: 10px 20px;
  border-radius: 999px; cursor: pointer; border: 1px solid var(--el-glass-border);
  background: var(--el-glass); color: var(--el-secondary); transition: all .15s;
  backdrop-filter: var(--el-blur); -webkit-backdrop-filter: var(--el-blur); }
${EL} .el-tab:hover { color: var(--el-text); border-color: var(--el-glass-border-hi); }
${EL} .el-tab.active { color: #fff; border-color: transparent;
  background: var(--el-accent);
  box-shadow: 0 8px 22px rgba(12,107,88,0.45); }
${EL} .el-demo { display: grid; grid-template-columns: 1fr 340px; gap: 18px; align-items: start; }
${EL} .el-demo-brain { grid-template-columns: 1fr; }
@media (max-width: 860px) { ${EL} .el-demo { grid-template-columns: 1fr; } }
${EL} .el-demo-main { background: var(--el-glass); border: 1px solid var(--el-glass-border); border-radius: var(--el-radius);
  padding: 26px; display: flex; flex-direction: column; gap: 20px; min-height: 480px;
  backdrop-filter: var(--el-blur); -webkit-backdrop-filter: var(--el-blur); box-shadow: var(--el-glass-shadow); }
${EL} .el-demo-step-head { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
${EL} .el-phase-chip { font-size: 11px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;
  color: var(--el-info); background: rgba(37,99,235,0.08); border: 1px solid rgba(37,99,235,0.45); padding: 4px 12px; border-radius: 999px;
  backdrop-filter: var(--el-blur); -webkit-backdrop-filter: var(--el-blur); }
${EL} .el-comp-chip { font-size: 11px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;
  color: var(--el-accent-hover); background: var(--el-accent-soft); border: 1px solid rgba(12,107,88,0.45); padding: 4px 12px; border-radius: 999px;
  backdrop-filter: var(--el-blur); -webkit-backdrop-filter: var(--el-blur); }
${EL} .el-step-count { margin-left: auto; font-size: 12px; color: var(--el-muted); font-weight: 600; }
${EL} .el-demo-q { font-family: 'Archivo', sans-serif; font-size: 16px; font-weight: 500; line-height: 1.5;
  background: var(--el-glass-2); border: 1px solid var(--el-glass-border); border-radius: 14px; padding: 20px 22px;
  backdrop-filter: var(--el-blur); -webkit-backdrop-filter: var(--el-blur); }
${EL} .el-demo-q::before { content: 'Q'; display: inline-flex; width: 24px; height: 24px; align-items: center;
  justify-content: center; border-radius: 8px; background: #0c6b58; color: #fff; font-size: 12px;
  font-weight: 700; margin-right: 10px; vertical-align: 2px; box-shadow: 0 4px 12px rgba(12,107,88,0.45); }
${EL} .el-demo-a { background: rgba(12,122,84,0.07); border: 1px solid rgba(12,122,84,0.40); border-radius: 14px;
  padding: 18px 20px; font-size: 13.5px; color: var(--el-secondary); display: none;
  backdrop-filter: var(--el-blur); -webkit-backdrop-filter: var(--el-blur); }
${EL} .el-demo-a.show { display: block; animation: elFadeIn .4s ease; }
${EL} .el-demo-a::before { content: 'A'; display: inline-flex; width: 24px; height: 24px; align-items: center;
  justify-content: center; border-radius: 8px; background: var(--el-success); color: #ffffff; font-size: 12px;
  font-weight: 700; margin-right: 10px; vertical-align: 2px; }
@keyframes elFadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
${EL} .el-demo-actions { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
${EL} .el-demo-bar { flex: 1; min-width: 200px; height: 6px; border-radius: 999px; background: rgba(23,32,29,0.09); overflow: hidden; }
${EL} .el-demo-bar-fill { height: 100%; width: 0%; border-radius: 999px; background: var(--el-accent); transition: width .6s ease; }
${EL} .el-demo-hint { font-size: 12px; color: var(--el-muted); }
${EL} .el-demo-side { display: flex; flex-direction: column; gap: 14px; }
${EL} .el-side-card { background: var(--el-glass); border: 1px solid var(--el-glass-border); border-radius: var(--el-radius);
  padding: 18px; backdrop-filter: var(--el-blur); -webkit-backdrop-filter: var(--el-blur); box-shadow: var(--el-glass-shadow); }
${EL} .el-side-card h4 { font-size: 12px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase;
  color: var(--el-muted); margin: 0 0 12px; }
${EL} .el-dim-row { display: flex; align-items: center; gap: 10px; margin-bottom: 9px; font-size: 12.5px; }
${EL} .el-dim-name { flex: 0 0 108px; color: var(--el-secondary); }
${EL} .el-dim-track { flex: 1; height: 5px; border-radius: 999px; background: rgba(23,32,29,0.09); overflow: hidden; }
${EL} .el-dim-fill { height: 100%; width: 0%; border-radius: 999px; background: rgba(90,102,96,0.38); transition: width .7s ease; }
${EL} .el-dim-score { flex: 0 0 30px; text-align: right; color: var(--el-text); font-weight: 600; }
${EL} .el-hypo { display: flex; gap: 9px; align-items: flex-start; font-size: 12.5px; color: var(--el-secondary); margin-bottom: 9px; }
${EL} .el-hypo-dot { width: 7px; height: 7px; border-radius: 50%; margin-top: 5px; flex: none; }
${EL} .el-st { font-size: 10.5px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; margin-top: 2px; display: block; }
${EL} .el-st.confirmed { color: var(--el-success); } ${EL} .el-st.refuted { color: var(--el-error); } ${EL} .el-st.testing { color: var(--el-warning); } ${EL} .el-st.untested { color: var(--el-muted); }
${EL} .el-reflect-text { font-size: 12.5px; color: var(--el-secondary); }
${EL} .el-ev-list { display: flex; flex-direction: column; gap: 8px; }
${EL} .el-ev-row { display: flex; align-items: center; gap: 10px; font-size: 12.5px; }
${EL} .el-ev-label { flex: 1; color: var(--el-secondary); }
${EL} .el-ev-avg { font-weight: 700; color: var(--el-text); }
${EL} .el-ev-count { font-size: 11px; color: var(--el-muted); }
${EL} .el-verdict { display: none; align-items: center; gap: 12px; border: 1px solid rgba(12,122,84,0.45);
  background: rgba(52,211,153,0.1); border-radius: 14px; padding: 16px 18px;
  backdrop-filter: var(--el-blur); -webkit-backdrop-filter: var(--el-blur);
  box-shadow: 0 10px 30px rgba(12,122,84,0.10); }
${EL} .el-verdict.show { display: flex; animation: elFadeIn .5s ease; }
${EL} .el-v-label { font-family: 'Archivo', sans-serif; font-weight: 700; font-size: 16px; color: var(--el-success); }
${EL} .el-v-sub { font-size: 12.5px; color: var(--el-secondary); }
${EL} .el-verdict.weak { border-color: rgba(180,83,9,0.45); background: rgba(180,83,9,0.08); }
${EL} .el-verdict.weak .el-v-label { color: var(--el-warning); }
${EL} .el-score-big { font-family: 'Archivo', sans-serif; font-size: 26px; font-weight: 800; }
${EL} .el-cand-meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; justify-content: center; margin: -14px 0 24px; }
${EL} .el-cand-chip { font-size: 11.5px; font-weight: 600; padding: 5px 12px; border-radius: 999px;
  backdrop-filter: var(--el-blur); -webkit-backdrop-filter: var(--el-blur); }
${EL} .el-cand-chip.strong { color: var(--el-success); border: 1px solid rgba(12,122,84,0.45); background: rgba(52,211,153,0.1); }
${EL} .el-cand-chip.weak { color: var(--el-warning); border: 1px solid rgba(180,83,9,0.45); background: rgba(180,83,9,0.08); }
${EL} .el-cand-chip.neutral { color: var(--el-secondary); border: 1px solid var(--el-glass-border); background: var(--el-glass); }

/* cta */
${EL} .el-cta { text-align: center; padding: 70px 24px; }
${EL} .el-cta .el-h2 { font-size: 32px; }
${EL} .el-cta .el-sub { margin: 0 auto 28px; }

/* footer */
${EL} .el-foot { margin-top: 8px; border-top: 1px solid var(--el-glass-border); padding: 52px 0 0;
  color: var(--el-muted); }
${EL} .el-foot-grid { display: grid; grid-template-columns: 2fr 1fr 1fr; gap: 40px; }
@media (max-width: 860px) { ${EL} .el-foot-grid { grid-template-columns: 1fr; gap: 28px; } }
${EL} .el-foot-tag { color: var(--el-muted); font-size: 13px; max-width: 380px; margin: 14px 0 0; }
${EL} .el-foot-col { display: flex; flex-direction: column; gap: 10px; }
${EL} .el-foot-col h4 { margin: 0 0 4px; font-family: 'Archivo', sans-serif; font-size: 12px;
  letter-spacing: .14em; text-transform: uppercase; color: var(--el-secondary); }
${EL} .el-foot-col a { color: var(--el-muted); font-size: 13px; text-decoration: none; transition: color .15s; }
${EL} .el-foot-col a:hover { color: var(--el-accent-hover); }
${EL} .el-foot-bar { display: flex; align-items: center; justify-content: space-between;
  flex-wrap: wrap; gap: 8px; margin-top: 44px; padding-top: 20px; border-top: 1px solid var(--el-glass-border);
  color: var(--el-muted); font-size: 12px; }
${EL} .el-foot a { color: var(--el-muted); }
${EL} .el-foot a:hover { color: var(--el-text); }

@media (max-width: 980px){
  ${EL} .el-hero { padding-top: 28px; }
  ${EL} .el-cards { grid-template-columns: 1fr; }
  ${EL} .el-pipe { grid-template-columns: 1fr 1fr; }
  ${EL} .el-pipe-step::after { content: ''; }
}
@media (max-width: 560px){
  ${EL} .el-pipe { grid-template-columns: 1fr; }
  ${EL} .el-hero-copy h1 { font-size: 32px; }
  ${EL} .el-nav-links { display: none; }
}
`;

export function Landing() {
  const [scrolled, setScrolled] = useState(false);
  const [activeSection, setActiveSection] = useState('graph');
  const [candId, setCandId] = useState<'alice' | 'brian'>('alice');
  const [step, setStep] = useState(0);
  const [answered, setAnswered] = useState(false);
  const [finished, setFinished] = useState(false);
  const [view, setView] = useState<'interview' | 'brain'>('interview');

  const cand: RealCandidate = REAL_CANDIDATES[candId];
  const cur: RealStep = cand.steps[step];

  const handleCandSwitch = (id: 'alice' | 'brian') => {
    if (id === candId) return;
    setCandId(id);
    setStep(0);
    setAnswered(false);
    setFinished(false);
    setView('interview');
  };

  const handleDemoClick = () => {
    if (finished) return;
    if (!answered) {
      setAnswered(true);
      if (step >= cand.steps.length - 1) setTimeout(() => setFinished(true), 400);
      return;
    }
    if (step >= cand.steps.length - 1) {
      setFinished(true);
      return;
    }
    setStep(step + 1);
    setAnswered(false);
  };

  const btnLabel = finished
    ? 'Interview complete'
    : answered
      ? step >= cand.steps.length - 1 ? 'Finish interview' : 'Next question →'
      : step >= cand.steps.length - 1 ? 'Reveal final answer' : 'Reveal candidate answer';

  const phaseColor: Record<string, string> = {
    intro: 'var(--el-info)',
    technical: 'var(--el-accent-hover)',
    behavioral: '#be185d',
    conclusion: 'var(--el-warning)',
  };
  const phaseBg: Record<string, string> = {
    intro: 'rgba(37,99,235,0.08)',
    technical: 'var(--el-accent-soft)',
    behavioral: 'rgba(190,24,93,0.08)',
    conclusion: 'rgba(180,83,9,0.10)',
  };
  const phaseBorder: Record<string, string> = {
    intro: 'rgba(37,99,235,0.45)',
    technical: 'rgba(12,107,88,0.45)',
    behavioral: 'rgba(190,24,93,0.45)',
    conclusion: 'rgba(180,83,9,0.50)',
  };

  const statusDot: Record<string, string> = {
    confirmed: 'var(--el-success)',
    refuted: 'var(--el-error)',
    testing: 'var(--el-warning)',
    untested: 'var(--el-muted)',
  };

  const stepHypotheses = cand.hypotheses.filter(h => h.competency === cur.comp).slice(0, 4);
  const scoreBars = [
    { name: 'Answer score', value: cur.score },
    { name: 'Technical', value: cur.tech },
    { name: 'Communication', value: cur.comm },
  ];
  const curEvidence = cand.evidence[cur.comp];

  useEffect(() => {
    document.body.classList.add('engine-landing');
    const onScroll = () => {
      setScrolled(window.scrollY > 140);
      const ids = ['impact', 'problem', 'ethos', 'graph', 'why', 'real', 'pipeline', 'cta'];
      let current = 'graph';
      for (const id of ids) {
        const el = document.getElementById(id);
        if (el && el.getBoundingClientRect().top < window.innerHeight * 0.4) current = id;
      }
      const atBottom = window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2;
      if (atBottom) current = ids[ids.length - 1];
      setActiveSection(current);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => {
      document.body.classList.remove('engine-landing');
      window.removeEventListener('scroll', onScroll);
    };
  }, []);

  const scrollTo = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });

  const RAIL: Array<[string, string, React.ReactNode]> = [
    ['impact', 'the problem', <BarChart3 key="impact" size={17} strokeWidth={2.2} />],
    ['problem', "who it's for", <Building2 key="problem" size={17} strokeWidth={2.2} />],
    ['ethos', 'auditable AI', <ShieldCheck key="ethos" size={17} strokeWidth={2.2} />],
    ['graph', 'graph', <Brain key="graph" size={17} strokeWidth={2.2} />],
    ['why', 'why', <Sparkles key="why" size={17} strokeWidth={2.2} />],
    ['real', 'real interviews', <MessageSquare key="real" size={17} strokeWidth={2.2} />],
    ['pipeline', 'pipeline', <Workflow key="pipe" size={17} strokeWidth={2.2} />],
    ['cta', 'start', <Play key="cta" size={17} strokeWidth={2.2} />],
  ];

  return (
    <div className="engine-landing">
      <style>{styles}</style>
      <div className="el-glow" />
      <div className="el-orb el-orb-1" />
      <div className="el-orb el-orb-2" />
      <div className="el-orb el-orb-3" />
      <div className="el-orb el-orb-4" />
      <div className="el-grid" />

      <nav className={`el-rail ${scrolled ? 'show' : ''}`} aria-label="Page sections">
        {RAIL.map(([id, label, icon]) => (
          <button key={id} className={`el-rail-item ${activeSection === id ? 'active' : ''}`} onClick={() => scrollTo(id)}>
            <span className="el-rail-icon">{icon}</span>
            <span className="el-rail-label">{label}</span>
          </button>
        ))}
      </nav>

      <div className="el-wrap">
        <nav className={`el-nav ${scrolled ? 'hide' : ''}`}>
          <div className="el-brand"><img className="el-logo" src="/favicon.svg" alt="" />AURA</div>
          <div className="el-nav-links">
            <a href="#graph">brain graph</a>
            <a href="#why">evidence-first</a>
            <a href="#real">real interviews</a>
            <a href="#pipeline">pipeline</a>
          </div>
          <div className="el-nav-cta">
            <Link className="el-btn el-btn-primary" to="/account">get started</Link>
          </div>
        </nav>

        <section className="el-hero">
          <div className="el-hero-copy">
            <div className="el-badge"><Sparkles size={13} /> AURA, your AI interviewer on both sides of the table</div>
            <h1>Know exactly why you hired.<br />Or why you didn't.</h1>
            <p>
              AURA conducts your interviews with AI, asking, listening, and scoring every
              answer, then hands you a verdict with the reasoning behind it. Hiring teams
              stop guessing; candidates walk away with feedback that actually teaches.
            </p>
            <div className="el-hero-btns">
              <Link className="el-btn el-btn-primary" to="/account">run an interview</Link>
              <Link className="el-btn el-btn-ghost" to="/brain-graph">explore the 13 layers →</Link>
            </div>
            <div className="el-hero-stats">
              <div><div className="el-num">1</div><div className="el-stat-label">verdict per interview, fully sourced</div></div>
              <div><div className="el-num">real-time</div><div className="el-stat-label">scoring as the candidate speaks</div></div>
              <div><div className="el-num">∞</div><div className="el-stat-label">replayable interview timeline</div></div>
            </div>
          </div>
        </section>
      </div>

      <div className="el-wrap">
        <section className="el-sec" id="impact">
          <div className="el-kicker">the problem, in numbers</div>
          <h2 className="el-h2">Hiring is broken in ways we all quietly accept.</h2>
          <div className="el-band">
            <div className="el-band-item">
              <div className="el-band-num">23h</div>
              <div className="el-band-label">per hire, a recruiter spends on interviews and screening that could be one consistent session</div>
              <div className="el-band-src">industry-reported screening averages</div>
            </div>
            <div className="el-band-item">
              <div className="el-band-num">57%</div>
              <div className="el-band-label">of hiring decisions are swayed by interviewer bias or first impressions, not evidence</div>
              <div className="el-band-src">commonly cited in HR industry surveys</div>
            </div>
            <div className="el-band-item">
              <div className="el-band-num">94%</div>
              <div className="el-band-label">of candidates want feedback after an interview, and most never receive a word</div>
              <div className="el-band-src">widely reported job-seeker surveys</div>
            </div>
            <div className="el-band-item">
              <div className="el-band-num">0</div>
              <div className="el-band-label">chances a candidate gets to question the verdict, when the reasons are locked in someone's head</div>
              <div className="el-band-src">AURA's answer: receipts for everyone</div>
            </div>
          </div>
        </section>
      </div>

      <div className="el-wrap">
        <section className="el-sec" id="problem">
          <div className="el-kicker">what we solve</div>
          <h2 className="el-h2">Both sides of the table are stuck on the same thing.</h2>
          <p className="el-sub">
            Hiring teams can't explain their decisions; candidates never get feedback.
            AURA fixes both with the same move: every interview ends with proof.
          </p>

          <div className="el-probs">
            <div className="el-prob">
              <div className="el-prob-head">
                <div className="el-ic"><Building2 /></div>
                <div>
                  <h3>For hiring teams</h3>
                  <p>the problem AURA solves for you</p>
                </div>
              </div>
              <div className="el-prob-item">
                <div className="el-problem">Why did we hire this person, and is it defensible?</div>
                <div className="el-sol">every interview ends with a scored, sourced verdict. Strong answers, gaps, and the exact reasoning behind the hire. Nothing to defend blind.</div>
              </div>
              <div className="el-prob-item">
                <div className="el-problem">Interviews are slow, inconsistent, and easy to game.</div>
                <div className="el-sol">one AI interviewer runs every session with the same questions and standards, scoring in real time. Comparable candidates, no drift.</div>
              </div>
              <div className="el-prob-item">
                <div className="el-problem">I can't prove we didn't just trust a gut feeling.</div>
                <div className="el-sol">every score traces back to a quote from the candidate. The verdict is only as strong as the chain that holds it up, and you can show it.</div>
              </div>
              <div className="el-prob-cta">
                <Link className="el-btn el-btn-primary" to="/account">start hiring with AURA</Link>
              </div>
            </div>

            <div className="el-prob">
              <div className="el-prob-head">
                <div className="el-ic cand"><UserRound /></div>
                <div>
                  <h3>For candidates</h3>
                  <p>the problem AURA solves for you</p>
                </div>
              </div>
              <div className="el-prob-item">
                <div className="el-problem">Rejections come back with zero feedback.</div>
                <div className="el-sol">you get itemized, sourced feedback after every interview: what you showed, what you missed, and what to work on next.</div>
              </div>
              <div className="el-prob-item">
                <div className="el-problem">I have no idea how I actually perform under interview pressure.</div>
                <div className="el-sol">practice interviews scored live, then review your own evidence trail. See your real performance, not a vibe.</div>
              </div>
              <div className="el-prob-item">
                <div className="el-problem">Every interviewer is a different coin flip.</div>
                <div className="el-sol">one consistent AI interviewer, the same standards every time. Practice against the actual bar, and walk into real interviews prepared.</div>
              </div>
              <div className="el-prob-cta">
                <Link className="el-btn el-btn-primary" to="/candidate/register">practice as a candidate</Link>
                <Link className="el-btn el-btn-ghost" to="/account">browse open interviews</Link>
              </div>
            </div>
          </div>
        </section>
      </div>

      <div className="el-wrap">
        <section className="el-sec" id="ethos">
          <div className="el-kicker">why this matters</div>
          <h2 className="el-h2">When a machine decides someone's career, it should have to show its work.</h2>
          <p className="el-sub">
            Automated hiring tools are already making decisions that shape careers, and most of
            them cannot explain themselves. Regulators are responding: the EU AI Act classifies
            employment AI as high risk and requires transparency, and New York's Local Law 144
            demands audits of automated hiring tools. AURA was built for this world.
          </p>
          <div className="el-ethos">
            <div className="el-card">
              <div className="el-ic"><Brain /></div>
              <h3>No black boxes</h3>
              <p>Every verdict ships with its reasoning trail: which answers, which evidence,
                and which hypotheses drove the decision.</p>
            </div>
            <div className="el-card">
              <div className="el-ic"><GitBranch /></div>
              <h3>Bias, surfaced not hidden</h3>
              <p>Scores are broken down per competency and per question, with contradictions
                flagged in red. Weak spots cannot hide inside a single number.</p>
            </div>
            <div className="el-card">
              <div className="el-ic"><ShieldCheck /></div>
              <h3>Regulation-ready by design</h3>
              <p>Explainability is not bolted on. The evidence-first architecture exists so any
                hire can be audited, questioned, and replayed end to end.</p>
            </div>
            <div className="el-card">
              <div className="el-ic"><ListChecks /></div>
              <h3>Candidates get answers too</h3>
              <p>Itemized, sourced feedback after every interview, so the person on the other
                side of the table is never left guessing.</p>
            </div>
          </div>

          <div className="el-table-wrap">
            <table className="el-table">
              <thead>
                <tr>
                  <th></th>
                  <th>the traditional loop</th>
                  <th>with AURA</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>time to a verdict</td>
                  <td className="bad">multiple rounds stretched over weeks</td>
                  <td className="good">one live session, verdict with receipts at the end</td>
                </tr>
                <tr>
                  <td>question consistency</td>
                  <td className="bad">every interviewer asks something different</td>
                  <td className="good">the same standards for every single candidate</td>
                </tr>
                <tr>
                  <td>candidate feedback</td>
                  <td className="bad">generic rejection, often silence</td>
                  <td className="good">itemized, sourced feedback after every interview</td>
                </tr>
                <tr>
                  <td>bias &amp; gut feel</td>
                  <td className="bad">first impressions sway the call</td>
                  <td className="good">evidence only, scored per answer in real time</td>
                </tr>
                <tr>
                  <td>explainability</td>
                  <td className="bad">"trust me, it was a good fit"</td>
                  <td className="good">every score traces back to a candidate's own words</td>
                </tr>
                <tr>
                  <td>cost</td>
                  <td className="bad">recruiter hours per hire, per round</td>
                  <td className="good">one consistent interviewer, fully automated</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <div className="el-wrap">
        <section className="el-sec" id="why">
          <div className="el-kicker">why teams trust AURA</div>
          <h2 className="el-h2">Decisions you can defend, not vibes you have to sell.</h2>
          <p className="el-sub">
            Every interview ends with a verdict plus the proof behind it: supporting evidence
            in green, contradictions in red, and a decision only as strong as its chain.
            Ask any recruiter to explain a hire. AURA lets them, with receipts.
          </p>
          <div className="el-cards">
            <div className="el-card">
              <div className="el-ic"><Brain /></div>
              <h3>No more gut-feel hiring</h3>
              <p>Every candidate leaves with a scored trail: which answers were strong,
                where the gaps are, and what actually drove the verdict.</p>
            </div>
            <div className="el-card">
              <div className="el-ic"><GitBranch /></div>
              <h3>Confidence you can see</h3>
              <p>Strong answers pull the decision toward hire; weak ones pull it away;
                and you can watch exactly what moved it, in real time.</p>
            </div>
            <div className="el-card">
              <div className="el-ic"><ListChecks /></div>
              <h3>Replay any interview</h3>
              <p>Scrub question by question and see every answer, score, and shift in the
                reasoning, useful for calibration or for the candidate afterwards.</p>
            </div>
            <div className="el-card">
              <div className="el-ic"><ShieldCheck /></div>
              <h3>Feedback candidates trust</h3>
              <p>Instead of a generic rejection, candidates get itemized, sourced feedback:
                what they showed, what they missed, and what to work on.</p>
            </div>
            <div className="el-card">
              <div className="el-ic"><Layers /></div>
              <h3>Drill into any claim</h3>
              <p>Question a score? Open the competency, the hypothesis, or the raw answer
                behind it. Every number traces back to a quote.</p>
            </div>
            <div className="el-card">
              <div className="el-ic"><Workflow /></div>
              <h3>Patience built in</h3>
              <p>The interviewer doesn't commit early. It keeps testing open questions
                until the proof settles, the same discipline good humans bring.</p>
            </div>
          </div>
        </section>
      </div>

      <div className="el-wrap">
        <section className="el-sec" id="real">
          <div className="el-kicker">real interviews</div>
          <h2 className="el-h2">A weak candidate and a strong one, turn by turn.</h2>
          <p className="el-sub">
            Two real sessions from the AURA engine: Alice (strong) and Brian (weak) both interviewed
            for the same Senior Python Developer role. Step through the actual questions and answers,
            and watch the side panel show exactly what the engine scored, cited, and believed.
          </p>

          <div className="el-tabs">
            <button className={`el-tab ${candId === 'alice' ? 'active' : ''}`} onClick={() => handleCandSwitch('alice')}>
              Alice Chan, strong
            </button>
            <button className={`el-tab ${candId === 'brian' ? 'active' : ''}`} onClick={() => handleCandSwitch('brian')}>
              Brian Osei, weak
            </button>
          </div>
          <div className="el-cand-meta">
            <span className={`el-cand-chip ${candId === 'alice' ? 'strong' : 'weak'}`}>
              final verdict: {cand.verdict} · composite {cand.composite?.toFixed(1)}
            </span>
            <span className="el-cand-chip neutral">
              {cand.steps.length} questions · difficulty {cand.difficulty} · coverage {Math.round((cand.coverage ?? 0) * 100)}%
            </span>
            <button className="el-brain-btn" onClick={() => setView(view === 'brain' ? 'interview' : 'brain')}>
              <Brain size={14} /> {view === 'brain' ? 'back to interview' : 'show this candidate\'s brain graph'}
            </button>
          </div>

          <div className={`el-demo ${view === 'brain' ? 'el-demo-brain' : ''}`} id="graph">
            {view === 'brain' ? (
              <div className="el-brain el-flip-in">
                <div className="el-brain-top">
                  <button className="el-btn el-btn-ghost" onClick={() => setView('interview')}>
                    ← back to interview
                  </button>
                  <div style={{ textAlign: 'center' }}>
                    <div className="el-brain-title">{cand.name}, {cand.verdict}</div>
                    <div className="el-brain-sub">{cand.steps.length} turns · {Object.keys(cand.evidence).length} competencies · session {cand.sessionId.slice(0, 8)}</div>
                  </div>
                  <Link className="el-btn el-btn-ghost" to="/brain-graph">open full view</Link>
                </div>
                <BrainGraph
                  snapshot={BRAIN_SNAPSHOTS[candId]}
                  title={cand.name + ' · evidence brain'}
                />
                <div className="el-stage-cap">
                  <b>this candidate's real brain.</b> drag nodes · play the timeline · click a layer to see what fed the verdict
                </div>
              </div>
            ) : (
            <>
            <div className="el-demo-main">
              <div className="el-demo-step-head">
                <span className="el-phase-chip" style={{ color: phaseColor[cur.phase], background: phaseBg[cur.phase], borderColor: phaseBorder[cur.phase] }}>{cur.phase}</span>
                <span className="el-comp-chip">{cur.compLabel}</span>
                <span className="el-step-count">Question {step + 1} / {cand.steps.length}</span>
              </div>
              <div className="el-demo-q">{cur.q}</div>
              <div className={`el-demo-a ${answered ? 'show' : ''}`}>{cur.a}</div>
              <div className="el-demo-actions">
                <button className="el-btn el-btn-primary" onClick={handleDemoClick} disabled={finished} style={{ minWidth: 180, justifyContent: 'center' }}>
                  {btnLabel}
                </button>
                <div className="el-demo-bar"><div className="el-demo-bar-fill" style={{ width: answered ? '100%' : '0%' }} /></div>
                <span className="el-demo-hint">{answered ? 'engine: scored · extracted evidence · updated hypotheses' : 'interviewer asked, candidate answer hidden'}</span>
              </div>
              <div className={`el-verdict ${finished ? 'show' : ''} ${candId === 'brian' ? 'weak' : ''}`}>
                <div>
                  <div className="el-v-label">{cand.verdict}</div>
                  <div className="el-v-sub">
                    composite {cand.composite?.toFixed(2)} · decision "{cand.decision}" ({cand.decisionScore?.toFixed(2)}) · difficulty {cand.difficulty}
                  </div>
                </div>
              </div>
            </div>
            <div className="el-demo-side">
              <div className="el-side-card">
                <h4>Answer evaluation</h4>
                {scoreBars.map((b) => (
                  <div className="el-dim-row" key={b.name}>
                    <span className="el-dim-name">{b.name}</span>
                    <div className="el-dim-track">
                      <div className="el-dim-fill" style={{
                        width: answered && b.value != null ? `${b.value * 10}%` : '0%',
                        background: answered && b.value != null ? (b.value >= 7 ? 'var(--el-success)' : b.value >= 5 ? 'var(--el-warning)' : 'var(--el-error)') : 'rgba(90,102,96,0.38)',
                      }} />
                    </div>
                    <span className="el-dim-score">{answered && b.value != null ? b.value.toFixed(1) : '-'}</span>
                  </div>
                ))}
                <div className="el-ev-list" style={{ marginTop: 12 }}>
                  <div className="el-reflect-text">
                    <b style={{ color: 'var(--el-success)' }}>strengths:</b> {answered ? cur.strengths.split(',').slice(0, 3).join(', ') : '…'}
                  </div>
                  <div className="el-reflect-text">
                    <b style={{ color: 'var(--el-error)' }}>weaknesses:</b> {answered ? cur.weaknesses.split(',').slice(0, 3).join(', ') : '…'}
                  </div>
                </div>
              </div>
              <div className="el-side-card">
                <h4>Hypothesis engine: {cur.compLabel}</h4>
                {stepHypotheses.length === 0 && <div className="el-reflect-text">no hypotheses tracked for this competency yet</div>}
                {stepHypotheses.map((h, i) => (
                  <div className="el-hypo" key={i}>
                    <span className="el-hypo-dot" style={{ background: statusDot[h.status] }} />
                    <div>
                      <span className={`el-st ${h.status}`}>{h.status}</span>
                      {h.statement} <span style={{ color: 'var(--el-muted)' }}>· {Math.round(h.confidence * 100)}%</span>
                    </div>
                  </div>
                ))}
              </div>
              <div className="el-side-card">
                <h4>Competency evidence</h4>
                {curEvidence && (
                  <div className="el-ev-list">
                    <div className="el-ev-row">
                      <span className="el-ev-label">{curEvidence.label}</span>
                      <span className="el-ev-avg">{curEvidence.avg != null ? curEvidence.avg.toFixed(1) : '-'}</span>
                      <span className="el-ev-count">avg</span>
                    </div>
                    <div className="el-ev-row">
                      <span className="el-ev-label">evidence items</span>
                      <span className="el-ev-avg">{curEvidence.count ?? '-'}</span>
                    </div>
                    <div className="el-ev-row">
                      <span className="el-ev-label">coverage gap</span>
                      <span className="el-ev-avg">{curEvidence.gap != null ? curEvidence.gap.toFixed(1) : '-'}</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
            </>
            )}
          </div>
        </section>
      </div>

      <div className="el-wrap">
        <section className="el-sec" id="pipeline">
          <div className="el-kicker">the pipeline</div>
          <h2 className="el-h2">From conversation to decision, in five moves.</h2>
          <p className="el-sub">
            The engine collects evidence, reasons over hypotheses, and only then produces a verdict.
          </p>
          <div className="el-pipe">
            <div className="el-pipe-step">
              <div className="el-pipe-n">01</div>
              <h3>interview</h3>
              <p>a live agent runs the session, turn by turn</p>
            </div>
            <div className="el-pipe-step">
              <div className="el-pipe-n">02</div>
              <h3>evidence</h3>
              <p>statements become evidence, tagged supporting or contradicting</p>
            </div>
            <div className="el-pipe-step">
              <div className="el-pipe-n">03</div>
              <h3>hypotheses</h3>
              <p>candidate hypotheses score up as proof accumulates</p>
            </div>
            <div className="el-pipe-step">
              <div className="el-pipe-n">04</div>
              <h3>competencies</h3>
              <p>evidence aggregates into the skills that matter</p>
            </div>
            <div className="el-pipe-step">
              <div className="el-pipe-n">05</div>
              <h3>decision</h3>
              <p>a single gold verdict, confidence-rated, fully sourced</p>
            </div>
          </div>
          <div className="el-legend">
            <span><span className="el-dot" style={{ background: '#8b5cf6' }} />decision core</span>
            <span><span className="el-dot" style={{ background: '#38bdf8' }} />competencies</span>
            <span><span className="el-dot" style={{ background: '#b45309' }} />hypotheses</span>
            <span><span className="el-dot" style={{ background: '#0c7a54' }} />evidence</span>
            <span><span className="el-dot" style={{ background: '#94a3b8' }} />questions</span>
            <span><span className="el-line" style={{ background: '#0c7a54' }} />supporting</span>
            <span><span className="el-line" style={{ background: '#fb7185' }} />contradicting</span>
          </div>
        </section>
      </div>

      <div className="el-wrap">
        <section className="el-cta" id="cta">
          <div className="el-kicker">get started</div>
          <h2 className="el-h2">Hire with confidence. Interview with proof.</h2>
          <p className="el-sub">Create a free account and run your first AI interview in minutes.</p>
          <Link className="el-btn el-btn-primary" to="/account">
            <Play size={15} /> get started free
          </Link>
        </section>
      </div>

      <footer className="el-foot">
        <div className="el-wrap el-foot-grid">
          <div className="el-foot-brand">
            <div className="el-brand" style={{ justifyContent: 'flex-start' }}>
              <img className="el-logo" src="/favicon.svg" alt="" />AURA
            </div>
            <p className="el-foot-tag">
              The AI interview agent. Every interview leaves a brain behind: questions,
              hypotheses, competencies, and proof feeding one verdict you can audit.
            </p>
          </div>
          <div className="el-foot-col">
            <h4>platform</h4>
            <a href="#graph">brain graph</a>
            <a href="#why">evidence-first</a>
            <a href="#real">real interviews</a>
            <a href="#pipeline">pipeline</a>
            <Link to="/brain-graph">explore the 13 layers</Link>
          </div>
          <div className="el-foot-col">
            <h4>account</h4>
            <Link to="/account">get started</Link>
          </div>
        </div>
        <div className="el-wrap el-foot-bar">
          <span>© {new Date().getFullYear()} AURA, the AI Interview Agent</span>
          <span>built to show its work</span>
        </div>
      </footer>
    </div>
  );
}