import { Link } from 'react-router-dom';
import { Building2, UserRound, ArrowRight, Sparkles } from 'lucide-react';

/* ════════════════════════════════════════════════════════════════════════
   AccountChoice - "who are you?" gate: hiring teams vs. candidates.
   Single centered frosted panel with the AURA logo on top.
   ════════════════════════════════════════════════════════════════════════ */

const EL = '.account-choice';

const styles = `
${EL} {
  --ac-page: #f6f7f4; --ac-text: #17201d; --ac-secondary: #3d4a44; --ac-muted: #5a6660;
  --ac-accent: #0c6b58; --ac-accent-hover: #085244; --ac-accent-soft: rgba(12,107,88,0.10);
  --ac-glass: #ffffff; --ac-glass-2: #fbfcfa;
  --ac-glass-border: #e2e6e1; --ac-glass-border-hi: #c9d1cb;
  --ac-blur: none;
  --ac-glass-shadow: 0 1px 2px rgba(23,32,29,0.05), 0 8px 24px rgba(23,32,29,0.06);
  min-height: 100vh; height: 100vh; overflow: hidden; background: var(--ac-page); color: var(--ac-text); line-height: 1.6;
  display: flex; align-items: center; justify-content: center; padding: 24px;
  -webkit-font-smoothing: antialiased;
}
body:has(${EL}) { margin: 0; background: var(--ac-page); }
html:has(${EL}) { background: var(--ac-page); }
${EL} h1, ${EL} h2, ${EL} h3 { font-family: 'Archivo', sans-serif; }
${EL} a { color: var(--ac-accent); text-decoration: none; }
${EL} a:hover { color: var(--ac-accent-hover); }

/* paper texture grid */
${EL} .ac-glow { position: fixed; inset: 0; z-index: 0; pointer-events: none; opacity: 0.30;
  background-image: linear-gradient(to bottom, rgba(23,32,29,0.05) 1px, transparent 1px),
    linear-gradient(to right, rgba(23,32,29,0.05) 1px, transparent 1px);
  background-size: 46px 46px; }

/* content panel */
${EL} .ac-panel { position: relative; z-index: 1; width: 100%; max-width: 700px; padding: 30px 32px 24px;
  background: var(--ac-glass); border: 1px solid var(--ac-glass-border); border-radius: 16px;
  box-shadow: var(--ac-glass-shadow); }
${EL} .ac-brand { display: flex; align-items: center; justify-content: center; gap: 10px;
  font-family: 'Archivo', sans-serif; font-weight: 800; font-size: 18px; letter-spacing: .18em;
  color: var(--ac-text); margin-bottom: 16px; }
${EL} .ac-logo { width: 30px; height: 30px; border-radius: 9px; flex: none;
  box-shadow: 0 2px 8px rgba(12,107,88,0.22); }
${EL} .ac-badge { display: inline-flex; align-items: center; gap: 8px; padding: 6px 14px; border-radius: 999px;
  background: var(--ac-glass-2); color: var(--ac-accent-hover); font-size: 12px; font-weight: 500;
  border: 1px solid var(--ac-glass-border); }
${EL} .ac-h1 { font-size: 26px; font-weight: 700; letter-spacing: -0.01em; margin: 10px 0 8px; }
${EL} .ac-sub { color: var(--ac-secondary); font-size: 14px; margin: 0 0 20px; }

${EL} .ac-cards { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; text-align: left; }
@media (max-width: 640px) { ${EL} .ac-cards { grid-template-columns: 1fr; } }
${EL} .ac-card { display: flex; flex-direction: column; gap: 10px; padding: 20px 18px; border-radius: 12px;
  background: var(--ac-glass-2); border: 1px solid var(--ac-glass-border);
  transition: border-color .2s, transform .2s, background .2s; }
${EL} .ac-card:hover { border-color: var(--ac-glass-border-hi); transform: translateY(-3px); background: #f3f6f2; }
${EL} .ac-icon { width: 40px; height: 40px; border-radius: 12px; display: flex; align-items: center; justify-content: center;
  background: var(--ac-accent-soft); color: var(--ac-accent-hover); }
${EL} .ac-icon.cand { background: rgba(37,99,235,0.10); color: #0369a1; }
${EL} .ac-card h3 { font-size: 16px; margin: 0; }
${EL} .ac-card p { font-size: 12.5px; color: var(--ac-secondary); margin: 0; }
${EL} .ac-links { display: flex; gap: 10px; margin-top: 2px; flex-wrap: wrap; }
${EL} .ac-btn { display: inline-flex; align-items: center; gap: 8px; padding: 9px 16px; border-radius: 12px;
  font-size: 12.5px; font-weight: 600; text-decoration: none; border: 1px solid transparent; cursor: pointer;
  transition: all 0.2s; }
${EL} .ac-btn-primary { background: #0c6b58; color: #fff;
  box-shadow: 0 4px 14px rgba(12,107,88,0.22); }
${EL} .ac-btn-primary:hover { background: #085244; color: #fff;
  box-shadow: 0 6px 18px rgba(12,107,88,0.28); }
${EL} .ac-btn-ghost { background: var(--ac-glass); color: var(--ac-text); border-color: var(--ac-glass-border); }
${EL} .ac-btn-ghost:hover { border-color: var(--ac-glass-border-hi); color: var(--ac-accent-hover); background: var(--ac-glass-2); }
${EL} .ac-foot { margin-top: 18px; text-align: center; font-size: 12.5px; color: var(--ac-muted); }
${EL} .ac-foot a { color: var(--ac-muted); }
${EL} .ac-foot a:hover { color: var(--ac-text); }
`;

export function AccountChoice() {
  return (
    <div className="account-choice">
      <style>{styles}</style>
      <div className="ac-glow" />

      <div className="ac-panel">
        <Link to="/" className="ac-brand"><img className="ac-logo" src="/favicon.svg" alt="" />AURA</Link>

        <div className="text-center">
          <div className="ac-badge"><Sparkles size={13} /> who are you joining as?</div>
          <h1 className="ac-h1">Choose your door</h1>
          <p className="ac-sub">One account flow, two ways in, pick the side you're on.</p>
        </div>

        <div className="ac-cards">
          <div className="ac-card">
            <div className="ac-icon"><Building2 size={22} /></div>
            <h3>I'm hiring</h3>
            <p>
              Run live AI interviews, watch the brain graph grow, and land on
              sourced, confidence-rated verdicts for every candidate.
            </p>
            <div className="ac-links">
              <Link className="ac-btn ac-btn-primary" to="/login">sign in as hiring team <ArrowRight size={14} /></Link>
              <Link className="ac-btn ac-btn-ghost" to="/register">create team account</Link>
            </div>
          </div>

          <div className="ac-card">
            <div className="ac-icon cand"><UserRound size={22} /></div>
            <h3>I'm a candidate</h3>
            <p>
              Practice, take real interviews, and see the evidence trail behind
              your own verdicts, everything scored question by question.
            </p>
            <div className="ac-links">
              <Link className="ac-btn ac-btn-primary" to="/candidate/login">sign in as candidate <ArrowRight size={14} /></Link>
              <Link className="ac-btn ac-btn-ghost" to="/candidate/register">create candidate account</Link>
            </div>
          </div>
        </div>

        <div className="ac-foot">
          not sure yet? <Link to="/opportunity-hub">browse open interviews</Link> · <Link to="/">back to home</Link>
        </div>
      </div>
    </div>
  );
}