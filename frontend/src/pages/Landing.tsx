import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Layers, Play, Bot, Gauge, Palette, ListChecks, Boxes, Route } from 'lucide-react';

/* ════════════════════════════════════════════════════════════════════════
   Landing — full engine presentation port (engine-presentation.html)
   Scoped styles: every selector is prefixed with .engine-landing so the
   rest of the app is unaffected.
   ════════════════════════════════════════════════════════════════════════ */

const EL = '.engine-landing';

const styles = `
${EL} {
  --el-page: #0a0a0b; --el-section: #141416; --el-elevated: #1c1c1f;
  --el-hover: #2f2f33; --el-text: #f2f2f5; --el-secondary: #a8a8b3;
  --el-muted: #8a8a94; --el-border: #2d2d32;
  --el-accent: #8b6ff5; --el-accent-hover: #a08aff; --el-accent-soft: rgba(139,111,245,0.14);
  --el-success: #34d399; --el-warning: #fbbf24; --el-error: #f87171; --el-info: #60a5fa;
  --el-shadow: 0 8px 24px rgba(0,0,0,0.45); --el-radius: 14px;
  background: var(--el-page); color: var(--el-text); line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}
${EL} h1, ${EL} h2, ${EL} h3, ${EL} h4 { font-family: 'Poppins', sans-serif; }
${EL} a { color: var(--el-accent); text-decoration: none; }
${EL} a:hover { color: var(--el-accent-hover); }
${EL} .el-glow { position: fixed; inset: 0; z-index: 0; pointer-events: none;
  background: radial-gradient(600px 320px at 12% -5%, rgba(139,111,245,0.16), transparent 65%),
    radial-gradient(700px 380px at 90% 15%, rgba(96,165,250,0.08), transparent 65%),
    radial-gradient(800px 500px at 50% 110%, rgba(139,111,245,0.10), transparent 60%); }
${EL} .el-grid { position: fixed; inset: 0; z-index: 0; pointer-events: none; opacity: 0.35;
  background-image: linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px);
  background-size: 44px 44px;
  mask-image: radial-gradient(ellipse 90% 70% at 50% 0%, #000 30%, transparent 75%); }
${EL} .el-main { position: relative; z-index: 1; max-width: 1160px; margin: 0 auto; padding: 0 24px; }

/* nav */
${EL} .el-nav { position: sticky; top: 0; z-index: 50; backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px); background: rgba(10,10,11,0.8); border-bottom: 1px solid var(--el-border); }
${EL} .el-nav-inner { max-width: 1160px; margin: 0 auto; padding: 0 24px; height: 60px;
  display: flex; align-items: center; justify-content: space-between; }
${EL} .el-brand { display: flex; align-items: center; gap: 10px; font-family: 'Poppins', sans-serif;
  font-weight: 700; font-size: 15px; color: var(--el-text); }
${EL} .el-brand-mark { width: 28px; height: 28px; border-radius: 8px; display: grid; place-items: center;
  background: linear-gradient(135deg, var(--el-accent), #a78bfa); color: #fff; font-size: 13px; font-weight: 800; }
${EL} .el-nav-links { display: flex; align-items: center; gap: 20px; }
${EL} .el-nav-links a { color: var(--el-secondary); font-size: 13px; font-weight: 500; }
${EL} .el-nav-links a:hover { color: var(--el-text); }
${EL} .el-nav-cta { display: inline-flex; font-family: 'Poppins', sans-serif; font-weight: 600; font-size: 13px;
  padding: 8px 18px; border-radius: 10px; background: linear-gradient(135deg, var(--el-accent), #a78bfa);
  color: #fff !important; }
${EL} .el-nav-cta:hover { background: var(--el-accent-hover); }

/* section rail */
${EL} .el-rail { position: fixed; right: 14px; top: 50%; transform: translateY(-50%); z-index: 40;
  display: flex; flex-direction: column; gap: 6px; padding: 10px 8px; border-radius: 16px;
  background: rgba(20,20,22,0.72); backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
  border: 1px solid var(--el-border); box-shadow: 0 12px 32px rgba(0,0,0,0.5); }
${EL} .el-rail-item { display: flex; align-items: center; gap: 10px; padding: 7px 8px; border-radius: 11px;
  border: 1px solid transparent; background: transparent; cursor: pointer; font: inherit;
  color: var(--el-secondary); transition: all .2s; }
${EL} .el-rail-icon { display: grid; place-items: center; width: 24px; height: 24px; flex: none; }
${EL} .el-rail-label { font-family: 'Poppins', sans-serif; font-size: 11.5px; font-weight: 600;
  white-space: nowrap; opacity: 0; width: 0; overflow: hidden; transform: translateX(8px);
  transition: all .2s; }
${EL} .el-rail-item:hover { background: var(--el-hover); color: var(--el-text); }
${EL} .el-rail-item:hover .el-rail-label, ${EL} .el-rail-item.active .el-rail-label { opacity: 1;
  width: auto; transform: none; }
${EL} .el-rail-item.active { color: #fff; background: linear-gradient(135deg, var(--el-accent), #a78bfa);
  box-shadow: 0 4px 16px rgba(139,111,245,0.4); }
@media (max-width: 860px) { ${EL} .el-rail { display: none; } }

/* hero */
${EL} .el-hero { padding: 96px 0 72px; text-align: center; }
${EL} .el-kicker { display: inline-flex; align-items: center; gap: 8px; font-size: 12px; font-weight: 600;
  letter-spacing: 0.12em; text-transform: uppercase; color: var(--el-accent-hover);
  border: 1px solid rgba(139,111,245,0.35); background: var(--el-accent-soft);
  padding: 6px 14px; border-radius: 999px; margin-bottom: 26px; }
${EL} .el-kicker-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--el-accent-hover); animation: elPulse 2s infinite; }
@keyframes elPulse { 0%,100% { opacity: 1; } 50% { opacity: 0.35; } }
${EL} .el-hero h1 { font-size: clamp(34px, 5.4vw, 60px); font-weight: 800; line-height: 1.08;
  letter-spacing: -0.02em; margin: 0;
  background: linear-gradient(100deg, #fff 30%, #c9b9ff 75%, var(--el-accent-hover));
  -webkit-background-clip: text; background-clip: text; color: transparent; }
${EL} .el-sub { max-width: 640px; margin: 22px auto 0; color: var(--el-secondary); font-size: 16.5px; }
${EL} .el-chips { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; margin-top: 30px; }
${EL} .el-chip { font-size: 12.5px; font-weight: 600; color: var(--el-secondary);
  border: 1px solid var(--el-border); background: var(--el-elevated); padding: 7px 14px; border-radius: 999px; }
${EL} .el-chip.hl { color: var(--el-accent-hover); border-color: rgba(139,111,245,0.4); background: var(--el-accent-soft); }
${EL} .el-cta { display: flex; gap: 14px; justify-content: center; margin-top: 38px; flex-wrap: wrap; }
${EL} .el-btn { display: inline-flex; align-items: center; gap: 8px; font-family: 'Poppins', sans-serif;
  font-weight: 600; font-size: 14px; padding: 12px 26px; border-radius: 12px; cursor: pointer;
  border: 1px solid transparent; transition: transform .15s, box-shadow .15s, background .15s; }
${EL} .el-btn-primary { background: linear-gradient(135deg, var(--el-accent), #a78bfa); color: #fff;
  box-shadow: 0 6px 22px rgba(139,111,245,0.35); }
${EL} .el-btn-primary:hover { transform: translateY(-1px); box-shadow: 0 10px 28px rgba(139,111,245,0.45); color: #fff; }
${EL} .el-btn-ghost { border-color: var(--el-border); color: var(--el-secondary); background: var(--el-elevated); }
${EL} .el-btn-ghost:hover { background: var(--el-hover); color: var(--el-text); }

/* sections */
${EL} section.el-block { padding: 64px 0; }
${EL} .el-sec-head { max-width: 680px; margin-bottom: 40px; }
${EL} .el-sec-tag { font-size: 12px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: var(--el-accent-hover); }
${EL} .el-sec-head h2 { font-size: clamp(24px, 3.4vw, 34px); font-weight: 700; letter-spacing: -0.015em; margin: 8px 0 0; }
${EL} .el-sec-head p { color: var(--el-secondary); font-size: 14.5px; margin-top: 12px; }
${EL} .el-sec-head.center { margin-left: auto; margin-right: auto; text-align: center; }
${EL} .el-reveal { opacity: 0; transform: translateY(18px); transition: opacity .6s ease, transform .6s ease; }
${EL} .el-reveal.visible { opacity: 1; transform: none; }

/* pipeline */
${EL} .el-pipe { display: flex; flex-direction: column; gap: 8px; align-items: center; }
${EL} .el-lane { width: 100%; background: var(--el-section); border: 1px solid var(--el-border); border-radius: var(--el-radius); padding: 22px 20px; }
${EL} .el-lane-label { display: flex; align-items: center; gap: 10px; font-size: 11px; font-weight: 700;
  letter-spacing: 0.12em; text-transform: uppercase; color: var(--el-muted); margin-bottom: 16px; }
${EL} .el-lane-label::after { content: ''; flex: 1; height: 1px; background: var(--el-border); }
${EL} .el-flow { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; align-items: stretch; }
${EL} .el-node { flex: 1 1 150px; min-width: 150px; max-width: 180px; background: var(--el-elevated);
  border: 1px solid var(--el-border); border-radius: 12px; padding: 13px 14px; position: relative;
  transition: border-color .2s, transform .2s, box-shadow .2s; }
${EL} .el-node:hover { transform: translateY(-2px); border-color: rgba(139,111,245,0.5); box-shadow: var(--el-shadow); }
${EL} .el-node.arrow::after { content: ''; position: absolute; top: 50%; right: -11px; width: 12px; height: 2px;
  background: var(--el-muted); opacity: 0.55; }
${EL} .el-node.arrow::before { content: ''; position: absolute; top: calc(50% - 4px); right: -15px;
  border: 4px solid transparent; border-left-color: var(--el-muted); opacity: 0.55; }
${EL} .el-node .el-n-tag { font-size: 9.5px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: var(--el-muted); }
${EL} .el-node .el-n-name { font-family: 'Poppins', sans-serif; font-size: 13px; font-weight: 600; margin-top: 3px; }
${EL} .el-node .el-n-desc { font-size: 11.5px; color: var(--el-secondary); margin-top: 4px; }
${EL} .el-node.loop { border-color: rgba(251,191,36,0.4); }
${EL} .el-node.loop .el-n-tag { color: var(--el-warning); }
${EL} .el-node.finish { border-color: rgba(52,211,153,0.4); }
${EL} .el-node.finish .el-n-tag { color: var(--el-success); }
${EL} .el-node.active-demo { border-color: var(--el-accent); box-shadow: 0 0 0 1px var(--el-accent), 0 0 26px rgba(139,111,245,0.35); transform: translateY(-2px); }
${EL} .el-pipe-arrow-down { color: var(--el-muted); font-size: 20px; opacity: 0.6; line-height: 1; }

/* lifecycle flow */
${EL} .el-lane-count { display: inline-flex; align-items: center; margin-left: auto; }
${EL} .el-llm-badge { display: inline-flex; align-items: center; font-size: 10px; font-weight: 700;
  letter-spacing: 0.06em; padding: 2px 8px; border-radius: 999px; white-space: nowrap; }
${EL} .el-llm-badge.zero { color: var(--el-muted); background: rgba(255,255,255,0.05); border: 1px solid var(--el-border); }
${EL} .el-llm-badge.one { color: var(--el-accent-hover); background: var(--el-accent-soft); border: 1px solid rgba(139,111,245,0.35); }
${EL} .el-llm-badge.six { color: var(--el-warning); background: rgba(251,191,36,0.12); border: 1px solid rgba(251,191,36,0.4); }
${EL} .el-n-meta { display: flex; align-items: center; gap: 8px; margin-top: 8px; flex-wrap: wrap; }
${EL} .el-n-prompt { font-size: 10px; color: var(--el-muted); font-weight: 600; letter-spacing: 0.03em; }
${EL} .el-flow-totals { display: flex; flex-wrap: wrap; gap: 12px; justify-content: center; margin-top: 28px; }
${EL} .el-total-card { flex: 1 1 220px; max-width: 300px; text-align: center; background: var(--el-section);
  border: 1px solid var(--el-border); border-radius: var(--el-radius); padding: 18px 16px; }
${EL} .el-total-num { font-family: 'Poppins', sans-serif; font-size: 28px; font-weight: 800; color: var(--el-accent-hover); }
${EL} .el-total-num.warn { color: var(--el-warning); }
${EL} .el-total-num.sm { font-size: 17px; padding-top: 8px; display: inline-block; }
${EL} .el-total-label { font-size: 11.5px; color: var(--el-secondary); margin-top: 4px; font-weight: 600; }
${EL} .el-total-sub { font-size: 10.5px; color: var(--el-muted); margin-top: 2px; }
${EL} .el-flow-table-wrap { margin-top: 28px; background: var(--el-section); border: 1px solid var(--el-border);
  border-radius: var(--el-radius); overflow-x: auto; }
${EL} .el-flow-table { width: 100%; border-collapse: collapse; font-size: 12.5px; min-width: 720px; }
${EL} .el-flow-table th { text-align: left; font-size: 10.5px; font-weight: 700; letter-spacing: 0.1em;
  text-transform: uppercase; color: var(--el-muted); padding: 12px 18px; border-bottom: 1px solid var(--el-border); }
${EL} .el-flow-table td { padding: 10px 18px; border-bottom: 1px solid var(--el-border); color: var(--el-secondary); }
${EL} .el-flow-table tr:last-child td { border-bottom: none; }
${EL} .el-flow-table tr:hover td { background: rgba(139,111,245,0.05); }
${EL} .el-flow-table td:first-child { color: var(--el-text); font-weight: 600; white-space: nowrap; }
${EL} .el-flow-table td:nth-child(3) { white-space: nowrap; }

/* demo */
${EL} .el-demo { display: grid; grid-template-columns: 1fr 340px; gap: 18px; align-items: start; }
@media (max-width: 860px) { ${EL} .el-demo { grid-template-columns: 1fr; } }
${EL} .el-demo-main { background: var(--el-section); border: 1px solid var(--el-border); border-radius: var(--el-radius);
  padding: 26px; display: flex; flex-direction: column; gap: 20px; min-height: 460px; }
${EL} .el-demo-step-head { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
${EL} .el-phase-chip { font-size: 11px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;
  color: var(--el-info); background: rgba(96,165,250,0.14); border: 1px solid rgba(96,165,250,0.35); padding: 4px 12px; border-radius: 999px; }
${EL} .el-comp-chip { font-size: 11px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;
  color: var(--el-accent-hover); background: var(--el-accent-soft); border: 1px solid rgba(139,111,245,0.35); padding: 4px 12px; border-radius: 999px; }
${EL} .el-step-count { margin-left: auto; font-size: 12px; color: var(--el-muted); font-weight: 600; }
${EL} .el-demo-q { font-family: 'Poppins', sans-serif; font-size: 17px; font-weight: 500; line-height: 1.5;
  background: var(--el-elevated); border: 1px solid var(--el-border); border-radius: 12px; padding: 20px 22px; }
${EL} .el-demo-q::before { content: 'Q'; display: inline-flex; width: 24px; height: 24px; align-items: center;
  justify-content: center; border-radius: 7px; background: var(--el-accent); color: #fff; font-size: 12px;
  font-weight: 700; margin-right: 10px; vertical-align: 2px; }
${EL} .el-demo-a { background: rgba(52,211,153,0.06); border: 1px solid rgba(52,211,153,0.3); border-radius: 12px;
  padding: 18px 20px; font-size: 13.5px; color: var(--el-secondary); display: none; }
${EL} .el-demo-a.show { display: block; animation: elFadeIn .4s ease; }
${EL} .el-demo-a::before { content: 'A'; display: inline-flex; width: 24px; height: 24px; align-items: center;
  justify-content: center; border-radius: 7px; background: var(--el-success); color: #0a0a0b; font-size: 12px;
  font-weight: 700; margin-right: 10px; vertical-align: 2px; }
@keyframes elFadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
${EL} .el-demo-actions { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
${EL} .el-demo-bar { flex: 1; min-width: 200px; height: 6px; border-radius: 999px; background: var(--el-hover); overflow: hidden; }
${EL} .el-demo-bar-fill { height: 100%; width: 0%; border-radius: 999px; background: linear-gradient(90deg, var(--el-accent), #a78bfa); transition: width .6s ease; }
${EL} .el-demo-hint { font-size: 12px; color: var(--el-muted); }
${EL} .el-verdict { display: none; align-items: center; gap: 12px; border: 1px solid rgba(52,211,153,0.4);
  background: rgba(52,211,153,0.1); border-radius: 12px; padding: 16px 18px; }
${EL} .el-verdict.show { display: flex; animation: elFadeIn .5s ease; }
${EL} .el-v-label { font-family: 'Poppins', sans-serif; font-weight: 700; font-size: 16px; color: var(--el-success); }
${EL} .el-v-sub { font-size: 12.5px; color: var(--el-secondary); }
${EL} .el-demo-side { display: flex; flex-direction: column; gap: 14px; }
${EL} .el-side-card { background: var(--el-section); border: 1px solid var(--el-border); border-radius: var(--el-radius); padding: 18px; }
${EL} .el-side-card h4 { font-size: 12px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase;
  color: var(--el-muted); margin: 0 0 12px; }
${EL} .el-dim-row { display: flex; align-items: center; gap: 10px; margin-bottom: 9px; font-size: 12.5px; }
${EL} .el-dim-name { flex: 0 0 108px; color: var(--el-secondary); }
${EL} .el-dim-track { flex: 1; height: 5px; border-radius: 999px; background: var(--el-hover); overflow: hidden; }
${EL} .el-dim-fill { height: 100%; width: 0%; border-radius: 999px; background: #3a3a40; transition: width .7s ease; }
${EL} .el-dim-score { flex: 0 0 30px; text-align: right; color: var(--el-text); font-weight: 600; }
${EL} .el-hypo { display: flex; gap: 9px; align-items: flex-start; font-size: 12.5px; color: var(--el-secondary); margin-bottom: 9px; }
${EL} .el-hypo-dot { width: 7px; height: 7px; border-radius: 50%; margin-top: 5px; flex: none; }
${EL} .el-st { font-size: 10.5px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; margin-top: 2px; display: block; }
${EL} .el-st.confirmed { color: var(--el-success); } ${EL} .el-st.refuted { color: var(--el-error); } ${EL} .el-st.testing { color: var(--el-warning); }
${EL} .el-reflect-text { font-size: 12.5px; color: var(--el-secondary); }

/* demo tabs */
${EL} .el-tabs { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; margin-bottom: 26px; }
${EL} .el-tab { font-family: 'Poppins', sans-serif; font-weight: 600; font-size: 13px; padding: 10px 20px;
  border-radius: 999px; cursor: pointer; border: 1px solid var(--el-border); background: var(--el-elevated);
  color: var(--el-secondary); transition: all .15s; }
${EL} .el-tab:hover { color: var(--el-text); border-color: rgba(139,111,245,0.45); }
${EL} .el-tab.active { color: #fff; border-color: transparent;
  background: linear-gradient(135deg, var(--el-accent), #a78bfa); box-shadow: 0 4px 16px rgba(139,111,245,0.35); }
${EL} .el-taxo { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin: -14px 0 24px; }
${EL} .el-taxo-chip { font-size: 11.5px; font-weight: 600; color: var(--el-accent-hover);
  border: 1px solid rgba(139,111,245,0.35); background: var(--el-accent-soft); padding: 5px 12px; border-radius: 999px; }

/* agents / grid */
${EL} .el-agents-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 14px; }
${EL} .el-agent-card { position: relative; background: var(--el-section); border: 1px solid var(--el-border); border-radius: var(--el-radius);
  padding: 20px; transition: transform .18s, border-color .18s, box-shadow .18s; }
${EL} .el-agent-card:hover { transform: translateY(-3px); border-color: rgba(139,111,245,0.45); box-shadow: var(--el-shadow); }
${EL} .el-agent-icon { width: 36px; height: 36px; border-radius: 10px; display: grid; place-items: center;
  font-family: 'Poppins', sans-serif; font-weight: 700; font-size: 13px; color: #fff;
  background: linear-gradient(135deg, var(--el-accent), #a78bfa); margin-bottom: 14px; }
${EL} .el-agent-icon.i2 { background: linear-gradient(135deg, #60a5fa, #818cf8); }
${EL} .el-agent-icon.i3 { background: linear-gradient(135deg, #34d399, #60a5fa); }
${EL} .el-agent-card h3 { font-size: 14.5px; font-weight: 600; margin: 0; }
${EL} .el-a-tag { position: absolute; top: -10px; right: 14px; z-index: 1; font-size: 10px; font-weight: 700;
  letter-spacing: 0.08em; text-transform: uppercase; color: var(--el-accent-hover);
  background: var(--el-page); border: 1px solid var(--el-border); padding: 3px 10px; border-radius: 999px; }
${EL} .el-agent-card p { font-size: 12.5px; color: var(--el-secondary); margin: 0; }

/* evaluation */
${EL} .el-eval-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
@media (max-width: 860px) { ${EL} .el-eval-grid { grid-template-columns: 1fr; } }
${EL} .el-eval-card { background: var(--el-section); border: 1px solid var(--el-border); border-radius: var(--el-radius); padding: 20px; }
${EL} .el-e-num { font-family: 'Poppins', sans-serif; font-size: 22px; font-weight: 800; color: var(--el-accent-hover); }
${EL} .el-eval-card h3 { font-size: 14px; font-weight: 600; margin: 4px 0 8px; }
${EL} .el-eval-card p { font-size: 12.5px; color: var(--el-secondary); margin: 0; }
${EL} .el-lifecycle { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; margin-top: 26px; align-items: center; }
${EL} .el-lc-node { background: var(--el-elevated); border: 1px solid var(--el-border); border-radius: 999px;
  padding: 9px 18px; font-size: 12.5px; font-weight: 600; color: var(--el-secondary); }
${EL} .el-lc-node.done { color: var(--el-success); border-color: rgba(52,211,153,0.4); background: rgba(52,211,153,0.08); }
${EL} .el-lc-node.dead { color: var(--el-error); border-color: rgba(248,113,113,0.4); background: rgba(248,113,113,0.08); }
${EL} .el-lc-arrow { color: var(--el-muted); font-size: 15px; }

/* styles */
${EL} .el-style-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 14px; }
${EL} .el-style-card { background: var(--el-section); border: 1px solid var(--el-border); border-radius: var(--el-radius); padding: 20px; }
${EL} .el-style-card h3 { font-size: 14px; font-weight: 600; margin: 0; }
${EL} .el-s-desc { font-size: 12.5px; color: var(--el-secondary); margin-top: 8px; }
${EL} .el-s-meta { font-size: 11px; color: var(--el-muted); margin-top: 12px; display: flex; gap: 8px; flex-wrap: wrap; }
${EL} .el-persona-chips { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; margin-top: 30px; }

/* competencies */
${EL} .el-resolve { display: flex; flex-wrap: wrap; gap: 12px; justify-content: center; align-items: center; margin: 26px 0; }
${EL} .el-resolve .el-node { flex: 1 1 200px; max-width: 250px; }
${EL} .el-resolve .el-node.req { border-color: rgba(52,211,153,0.4); }
${EL} .el-resolve .el-node.req .el-n-tag { color: var(--el-success); }
${EL} .el-resolve-arrow { color: var(--el-muted); font-size: 20px; }
${EL} .el-cat-row { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; }
${EL} .el-cat { font-size: 12px; font-weight: 600; padding: 7px 14px; border-radius: 999px;
  border: 1px solid var(--el-border); background: var(--el-elevated); color: var(--el-secondary); }
${EL} .el-cat:nth-child(1) { color: #fbbf24; border-color: rgba(251,191,36,0.35); }
${EL} .el-cat:nth-child(2) { color: #60a5fa; border-color: rgba(96,165,250,0.35); }
${EL} .el-cat:nth-child(3) { color: #34d399; border-color: rgba(52,211,153,0.35); }
${EL} .el-cat:nth-child(4) { color: #f472b6; border-color: rgba(244,114,182,0.35); }
${EL} .el-cat:nth-child(5) { color: #a08aff; border-color: rgba(139,111,245,0.35); }

/* stack */
${EL} .el-stack-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 14px; }
${EL} .el-stack-card { background: var(--el-section); border: 1px solid var(--el-border); border-radius: var(--el-radius); padding: 18px; }
${EL} .el-stk-name { font-family: 'Poppins', sans-serif; font-weight: 600; font-size: 13.5px; }
${EL} .el-stk-use { font-size: 12px; color: var(--el-secondary); margin-top: 4px; }

/* footer */
${EL} footer { border-top: 1px solid var(--el-border); margin-top: 60px; }
${EL} .el-foot-inner { max-width: 1160px; margin: 0 auto; padding: 34px 24px; display: flex;
  justify-content: space-between; align-items: center; gap: 16px; flex-wrap: wrap; }
${EL} .el-foot-inner p { font-size: 12.5px; color: var(--el-muted); }
`;

/* ── Demo data — one canned interview per field (Malaysia-relevant roles) ── */
interface DemoStep {
  phase: string;
  comp: string;
  q: string;
  a: string;
  scores: number[];
  reflection: string;
  nodes: string[];
  hint: string;
}

interface DemoField {
  id: string;
  label: string;
  role: string;
  taxonomy: string[];
  hypos: string[];
  verdict: { label: string; sub: string };
  steps: DemoStep[];
}

const START_NODES = ['s1', 's2', 's3', 's4', 's5', 's6', 's7'];

const DEMO_FIELDS: DemoField[] = [
  {
    id: 'marketing',
    label: 'Marketing Manager',
    role: 'Senior Marketing Manager',
    taxonomy: ['Campaign Strategy', 'Analytical Thinking', 'Stakeholder Management', 'Brand Awareness'],
    hypos: [
      'Strong in full-funnel campaign strategy',
      'Weak in data-driven decision making',
      'Communicates clearly under pressure',
    ],
    verdict: {
      label: 'Hire · confidence 0.82',
      sub: 'Coverage 0.90 · 5 competencies covered · 2 hypotheses confirmed, 0 refuted · no contradictions',
    },
    steps: [
      {
        phase: 'Intro', comp: 'General', nodes: START_NODES,
        hint: 'Engine: planning, strategy, first question…',
        q: "Thanks for joining, Maya. To start, walk me through a campaign you ran in the last year that you're most proud of. What were you trying to move, and how did you structure the plan?",
        a: "The Q3 full-funnel launch for our new SaaS tier across Malaysia and Singapore. I owned strategy end to end: persona mapping across 4 segments, a 6-week channel plan: paid social, search, email nurture, and a webcast partnership. We hit 142% of qualified demo target with a CAC 18% below plan, and I cut the underperforming display budget at week 2 the moment blended CPMs doubled.",
        scores: [8.5, 8.0, 7.5, 6.5, 8.0, 8.0],
        reflection: 'Action: probe: hypothesis "strong in full-funnel strategy" gaining confidence',
      },
      {
        phase: 'Competency probe', comp: 'Campaign Strategy', nodes: ['l1'],
        hint: 'Engine: evaluating…',
        q: "You mentioned cutting display at week 2. Walk me through that decision. What signals did you look at, and how did you reallocate the budget without hurting upper-funnel awareness?",
        a: "I tracked a daily scorecard: CPM, CPC, conversion rate by segment, and SQL contribution share. Display was driving 60% of spend but only 12% of SQLs. I shifted 70% of it into search and email where intent was proven, and used the remaining 30% for a retargeting pool. Awareness dipped 4% but qualified volume rose 19% the following week.",
        scores: [9.0, 8.5, 8.5, 7.0, 8.5, 8.5],
        reflection: 'Action: probe: "strong in campaign strategy" CONFIRMED (0.84). Weak-in-data hypothesis weakening',
      },
      {
        phase: 'Deep probe', comp: 'Analytical Thinking', nodes: ['l2'],
        hint: 'Engine: evaluating…',
        q: "How did you measure incrementality on that retargeting pool, and what would you do differently if you ran it again?",
        a: "Honestly, incrementality was the weak spot; we ran geo holdouts on search only. Retargeting attribution was last-click, so I know some of it was duplication. Next time I'd set up an exclusion audience from the start and measure conversion lift against a 10% holdout before scaling spend.",
        scores: [7.0, 8.0, 9.0, 6.5, 7.5, 8.0],
        reflection: 'Action: change_competency: contradiction detected in analytical depth; switching target to Behavioral',
      },
      {
        phase: 'Behavioral', comp: 'Stakeholder Management', nodes: ['l3'],
        hint: 'Engine: evaluating…',
        q: "Tell me about a time a stakeholder disagreed with your channel plan. What was the conflict, and how did you resolve it?",
        a: "Our CMO wanted to double down on brand video; I had data showing it wouldn't move pipeline. I didn't dismiss it. I ran a small 2-week test against the objection, presented the results with the revenue impact spelled out, and proposed a compromise: 20% brand, 80% performance. She approved it, and that trust carried into the next quarter.",
        scores: [7.5, 9.0, 8.0, 9.0, 8.5, 8.5],
        reflection: 'Action: probe: "communicates clearly" CONFIRMED. Coverage 0.80, one gap remains',
      },
      {
        phase: 'Conclusion', comp: 'Synthesis', nodes: ['l4'],
        hint: 'Engine: evaluating…',
        q: "Final question: if you had a 12-month budget horizon in this role, what would your first 90 days look like?",
        a: "First 30 days: audit attribution, inventory the stack, and meet the sales team to understand what 'qualified' actually means. Days 30-60: fix the measurement baseline and run 3 controlled experiments. Days 60-90: scale the winners and align the channel mix to pipeline contribution, not vanity metrics.",
        scores: [8.5, 8.5, 8.5, 8.0, 8.0, 9.0],
        reflection: 'Sufficiency reached (coverage 0.90). Action: FINISH, then synthesis',
      },
    ],
  },
  {
    id: 'software',
    label: 'Software Engineer',
    role: 'Software Engineer',
    taxonomy: ['Core Language Proficiency', 'System Design', 'Data Structures', 'Code Quality'],
    hypos: [
      'Strong in system design',
      'Weak in deep data structures',
      'Communicates technical ideas clearly',
    ],
    verdict: {
      label: 'Hire · confidence 0.85',
      sub: 'Coverage 0.90 · 5 competencies covered · 2 hypotheses confirmed, 0 refuted · no contradictions',
    },
    steps: [
      {
        phase: 'Intro', comp: 'General', nodes: START_NODES,
        hint: 'Engine: planning, strategy, first question…',
        q: "Thanks for joining, Arif. To start, walk me through a project you're proud of. What did you build, and what problem did it solve?",
        a: "A payment gateway for a fintech startup in Kuala Lumpur. I designed and built the transaction service in Go with PostgreSQL. We absorbed 2x the transaction volume during a campaign period at 99.97% uptime, and brought failure rates from 1.2% down to 0.15%.",
        scores: [8.0, 7.5, 7.5, 6.5, 7.5, 8.0],
        reflection: 'Action: probe: hypothesis "strong in system design" gaining confidence',
      },
      {
        phase: 'Competency probe', comp: 'System Design', nodes: ['l1'],
        hint: 'Engine: evaluating…',
        q: "Your team needed to scale the payment API. Walk me through the design. What were the key trade-offs you made?",
        a: "We moved from synchronous calls to an async queue with idempotency keys. I chose at-least-once delivery plus a dedupe table over exactly-once because the queue couldn't guarantee it; then I added read replicas for queries and circuit breakers so a slow bank API couldn't take down the whole flow.",
        scores: [9.0, 8.0, 8.5, 7.0, 8.0, 8.5],
        reflection: 'Action: probe: "strong in system design" CONFIRMED (0.86)',
      },
      {
        phase: 'Deep probe', comp: 'Data Structures', nodes: ['l2'],
        hint: 'Engine: evaluating…',
        q: "A million users hold in-flight payments at the same time. How would you detect duplicate charge requests at scale?",
        a: "Partition by merchant + transaction key, keep a bloom filter in memory before hitting the unique index on the DB, and backfill from an audit log. I'll be honest; I'd need to validate the bloom filter's false-positive rate against the memory budget before promising it.",
        scores: [7.0, 8.0, 9.0, 6.5, 7.5, 8.0],
        reflection: 'Action: change_competency: contradiction detected in data structures depth; switching to Behavioral',
      },
      {
        phase: 'Behavioral', comp: 'Code Quality', nodes: ['l3'],
        hint: 'Engine: evaluating…',
        q: "A senior engineer rejected your pull request and the team was waiting on it. What happened, and how did you handle it?",
        a: "I didn't argue. We reproduced the race condition she flagged in a test, and I wrote a failing test first, then fixed it. We discussed the design offline, agreed on a simpler approach, and I shipped the revised PR the same day with her sign-off.",
        scores: [7.5, 9.0, 8.0, 9.0, 8.5, 8.5],
        reflection: 'Action: probe: "communicates technical ideas" CONFIRMED. Coverage 0.80, one gap remains',
      },
      {
        phase: 'Conclusion', comp: 'Synthesis', nodes: ['l4'],
        hint: 'Engine: evaluating…',
        q: "Final question: what would your first 90 days look like in this role?",
        a: "Read the payment flows and the incident runbooks, shadow on-call for two weeks, propose a latency budget for the API, and land a small, safe refactor to build trust before touching anything critical.",
        scores: [8.5, 8.5, 8.5, 8.0, 8.0, 9.0],
        reflection: 'Sufficiency reached (coverage 0.90). Action: FINISH, then synthesis',
      },
    ],
  },
  {
    id: 'accountant',
    label: 'Accountant',
    role: 'Accountant',
    taxonomy: ['Financial Reporting', 'Tax Compliance', 'Audit Readiness', 'Attention to Detail'],
    hypos: [
      'Strong in tax compliance',
      'Weak in financial reporting depth',
      'Keeps calm under audit pressure',
    ],
    verdict: {
      label: 'Hire · confidence 0.84',
      sub: 'Coverage 0.88 · 5 competencies covered · 2 hypotheses confirmed, 0 refuted · no contradictions',
    },
    steps: [
      {
        phase: 'Intro', comp: 'General', nodes: START_NODES,
        hint: 'Engine: planning, strategy, first question…',
        q: "Thanks for joining, Siti. To start, walk me through how you closed the books last quarter-end. What did the process look like?",
        a: "For a group of SME clients I closed month-end within 5 working days: bank reconciliations matched daily, accruals reviewed against actuals, and every LHDN and SST deadline tracked on a compliance calendar so e-filing was never rushed. Last year, zero late submissions across 14 entities.",
        scores: [8.0, 7.5, 7.0, 6.5, 7.5, 8.0],
        reflection: 'Action: probe: hypothesis "strong in tax compliance" gaining confidence',
      },
      {
        phase: 'Competency probe', comp: 'Tax Compliance', nodes: ['l1'],
        hint: 'Engine: evaluating…',
        q: "The company receives a letter from LHDN about a discrepancy in last year's return. What do you do, step by step?",
        a: "First, reconcile the discrepancy against source records; never amend before understanding it. Check e-Invoice records and the previous year's working papers, quantify the exposure, and if it's material, engage the tax agent before responding. Always respond inside the timeline and keep everything documented.",
        scores: [9.0, 8.0, 8.5, 7.0, 8.5, 8.5],
        reflection: 'Action: probe: "strong in tax compliance" CONFIRMED (0.85)',
      },
      {
        phase: 'Deep probe', comp: 'Financial Reporting', nodes: ['l2'],
        hint: 'Engine: evaluating…',
        q: "Two departments are counting revenue differently, and the audit is next month. How do you standardise it?",
        a: "Map both treatments against MFRS 15. The recognition point has to be agreed with sales, then written into policy. I'd restate the comparison period so the auditor sees one consistent method. Honestly, a manual workaround existed before, and I'd flag the control gap in the management letter.",
        scores: [7.5, 8.0, 9.0, 6.5, 7.5, 8.0],
        reflection: 'Action: change_competency: contradiction detected in reporting depth; switching to Behavioral',
      },
      {
        phase: 'Behavioral', comp: 'Audit Readiness', nodes: ['l3'],
        hint: 'Engine: evaluating…',
        q: "An auditor challenged your provision for doubtful debts and wanted it much higher. What happened?",
        a: "I presented the ageing analysis and collection history that justified the current provision. She pushed back, so we negotiated with the supporting data and the CFO approved a middle ground. I documented the decision with the evidence trail, and the provision was signed off without further dispute.",
        scores: [7.5, 9.0, 8.0, 9.0, 8.5, 8.5],
        reflection: 'Action: probe: "keeps calm under audit pressure" CONFIRMED. Coverage 0.80',
      },
      {
        phase: 'Conclusion', comp: 'Synthesis', nodes: ['l4'],
        hint: 'Engine: evaluating…',
        q: "Final question: what would your first 90 days look like in this role?",
        a: "Reconcile opening balances against the prior audit file, build the LHDN and SST compliance calendar, review the chart of accounts for gaps, and map the internal controls before touching any period-end close.",
        scores: [8.5, 8.5, 8.5, 8.0, 8.0, 9.0],
        reflection: 'Sufficiency reached (coverage 0.88). Action: FINISH, then synthesis',
      },
    ],
  },
  {
    id: 'teacher',
    label: 'Teacher',
    role: 'Secondary School Teacher',
    taxonomy: ['Subject Mastery', 'Classroom Management', 'Lesson Design', 'Student Engagement'],
    hypos: [
      'Strong in classroom management',
      'Weak in mixed-ability differentiation',
      'Communicates well with parents',
    ],
    verdict: {
      label: 'Hire · confidence 0.83',
      sub: 'Coverage 0.88 · 5 competencies covered · 2 hypotheses confirmed, 0 refuted · no contradictions',
    },
    steps: [
      {
        phase: 'Intro', comp: 'General', nodes: START_NODES,
        hint: 'Engine: planning, strategy, first question…',
        q: "Thanks for joining, Nadia. To start, tell me about a lesson you're proud of designing. What made it work?",
        a: "A Form 4 Mathematics project for an SPM-bound class that had been written off as weak. I replaced textbook exercises with a real survey. The students collected data from their own families, built charts and presented findings. Pass rate on the statistics paper went from 55% to 78%.",
        scores: [8.0, 8.0, 7.5, 6.5, 7.5, 8.0],
        reflection: 'Action: probe: hypothesis "strong in classroom management" gaining confidence',
      },
      {
        phase: 'Competency probe', comp: 'Classroom Management', nodes: ['l1'],
        hint: 'Engine: evaluating…',
        q: "A student is consistently disruptive and it's affecting the whole class. What do you do?",
        a: "A private conversation first. I found out his disruption started when his parents separated. I agreed simple, consistent expectations with him, looped in the counselor and his parents, and praised improvement publicly. Disruptions dropped sharply within three weeks without a single disciplinary referral.",
        scores: [8.5, 8.5, 7.5, 8.5, 8.0, 8.5],
        reflection: 'Action: probe: "strong in classroom management" CONFIRMED (0.84)',
      },
      {
        phase: 'Deep probe', comp: 'Lesson Design', nodes: ['l2'],
        hint: 'Engine: evaluating…',
        q: "Your class has students from A-grade to barely-passing. How do you design lessons that work for both?",
        a: "Tiered worksheets (the same objective, three difficulty levels) plus peer tutoring pairs and exit tickets so I know who needs re-teaching before the next lesson. I'll admit differentiation is my weakest area: planning for three tiers consistently is hard with a 40-student class.",
        scores: [7.5, 8.0, 8.5, 7.0, 7.5, 8.0],
        reflection: 'Action: change_competency: contradiction detected in differentiation; switching to Behavioral',
      },
      {
        phase: 'Behavioral', comp: 'Student Engagement', nodes: ['l3'],
        hint: 'Engine: evaluating…',
        q: "A parent challenged a grade you gave their child and demanded it be changed. How did you handle it?",
        a: "I showed them the rubric and the marked samples side by side, and walked through the assessment criteria. I listened without being defensive, then agreed to set clearer grade expectations in writing next term. The parent left satisfied, and the student understood exactly what to improve.",
        scores: [7.5, 9.0, 8.0, 9.0, 8.5, 8.5],
        reflection: 'Action: probe: "communicates well with parents" CONFIRMED. Coverage 0.80',
      },
      {
        phase: 'Conclusion', comp: 'Synthesis', nodes: ['l4'],
        hint: 'Engine: evaluating…',
        q: "Final question: what would your first 90 days look like at a new school?",
        a: "Observe senior teachers' classes before changing anything, learn the school's discipline culture, audit syllabus coverage against the exam calendar, and build trust with students through consistent, fair expectations.",
        scores: [8.5, 8.5, 8.5, 8.0, 8.0, 9.0],
        reflection: 'Sufficiency reached (coverage 0.88). Action: FINISH, then synthesis',
      },
    ],
  },
  {
    id: 'nurse',
    label: 'Nurse',
    role: 'Staff Nurse',
    taxonomy: ['Clinical Skills', 'Patient Care', 'Emergency Response', 'Documentation'],
    hypos: [
      'Strong in emergency response',
      'Weak in difficult patient communication',
      'Documents accurately under pressure',
    ],
    verdict: {
      label: 'Hire · confidence 0.85',
      sub: 'Coverage 0.90 · 5 competencies covered · 2 hypotheses confirmed, 0 refuted · no contradictions',
    },
    steps: [
      {
        phase: 'Intro', comp: 'General', nodes: START_NODES,
        hint: 'Engine: planning, strategy, first question…',
        q: "Thanks for joining, Aishah. To start, walk me through how you manage a busy ward shift. What does a good shift look like for you?",
        a: "It starts with a proper handover, then triage by acuity before anything else. On a 28-bed medical ward I kept medication rounds on schedule, charted as I went rather than at the end of the shift, and handed over with a clear picture of every patient's trajectory, with zero charting discrepancies all year.",
        scores: [8.0, 7.5, 7.5, 6.5, 8.0, 8.0],
        reflection: 'Action: probe: hypothesis "strong in emergency response" gaining confidence',
      },
      {
        phase: 'Competency probe', comp: 'Emergency Response', nodes: ['l1'],
        hint: 'Engine: evaluating…',
        q: "A patient in your bay suddenly deteriorates: desaturated, unresponsive. Walk me through your response. What do you do first?",
        a: "ABCs first: I assess airway, breathing, circulation while calling for help (code blue), with a clear handover of what I've seen. I start CPR without waiting if there's no pulse, delegate tasks by name so there's no confusion, and nominate someone to document the timeline as it happens. I'm trained on MEWS, so I escalate on the early warning score before it gets to that point.",
        scores: [8.5, 8.0, 8.5, 8.0, 9.0, 8.5],
        reflection: 'Action: probe: "strong in emergency response" CONFIRMED (0.87)',
      },
      {
        phase: 'Deep probe', comp: 'Patient Care', nodes: ['l2'],
        hint: 'Engine: evaluating…',
        q: "A patient refuses a treatment that's clearly indicated. What do you do?",
        a: "Understand the refusal first. Is it fear, cost, or misinformation? I educate on risks and benefits in plain language, involve the doctor and family if the patient agrees, and respect their autonomy in the end. I document the refusal and the discussion accurately, and I never coerce. It's the area I find hardest: walking the line between advocacy and respect.",
        scores: [7.5, 8.5, 8.5, 7.5, 8.0, 8.5],
        reflection: 'Action: change_competency: contradiction detected in difficult-patient communication; switching to Behavioral',
      },
      {
        phase: 'Behavioral', comp: 'Documentation', nodes: ['l3'],
        hint: 'Engine: evaluating…',
        q: "You saw a junior nurse about to give a patient the wrong medication. What did you do?",
        a: "I stopped her hand immediately, checked the chart together, and caught the error before it reached the patient. Afterwards I debriefed privately, without blame, and logged it per protocol. She now double-checks against the chart out loud, and the unit adopted that practice.",
        scores: [7.5, 9.0, 8.0, 9.0, 8.5, 8.5],
        reflection: 'Action: probe: "documents accurately under pressure" CONFIRMED. Coverage 0.80',
      },
      {
        phase: 'Conclusion', comp: 'Synthesis', nodes: ['l4'],
        hint: 'Engine: evaluating…',
        q: "Final question: what would your first 90 days look like at a new hospital?",
        a: "Learn the ward protocols and emergency procedures before anything else, verify the resuscitation equipment, build rapport with the team, and review the documentation standards so my charting matches theirs from day one.",
        scores: [8.5, 8.5, 8.5, 8.0, 8.0, 9.0],
        reflection: 'Sufficiency reached (coverage 0.90). Action: FINISH, then synthesis',
      },
    ],
  },
];

const DIM_NAMES = ['Domain Knowledge', 'Communication', 'Reasoning', 'Behavioral', 'Confidence', 'Completeness'];
const DIM_COLORS = ['#8b6ff5', '#34d399', '#60a5fa', '#fbbf24', '#f472b6', '#a08aff'];

function hypoStatus(step: number): string[] {
  return ['testing', 'testing', 'testing'].map((s, i) => {
    if (i === 0 && step >= 2) return 'confirmed';
    if (i === 1 && step >= 3) return 'refuted';
    if (i === 2 && step >= 3) return 'confirmed';
    return s;
  });
}

interface FlowNode {
  tag: string;
  name: string;
  desc: string;
  badge: string;
  tone: 'zero' | 'one' | 'six';
  prompt?: string;
}

interface FlowLane {
  label: string;
  count: string;
  tone: 'zero' | 'one' | 'six';
  nodeClass?: string;
  nodes: FlowNode[];
}

const FLOW_LANES: FlowLane[] = [
  {
    label: 'Org setup: docs and templates',
    count: '0 LLM calls',
    tone: 'zero',
    nodes: [
      { tag: 'Docs', name: 'Department Docs', desc: 'Org knowledge base to Pinecone RAG index', badge: 'LLM ×0', tone: 'zero' },
      { tag: 'Scorecard', name: 'Scorecard Template', desc: 'Org-curated competencies (JSONB)', badge: 'LLM ×0', tone: 'zero' },
      { tag: 'Template', name: 'Interview Template', desc: 'Department-level competencies', badge: 'LLM ×0', tone: 'zero' },
    ],
  },
  {
    label: 'Public listing: candidate enters',
    count: '0 LLM calls',
    tone: 'zero',
    nodes: [
      { tag: 'Listing', name: 'Publish Listing', desc: 'Marketplace entry: mode, expiry', badge: 'LLM ×0', tone: 'zero' },
      { tag: 'Enter', name: 'Candidate Enters', desc: 'Starts session from public link', badge: 'LLM ×0', tone: 'zero' },
      { tag: 'Resolve', name: 'Competency Resolver', desc: 'Scorecard, template, or default', badge: 'LLM ×0', tone: 'zero' },
    ],
  },
  {
    label: 'Session start: 2 LLM calls, 5 deterministic nodes',
    count: '2 LLM calls',
    tone: 'one',
    nodes: [
      { tag: 'Init', name: 'Session Init', desc: 'Seed state, timeline, mode', badge: 'LLM ×0', tone: 'zero' },
      { tag: 'RAG', name: 'Department Context', desc: 'Pinecone vector retrieval', badge: 'LLM ×0', tone: 'zero' },
      { tag: 'Profile', name: 'Candidate Profile', desc: 'DB load + evidence', badge: 'LLM ×0', tone: 'zero' },
      { tag: 'Plan', name: 'Competency Planner', desc: 'Rank gaps, pick target', badge: 'LLM ×0', tone: 'zero' },
      { tag: 'Strategy', name: 'Strategy Brain', desc: 'Persona, difficulty, thresholds', badge: 'LLM ×1', tone: 'one', prompt: 'strategy_brain.md' },
      { tag: 'Thesis', name: 'Hypothesis Engine', desc: 'Form candidate beliefs', badge: 'LLM ×0', tone: 'zero' },
      { tag: 'Ask', name: 'Question Generator', desc: 'LLM question #1, hypothesis-targeted', badge: 'LLM ×1', tone: 'one', prompt: 'question_generation.md' },
    ],
  },
  {
    label: 'Answer loop: repeated per answer',
    count: '2-7 LLM calls',
    tone: 'six',
    nodeClass: 'loop',
    nodes: [
      { tag: 'Evaluate', name: 'Unified Evaluator', desc: 'Unified ×1, parallel ×6', badge: 'LLM ×1 · ×6', tone: 'six', prompt: 'unified_evaluator.md' },
      { tag: 'Extract', name: 'Evidence Extractor', desc: 'Score, cite, persist', badge: 'LLM ×0', tone: 'zero' },
      { tag: 'Reflect', name: 'Reflection Engine', desc: 'Sufficiency, contradictions', badge: 'LLM ×0', tone: 'zero' },
      { tag: 'Replan', name: 'Planner + Hypotheses', desc: 'Only on change_competency', badge: 'LLM ×0', tone: 'zero' },
      { tag: 'Ask', name: 'Question Generator', desc: 'LLM follow-up or new angle', badge: 'LLM ×1', tone: 'one', prompt: 'question_generation.md' },
    ],
  },
  {
    label: 'Finish: synthesis report',
    count: '1 LLM call',
    tone: 'one',
    nodeClass: 'finish',
    nodes: [
      { tag: 'Finish', name: 'Synthesis Node', desc: 'Weighted score, evidence map, verdict', badge: 'LLM ×1', tone: 'one', prompt: 'synthesis.md' },
    ],
  },
];

const FLOW_TABLE: [string, string, string, string][] = [
  ['Session Init', 'Session start', '×0', 'Deterministic'],
  ['Department Context', 'Session start', '×0', 'Pinecone vector retrieval'],
  ['Candidate Profile', 'Session start', '×0', 'DB load + evidence state'],
  ['Competency Planner', 'Start + replan', '×0', 'Deterministic planner'],
  ['Strategy Brain', 'Session start (cached)', '×1', 'prompts/strategy_brain.md'],
  ['Hypothesis Engine', 'Start + every answer', '×0', 'Confidence heuristics'],
  ['Question Generator', 'Start + every answer', '×1', 'prompts/question_generation.md'],
  ['Unified Evaluator', 'Every answer', '×1 · ×6', 'unified_evaluator.md + 6 dim prompts'],
  ['Evidence Extractor', 'Every answer', '×0', 'Persist + competency summaries'],
  ['Reflection Engine', 'Every answer', '×0', 'Thresholds + verdict logic'],
  ['Synthesis Node', 'Session end (once)', '×1', 'prompts/synthesis.md'],
];

const SECTION_IDS = [
  ['pipeline', 'Pipeline', Layers],
  ['flow', 'Flow', Route],
  ['demo', 'Live Demo', Play],
  ['agents', 'Agents', Bot],
  ['evaluation', 'Evaluation', Gauge],
  ['styles', 'Styles', Palette],
  ['competencies', 'Competencies', ListChecks],
  ['stack', 'Stack', Boxes],
] as const;

export function Landing() {
  const rootRef = useRef<HTMLDivElement>(null);
  const [currentField, setCurrentField] = useState('marketing');
  const [step, setStep] = useState(0);
  const [answered, setAnswered] = useState(false);
  const [finished, setFinished] = useState(false);
  const [showVerdict, setShowVerdict] = useState(false);
  const [scores, setScores] = useState<number[]>(Array(6).fill(0));
  const [hypos, setHypos] = useState<string[]>(['testing', 'testing', 'testing']);
  const [reflection, setReflection] = useState(DEMO_FIELDS[0].steps[0].reflection);
  const [activeSection, setActiveSection] = useState('pipeline');

  useEffect(() => {
    const io = new IntersectionObserver((entries) => {
      entries.forEach(e => { if (e.isIntersecting) setActiveSection(e.target.id); });
    }, { rootMargin: '-45% 0px -50% 0px' });
    SECTION_IDS.forEach(([id]) => {
      const el = document.getElementById(id);
      if (el) io.observe(el);
    });
    return () => io.disconnect();
  }, []);

  const scrollToSection = (id: string) => {
    const el = document.getElementById(id);
    if (!el) return;
    const top = el.getBoundingClientRect().top + window.scrollY - 70;
    window.scrollTo({ top, behavior: 'smooth' });
  };

  useEffect(() => {
    const el = rootRef.current;
    if (!el) return;
    const els = el.querySelectorAll('.el-reveal');
    const io = new IntersectionObserver((entries) => {
      entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('visible'); io.unobserve(e.target); } });
    }, { threshold: 0.12 });
    els.forEach(n => io.observe(n));
    els.forEach(n => { if (n.getBoundingClientRect().top < window.innerHeight * 0.85) n.classList.add('visible'); });
    return () => io.disconnect();
  }, []);

  const field = DEMO_FIELDS.find(f => f.id === currentField) ?? DEMO_FIELDS[0];
  const cur = field.steps[step];

  const handleFieldSwitch = (id: string) => {
    if (id === currentField) return;
    setCurrentField(id);
    setStep(0);
    setAnswered(false);
    setFinished(false);
    setShowVerdict(false);
    setScores(Array(6).fill(0));
    setHypos(['testing', 'testing', 'testing']);
    const f = DEMO_FIELDS.find(x => x.id === id) ?? DEMO_FIELDS[0];
    setReflection(f.steps[0].reflection);
  };

  const handleDemoClick = () => {
    if (finished) return;
    if (!answered) {
      setAnswered(true);
      setScores(cur.scores);
      setHypos(hypoStatus(step));
      setReflection(cur.reflection);
      if (step >= field.steps.length - 1) {
        setTimeout(() => setShowVerdict(true), 600);
      }
      return;
    }
    if (step >= field.steps.length - 1) {
      setFinished(true);
      return;
    }
    const next = step + 1;
    setStep(next);
    setAnswered(false);
    setScores(Array(6).fill(0));
    setHypos(['testing', 'testing', 'testing']);
    setReflection(field.steps[next].reflection);
  };

  const btnLabel = finished
    ? 'Interview complete'
    : answered
      ? step >= field.steps.length - 1 ? 'Finish interview' : 'Next question →'
      : step < field.steps.length - 1 ? 'Reveal candidate answer' : 'Reveal final answer';

  const activeSet = new Set(answered ? cur.nodes : step === 0 ? field.steps[0].nodes : []);

  return (
    <div ref={rootRef} className="engine-landing min-h-screen">
      <style>{styles}</style>
      <div className="el-glow" />
      <div className="el-grid" />

      <nav className="el-nav">
        <div className="el-nav-inner">
          <Link to="/" className="el-brand">
            <span className="el-brand-mark">AI</span>
            AI Interview Agent
          </Link>
          <div className="el-nav-links">
            <Link to="/candidate/login">Candidate Login</Link>
            <Link to="/login">Sign In</Link>
            <Link to="/register" className="el-nav-cta">Get Started</Link>
          </div>
        </div>
      </nav>

      <nav className="el-rail" aria-label="Page sections">
        {SECTION_IDS.map(([id, label, Icon]) => (
          <button key={id} className={`el-rail-item ${activeSection === id ? 'active' : ''}`} onClick={() => scrollToSection(id)}>
            <span className="el-rail-icon"><Icon size={17} strokeWidth={2.2} /></span>
            <span className="el-rail-label">{label}</span>
          </button>
        ))}
      </nav>

      <div className="el-main">
        {/* ── HERO ── */}
        <section className="el-hero">
          <span className="el-kicker"><span className="el-kicker-dot" /> Evidence-driven interview engine</span>
          <h1>An AI interviewer that<br />thinks like a hiring manager</h1>
          <p className="el-sub">A LangGraph-powered agentic system that forms hypotheses about every candidate, probes them with targeted questions, extracts evidence from every answer, and reflects until it can defend a hiring decision.</p>
          <div className="el-chips">
            <span className="el-chip hl">Field-agnostic</span>
            <span className="el-chip">6-dimension evaluation</span>
            <span className="el-chip">Hypothesis engine</span>
            <span className="el-chip">RAG department context</span>
            <span className="el-chip">Typing · Voice · Avatar</span>
            <span className="el-chip">Public interview marketplace</span>
          </div>
          <div className="el-cta">
            <Link to="/register" className="el-btn el-btn-primary">Get Started</Link>
            <Link to="/login" className="el-btn el-btn-ghost">Sign In</Link>
          </div>
        </section>

        {/* ── PIPELINE ── */}
        <section className="el-block" id="pipeline">
          <div className="el-sec-head center">
            <div className="el-sec-tag">Architecture</div>
            <h2>The v4 evidence-driven pipeline</h2>
            <p>Two lanes. On start, the engine builds a plan and a strategy. On every answer, it evaluates, extracts evidence, and reflects, looping until the evidence is sufficient.</p>
          </div>
          <div className="el-pipe el-reveal">
            <div className="el-lane">
              <div className="el-lane-label">Session start: plan, strategy &amp; first question</div>
              <div className="el-flow">
                {[
                  ['s1', 'Init', 'Session Init', 'Seed state, timeline, mode'],
                  ['s2', 'RAG', 'Department Context', 'Inject org knowledge base'],
                  ['s3', 'Profile', 'Candidate Profile', 'Load strengths, history'],
                  ['s4', 'Plan', 'Competency Planner', 'Rank gaps, pick target'],
                  ['s5', 'Strategy', 'Strategy Brain', 'LLM strategy + persona'],
                  ['s6', 'Thesis', 'Hypothesis Engine', 'Form candidate beliefs'],
                  ['s7', 'Ask', 'Question Generator', 'Targeted question #1'],
                ].map(([id, tag, name, desc]) => (
                  <div key={id} className={`el-node ${id === 's7' ? '' : 'arrow '}${activeSet.has(id) ? 'active-demo' : ''}`}>
                    <div className="el-n-tag">{tag}</div>
                    <div className="el-n-name">{name}</div>
                    <div className="el-n-desc">{desc}</div>
                  </div>
                ))}
              </div>
            </div>
            <div className="el-pipe-arrow-down">↓</div>
            <div className="el-lane">
              <div className="el-lane-label">Answer loop: evaluate · extract · reflect (repeat)</div>
              <div className="el-flow">
                {[
                  ['l1', 'Evaluate', 'Unified Evaluator', '6 dimensions, 0-10'],
                  ['l2', 'Extract', 'Evidence Extractor', 'Score, cite, persist'],
                  ['l3', 'Reflect', 'Reflection Engine', 'Sufficiency, contradictions, verdict'],
                  ['l4', 'Replan', 'Planner + Hypotheses', 'Next competency, next thesis'],
                  ['l5', 'Ask', 'Question Generator', 'Follow-up or new angle'],
                ].map(([id, tag, name, desc]) => (
                  <div key={id} className={`el-node ${id === 'l5' ? '' : 'arrow '}loop ${activeSet.has(id) ? 'active-demo' : ''}`}>
                    <div className="el-n-tag">{tag}</div>
                    <div className="el-n-name">{name}</div>
                    <div className="el-n-desc">{desc}</div>
                  </div>
                ))}
              </div>
            </div>
            <div className="el-pipe-arrow-down">↓</div>
            <div className="el-lane">
              <div className="el-flow">
                <div className="el-node finish" style={{ flex: '1 1 260px', maxWidth: 340 }}>
                  <div className="el-n-tag">Finish</div>
                  <div className="el-n-name">Synthesis</div>
                  <div className="el-n-desc">Final report: weighted score, evidence map, hiring verdict with confidence</div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ── END-TO-END FLOW ── */}
        <section className="el-block" id="flow">
          <div className="el-sec-head center">
            <div className="el-sec-tag">Lifecycle</div>
            <h2>From org docs to candidate to verdict</h2>
            <p>Departments publish a public listing, candidates enter, and every engine node carries an exact LLM budget. Each node below shows its calls and prompt, so a session's cost is always visible.</p>
          </div>
          <div className="el-pipe el-reveal">
            {FLOW_LANES.map((lane, li) => (
              <div key={lane.label} style={{ width: '100%' }}>
                <div className="el-lane">
                  <div className="el-lane-label">
                    {lane.label}
                    <span className={`el-lane-count el-llm-badge ${lane.tone}`}>{lane.count}</span>
                  </div>
                  <div className="el-flow">
                    {lane.nodes.map((n, i) => (
                      <div key={n.tag} className={`el-node ${i < lane.nodes.length - 1 ? 'arrow ' : ''}${lane.nodeClass || ''}`}
                        style={lane.nodeClass === 'finish' ? { flex: '1 1 260px', maxWidth: 340 } : undefined}>
                        <div className="el-n-tag">{n.tag}</div>
                        <div className="el-n-name">{n.name}</div>
                        <div className="el-n-desc">{n.desc}</div>
                        <div className="el-n-meta">
                          <span className={`el-llm-badge ${n.tone}`}>{n.badge}</span>
                          {n.prompt && <span className="el-n-prompt">{n.prompt}</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
                {li < FLOW_LANES.length - 1 && <div className="el-pipe-arrow-down">↓</div>}
              </div>
            ))}
          </div>
          <div className="el-flow-totals">
            <div className="el-total-card">
              <div className="el-total-num">22</div>
              <div className="el-total-label">LLM calls per 10-question session</div>
              <div className="el-total-sub">Unified evaluator mode</div>
            </div>
            <div className="el-total-card">
              <div className="el-total-num warn">72</div>
              <div className="el-total-label">LLM calls per 10-question session</div>
              <div className="el-total-sub">Parallel mode: 6 dimension evaluators per answer</div>
            </div>
            <div className="el-total-card">
              <div className="el-total-num sm">3-model fallback chain</div>
              <div className="el-total-label">Groq, local, OpenRouter</div>
              <div className="el-total-sub">Extra calls only when a provider fails</div>
            </div>
          </div>
          <div className="el-flow-table-wrap">
            <table className="el-flow-table">
              <thead>
                <tr>
                  <th>Node</th>
                  <th>Called when</th>
                  <th>LLM calls</th>
                  <th>Prompt</th>
                </tr>
              </thead>
              <tbody>
                {FLOW_TABLE.map(([node, when, calls, prompt]) => (
                  <tr key={node}>
                    <td>{node}</td>
                    <td>{when}</td>
                    <td><span className={`el-llm-badge ${calls === '×0' ? 'zero' : calls.includes('·') ? 'six' : 'one'}`}>{calls}</span></td>
                    <td>{prompt}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* ── LIVE DEMO ── */}
        <section className="el-block" id="demo">
          <div className="el-sec-head center">
            <div className="el-sec-tag">Interactive demo</div>
            <h2>A real session, simulated</h2>
            <p>Watch the engine interview candidates across <b>five Malaysia-relevant fields</b>. Pick a role. The pipeline above lights up as it runs.</p>
          </div>
          <div className="el-tabs">
            {DEMO_FIELDS.map(f => (
              <button key={f.id} className={`el-tab ${f.id === currentField ? 'active' : ''}`} onClick={() => handleFieldSwitch(f.id)}>
                {f.label}
              </button>
            ))}
          </div>
          <div className="el-taxo">
            {field.taxonomy.map(t => (
              <span className="el-taxo-chip" key={t}>{t}</span>
            ))}
          </div>
          <div className="el-demo el-reveal">
            <div className="el-demo-main">
              <div className="el-demo-step-head">
                <span className="el-phase-chip">{cur.phase}</span>
                <span className="el-comp-chip">{cur.comp}</span>
                <span className="el-step-count">Step {step + 1} / {field.steps.length}</span>
              </div>
              <div className="el-demo-q">{cur.q}</div>
              <div className={`el-demo-a ${answered ? 'show' : ''}`}>{cur.a}</div>
              <div className="el-demo-actions">
                <button className="el-btn el-btn-primary" onClick={handleDemoClick} disabled={finished} style={{ minWidth: 170, justifyContent: 'center' }}>
                  {btnLabel}
                </button>
                <div className="el-demo-bar"><div className="el-demo-bar-fill" style={{ width: answered ? '100%' : '0%' }} /></div>
                <span className="el-demo-hint">{answered ? 'Engine: scored 6 dimensions · extracted evidence · reflected' : cur.hint}</span>
              </div>
              <div className={`el-verdict ${showVerdict ? 'show' : ''}`}>
                <div>
                  <div className="el-v-label">{field.verdict.label}</div>
                  <div className="el-v-sub">{field.verdict.sub}</div>
                </div>
              </div>
            </div>
            <div className="el-demo-side">
              <div className="el-side-card">
                <h4>Live evidence</h4>
                {DIM_NAMES.map((name, i) => (
                  <div className="el-dim-row" key={name}>
                    <span className="el-dim-name">{name}</span>
                    <div className="el-dim-track"><div className="el-dim-fill" style={{ width: `${scores[i] * 10}%`, background: scores[i] ? DIM_COLORS[i] : '#3a3a40' }} /></div>
                    <span className="el-dim-score">{scores[i].toFixed(1)}</span>
                  </div>
                ))}
              </div>
              <div className="el-side-card">
                <h4>Hypothesis engine</h4>
                {field.hypos.map((h, i) => (
                  <div className="el-hypo" key={h}>
                    <span className="el-hypo-dot" style={{ background: hypos[i] === 'confirmed' ? 'var(--el-success)' : hypos[i] === 'refuted' ? 'var(--el-error)' : 'var(--el-warning)' }} />
                    <div><span className={`el-st ${hypos[i]}`}>{hypos[i]}</span>{h}</div>
                  </div>
                ))}
              </div>
              <div className="el-side-card">
                <h4>Reflection</h4>
                <div className="el-reflect-text">{reflection}</div>
              </div>
            </div>
          </div>
        </section>

        {/* ── AGENTS ── */}
        <section className="el-block" id="agents">
          <div className="el-sec-head">
            <div className="el-sec-tag">Agentic core</div>
            <h2>Specialist nodes, one shared memory</h2>
            <p>Every node reads and writes a single <b>InterviewState</b> (the shared blackboard), so planning, evidence and reflection always agree with each other.</p>
          </div>
          <div className="el-agents-grid el-reveal">
            {[
              ['CB', '', 'Candidate Profile Node', 'Context', 'Loads the candidate\'s history, accumulates strengths, weaknesses and risk flags from evidence across sessions.'],
              ['DC', 'i2', 'Department Context Node', 'Context', 'Retrieves org documents (RAG) so questions are grounded in the role\'s actual requirements.'],
              ['CP', 'i3', 'Competency Planner', 'Planning', 'Builds the coverage plan: gap per competency, priority, evidence required; picks the next target.'],
              ['SB', '', 'Strategy Brain', 'Planning', 'LLM-driven interview strategy: question approach, persona, difficulty curve and early-termination thresholds.'],
              ['HY', 'i2', 'Hypothesis Engine', 'Memory', 'Forms beliefs about the candidate, updates confidence from evidence, confirms or refutes them.'],
              ['QG', 'i3', 'Question Generator', 'Asking', 'Deterministic question templates per competency, difficulty-aware, follow-up aware, persona-aware.'],
              ['EV', '', 'Unified Evaluator', 'Judging', 'Scores every answer on 6 dimensions with cited evidence, in unified or parallel LLM mode.'],
              ['EX', 'i2', 'Evidence Extractor', 'Memory', 'Converts evaluations into persisted evidence records and live competency summaries.'],
              ['RF', 'i3', 'Reflection Engine', 'Judging', 'Detects contradictions, weighs coverage, decides: probe deeper, change competency, or finish.'],
              ['SY', '', 'Synthesis Node', 'Output', 'Produces the final report: composite score, hiring verdict, confidence and evidence map.'],
            ].map(([icon, tone, name, tag, desc]) => (
              <div className="el-agent-card" key={name}>
                <div className={`el-agent-icon ${tone}`}>{icon}</div>
                <div className="el-a-tag">{tag}</div>
                <h3>{name}</h3>
                <p>{desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* ── EVALUATION ── */}
        <section className="el-block" id="evaluation">
          <div className="el-sec-head">
            <div className="el-sec-tag">Judgment</div>
            <h2>Six dimensions, one composite score</h2>
            <p>Every answer is scored 0-10 with evidence citations, then weighted into a composite. The dimension label adapts to the field: <b>Technical Knowledge</b> for engineering, <b>Domain Knowledge</b> for anything else.</p>
          </div>
          <div className="el-eval-grid el-reveal">
            {[
              ['01', 'Domain / Technical Knowledge', 'Correctness of concepts, depth, terminology, awareness of trade-offs.'],
              ['02', 'Communication', 'Clarity, structure, conciseness, ability to explain complex ideas simply.'],
              ['03', 'Reasoning', 'Logical structure, alternatives considered, cause-effect analysis.'],
              ['04', 'Behavioral', 'Teamwork, ownership, self-awareness, STAR-style evidence.'],
              ['05', 'Confidence', 'Certainty, honest unknowns, no false expertise.'],
              ['06', 'Completeness', 'Full coverage of the question, sub-parts, missing elements.'],
            ].map(([num, name, desc]) => (
              <div className="el-eval-card" key={num}>
                <div className="el-e-num">{num}</div>
                <h3>{name}</h3>
                <p>{desc}</p>
              </div>
            ))}
          </div>
          <div className="el-lifecycle el-reveal">
            <span className="el-lc-node">Hypothesis: untested</span>
            <span className="el-lc-arrow">→</span>
            <span className="el-lc-node">testing</span>
            <span className="el-lc-arrow">→</span>
            <span className="el-lc-node done">confirmed</span>
            <span className="el-lc-arrow">or</span>
            <span className="el-lc-node dead">refuted</span>
            <span className="el-lc-arrow">→</span>
            <span className="el-lc-node done">Hiring verdict + confidence</span>
          </div>
        </section>

        {/* ── STYLES ── */}
        <section className="el-block" id="styles">
          <div className="el-sec-head">
            <div className="el-sec-tag">Personality</div>
            <h2>Styles and personas</h2>
            <p>Each style tunes the difficulty curve, question mix and persona; the same evidence engine underneath.</p>
          </div>
          <div className="el-style-grid el-reveal">
            {[
              ['STANDARD', 'Balanced evidence-driven interview with a warm, structured flow.', 'Persona: friendly · max 10-20 Q'],
              ['CONVERSATIONAL', 'Natural back-and-forth, lighter probing, high rapport.', 'Persona: conversational'],
              ['TECHNICAL_DEEP', 'Depth-first technical probes, hard difficulty curve, tighter evidence thresholds.', 'Persona: strict'],
              ['BEHAVIORAL', 'STAR-heavy sessions targeting behavioral competencies.', 'Persona: empathetic'],
              ['CASE_STUDY', 'Scenario-driven questions with staged difficulty progression.', 'Persona: analytical'],
            ].map(([name, desc, meta]) => (
              <div className="el-style-card" key={name}>
                <h3>{name}</h3>
                <p className="el-s-desc">{desc}</p>
                <div className="el-s-meta"><span>{meta}</span></div>
              </div>
            ))}
          </div>
          <div className="el-persona-chips el-reveal">
            {['friendly', 'formal', 'strict', 'mentor', 'conversational', 'empathetic', 'analytical', 'faang', 'stress'].map(p => (
              <span className="el-chip" key={p}>{p}</span>
            ))}
          </div>
        </section>

        {/* ── COMPETENCIES ── */}
        <section className="el-block" id="competencies">
          <div className="el-sec-head">
            <div className="el-sec-tag">Field-agnostic by design</div>
            <h2>Competencies come from the org, not the code</h2>
            <p>At session start, the engine resolves the competency taxonomy in priority order. No schema changes, no retraining: a marketing department, a nursing team and a data org all get their own competency model.</p>
          </div>
          <div className="el-resolve el-reveal">
            <div className="el-node req">
              <div className="el-n-tag">1 · Highest priority</div>
              <div className="el-n-name">Scorecard template</div>
              <div className="el-n-desc">Org-curated competencies with weights</div>
            </div>
            <div className="el-resolve-arrow">→</div>
            <div className="el-node req">
              <div className="el-n-tag">2</div>
              <div className="el-n-name">Interview template</div>
              <div className="el-n-desc">Department-level competency definitions</div>
            </div>
            <div className="el-resolve-arrow">→</div>
            <div className="el-node">
              <div className="el-n-tag">3 · Fallback</div>
              <div className="el-n-name">Default taxonomy</div>
              <div className="el-n-desc">22-engineer-built competencies</div>
            </div>
          </div>
          <div className="el-cat-row el-reveal">
            <span className="el-cat">technical</span>
            <span className="el-cat">behavioral</span>
            <span className="el-cat">cognitive</span>
            <span className="el-cat">experience</span>
            <span className="el-cat">custom (e.g. campaign_strategy)</span>
          </div>
        </section>

        {/* ── STACK ── */}
        <section className="el-block" id="stack">
          <div className="el-sec-head">
            <div className="el-sec-tag">Platform</div>
            <h2>Built to ship</h2>
            <p>A production-grade stack behind the engine.</p>
          </div>
          <div className="el-stack-grid el-reveal">
            {[
              ['LangGraph', 'Agent state machine: question, evaluation & reflection subgraphs'],
              ['FastAPI', 'Typing, voice and avatar APIs over WebSockets + REST'],
              ['PostgreSQL + Supabase', 'Sessions, evidence store, scorecards, org data'],
              ['Pinecone RAG', 'Department documents → grounded interview context'],
              ['Groq / OpenRouter / OpenAI', 'Swappable LLM providers with configurable model chain'],
              ['ElevenLabs', 'Streamed TTS with viseme timestamps for the avatar'],
              ['React + Vite', 'Typing, voice and avatar interview rooms'],
              ['Alembic', 'Versioned migrations, indexed and production-safe schema'],
            ].map(([name, use]) => (
              <div className="el-stack-card" key={name}>
                <div className="el-stk-name">{name}</div>
                <div className="el-stk-use">{use}</div>
              </div>
            ))}
          </div>
        </section>
      </div>

      <footer>
        <div className="el-foot-inner">
          <p>AI Interview Agent · evidence-driven, field-agnostic interview engine</p>
          <p>Final Year Project · v4 engine</p>
        </div>
      </footer>
    </div>
  );
}
