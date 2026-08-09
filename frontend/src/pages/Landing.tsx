import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Layers, Play, Brain, GitBranch, ShieldCheck, ListChecks, Sparkles, Workflow } from 'lucide-react';
import BrainGraph from '../components/graph/BrainGraph';

/* ════════════════════════════════════════════════════════════════════════
   Landing — new page: AURA evidence-first interviews + the live Brain Graph
   The Brain Graph is a React component (components/graph/BrainGraph.tsx) —
   a three-box demo card: big graph, info side panel, replay play bar.
   Scoped styles: every selector is prefixed with .engine-landing.
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
  background-image: linear-gradient(to bottom, rgba(255,255,255,0.025) 1px, transparent 1px),
    linear-gradient(to right, rgba(255,255,255,0.025) 1px, transparent 1px);
  background-size: 46px 46px; }
${EL} .el-wrap { position: relative; z-index: 1; max-width: 1180px; margin: 0 auto; padding: 0 24px; }

/* nav */
${EL} .el-nav { display: flex; align-items: center; justify-content: space-between; padding: 18px 24px; }
${EL} .el-brand { font-family: 'Poppins', sans-serif; font-weight: 800; font-size: 22px; letter-spacing: .18em;
  background: linear-gradient(90deg, #c4b5fd, #7dd3fc); -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent; }
${EL} .el-nav-links { display: flex; gap: 26px; font-size: 13px; color: var(--el-muted); }
${EL} .el-nav-links a { color: var(--el-muted); }
${EL} .el-nav-links a:hover { color: var(--el-text); }
${EL} .el-nav-cta { display: flex; gap: 10px; }
${EL} .el-rail { position: fixed; right: 14px; top: 50%; transform: translateY(-50%); z-index: 40;
  display: flex; flex-direction: column; gap: 4px; background: rgba(20,20,22,.7);
  border: 1px solid var(--el-border); border-radius: 12px; padding: 6px; backdrop-filter: blur(12px); }
${EL} .el-rail-item { display: flex; align-items: center; gap: 10px; padding: 7px 9px; border-radius: 9px;
  border: none; background: transparent; cursor: pointer; color: var(--el-muted); font-family: inherit; }
${EL} .el-rail-icon { display: grid; place-items: center; width: 20px; height: 20px; flex: none; }
${EL} .el-rail-label { font-family: 'Poppins', sans-serif; font-size: 11.5px; font-weight: 600;
  opacity: 0; max-width: 0; white-space: nowrap; overflow: hidden; transition: opacity .2s, max-width .2s; }
${EL} .el-rail-item:hover { background: var(--el-hover); color: var(--el-text); }
${EL} .el-rail-item:hover .el-rail-label, ${EL} .el-rail-item.active .el-rail-label { opacity: 1; max-width: 140px; }
${EL} .el-rail-item.active { color: #fff; background: linear-gradient(135deg, var(--el-accent), #a78bfa); }
@media (max-width: 860px){ ${EL} .el-rail { display: none; } }
${EL} .el-btn { display: inline-flex; align-items: center; gap: 8px; padding: 10px 18px; border-radius: 10px;
  font-size: 13px; font-weight: 600; text-decoration: none; border: 1px solid transparent; cursor: pointer;
  transition: all 0.2s; }
${EL} .el-btn-primary { background: var(--el-accent); color: #fff; }
${EL} .el-btn-primary:hover { background: var(--el-accent-hover); color: #fff; }
${EL} .el-btn-ghost { background: transparent; color: var(--el-text); border-color: var(--el-border); }
${EL} .el-btn-ghost:hover { border-color: var(--el-accent); color: var(--el-accent); }

/* hero */
${EL} .el-hero { padding: 40px 0 64px; text-align: center; }
${EL} .el-badge { display: inline-flex; align-items: center; gap: 8px; padding: 5px 12px; border-radius: 999px;
  background: var(--el-accent-soft); color: var(--el-accent); font-size: 12px; font-weight: 500;
  border: 1px solid rgba(139,111,245,0.25); margin-bottom: 20px; }
${EL} .el-hero-copy { max-width: 780px; margin: 0 auto 44px; }
${EL} .el-hero-copy h1 { font-size: 44px; line-height: 1.12; letter-spacing: -0.02em; margin-bottom: 18px;
  background: linear-gradient(90deg, #f2f2f5 30%, #b9a7ff 100%); -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent; }
${EL} .el-hero-copy p { color: var(--el-secondary); font-size: 16px; max-width: 560px; margin: 0 auto 26px; }
${EL} .el-hero-btns { display: flex; gap: 12px; flex-wrap: wrap; justify-content: center; }
${EL} .el-hero-stats { display: flex; gap: 32px; margin-top: 42px; flex-wrap: wrap; justify-content: center; }
${EL} .el-num { font-size: 26px; font-weight: 700; }
${EL} .el-stat-label { font-size: 11px; color: var(--el-muted); text-transform: uppercase; letter-spacing: .08em; }

/* graph stage — three-box demo card */
${EL} .el-stage { position: relative; max-width: 1080px; margin: 0 auto; }
${EL} .el-stage-cap { margin-top: 14px; text-align: center; color: var(--el-muted); font-size: 12px; }
${EL} .el-stage-cap b { color: var(--el-secondary); font-weight: 600; }

/* sections */
${EL} .el-sec { padding: 56px 0; }
${EL} .el-kicker { font-size: 11px; text-transform: uppercase; letter-spacing: .16em; color: var(--el-accent);
  font-weight: 700; margin-bottom: 10px; }
${EL} .el-h2 { font-size: 29px; font-weight: 700; letter-spacing: -0.01em; margin-bottom: 12px; }
${EL} .el-sub { color: var(--el-secondary); max-width: 660px; margin-bottom: 34px; font-size: 15px; }

/* cards */
${EL} .el-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; }
${EL} .el-card { background: var(--el-section); border: 1px solid var(--el-border); border-radius: var(--el-radius);
  padding: 24px; transition: border-color .2s, transform .2s; }
${EL} .el-card:hover { border-color: var(--el-accent); transform: translateY(-2px); }
${EL} .el-ic { width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center;
  background: var(--el-accent-soft); color: var(--el-accent); margin-bottom: 14px; }
${EL} .el-ic svg { width: 20px; height: 20px; }
${EL} .el-card h3 { font-size: 15px; margin-bottom: 7px; }
${EL} .el-card p { font-size: 13px; color: var(--el-secondary); }

/* pipeline strip */
${EL} .el-pipe { display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; margin-bottom: 34px; }
${EL} .el-pipe-step { background: var(--el-section); border: 1px solid var(--el-border); border-radius: 12px;
  padding: 16px 18px; position: relative; }
${EL} .el-pipe-step::after { content: '→'; position: absolute; right: -12px; top: 50%; transform: translateY(-50%);
  color: var(--el-muted); font-size: 14px; z-index: 2; }
${EL} .el-pipe-step:last-child::after { content: ''; }
${EL} .el-pipe-n { font-size: 10px; font-weight: 800; color: var(--el-accent); letter-spacing: .14em; margin-bottom: 6px; }
${EL} .el-pipe-step h3 { font-size: 13.5px; margin-bottom: 4px; }
${EL} .el-pipe-step p { font-size: 11.5px; color: var(--el-muted); }

/* legend */
${EL} .el-legend { display: flex; gap: 16px; flex-wrap: wrap; align-items: center;
  background: var(--el-section); border: 1px solid var(--el-border); border-radius: 12px; padding: 12px 18px;
  font-size: 12px; color: var(--el-secondary); margin-bottom: 14px; }
${EL} .el-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; vertical-align: -1px; }
${EL} .el-line { display: inline-block; width: 22px; height: 2px; margin-right: 6px; vertical-align: 3px; }

/* cta */
${EL} .el-cta { text-align: center; padding: 64px 24px; }
${EL} .el-cta .el-h2 { font-size: 32px; }
${EL} .el-cta .el-sub { margin: 0 auto 28px; }

/* footer */
${EL} .el-foot { border-top: 1px solid var(--el-border); padding: 24px 24px 40px; display: flex;
  justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; color: var(--el-muted); font-size: 12.5px; }
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
  const [activeSection, setActiveSection] = useState('graph');

  useEffect(() => {
    document.body.classList.add('engine-landing');
    const onScroll = () => {
      let current = 'graph';
      for (const id of ['graph', 'why', 'pipeline', 'cta']) {
        const el = document.getElementById(id);
        if (el && el.getBoundingClientRect().top < window.innerHeight * 0.4) current = id;
      }
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
    ['graph', 'graph', <Brain key="graph" size={17} strokeWidth={2.2} />],
    ['why', 'why', <Sparkles key="why" size={17} strokeWidth={2.2} />],
    ['pipeline', 'pipeline', <Workflow key="pipe" size={17} strokeWidth={2.2} />],
    ['cta', 'start', <Play key="cta" size={17} strokeWidth={2.2} />],
  ];

  return (
    <div className="engine-landing">
      <style>{styles}</style>
      <div className="el-glow" />
      <div className="el-grid" />

      <nav className="el-rail" aria-label="Page sections">
        {RAIL.map(([id, label, icon]) => (
          <button key={id} className={`el-rail-item ${activeSection === id ? 'active' : ''}`} onClick={() => scrollTo(id)}>
            <span className="el-rail-icon">{icon}</span>
            <span className="el-rail-label">{label}</span>
          </button>
        ))}
      </nav>

      <div className="el-wrap">
        <nav className="el-nav">
          <div className="el-brand">AURA</div>
          <div className="el-nav-links">
            <a href="#graph">brain graph</a>
            <a href="#why">evidence-first</a>
            <a href="#pipeline">pipeline</a>
            <Link to="/brain-graph">13 layers</Link>
            <Link to="/candidate/login">candidate</Link>
          </div>
          <div className="el-nav-cta">
            <Link className="el-btn el-btn-ghost" to="/login">sign in</Link>
            <Link className="el-btn el-btn-primary" to="/register">get started</Link>
          </div>
        </nav>

        <section className="el-hero">
          <div className="el-hero-copy">
            <div className="el-badge"><Sparkles size={13} /> interviews that leave a brain behind</div>
            <h1>Watch every hire decision think itself through.</h1>
            <p>
              AURA interviews in real time and reasons over evidence — building a live
              brain graph of questions, hypotheses, competencies, and proof. No black box:
              every verdict ships with its entire reasoning trail.
            </p>
            <div className="el-hero-btns">
              <Link className="el-btn el-btn-primary" to="/register">run an interview</Link>
              <Link className="el-btn el-btn-ghost" to="/brain-graph">explore the 13 layers →</Link>
            </div>
            <div className="el-hero-stats">
              <div><div className="el-num">100%</div><div className="el-stat-label">evidence-backed verdicts</div></div>
              <div><div className="el-num">13</div><div className="el-stat-label">brain layers</div></div>
              <div><div className="el-num">∞</div><div className="el-stat-label">replayable timeline</div></div>
            </div>
          </div>

          <div className="el-stage" id="graph">
            <BrainGraph />
            <div className="el-stage-cap">
              <b>live demo — the engine's own brain graph.</b> drag nodes · play the timeline · click a layer to see what fed the verdict ·{" "}
              <Link to="/brain-graph" style={{ textDecoration: "underline" }}>open full view →</Link>
            </div>
          </div>
        </section>
      </div>

      <div className="el-wrap">
        <section className="el-sec" id="why">
          <div className="el-kicker">why evidence-first</div>
          <h2 className="el-h2">Reasoning you can audit, not vibes you have to trust.</h2>
          <p className="el-sub">
            Every interview becomes a graph of claims and proof. Supporting evidence is green,
            contradicting evidence is red — and the final decision is only as strong as the
            chain that holds it up.
          </p>
          <div className="el-cards">
            <div className="el-card">
              <div className="el-ic"><Brain /></div>
              <h3>Live brain graph</h3>
              <p>The interview's reasoning materializes as it happens — questions, hypotheses,
                and evidence arranged by confidence around a decision core.</p>
            </div>
            <div className="el-card">
              <div className="el-ic"><GitBranch /></div>
              <h3>Confidence-aware layout</h3>
              <p>Strong hypotheses anchor near the core; refuted ones fade to the edge. Read
                the state of the interview at a glance.</p>
            </div>
            <div className="el-card">
              <div className="el-ic"><ListChecks /></div>
              <h3>Timeline replay</h3>
              <p>Scrub question by question and watch evidence light up — exactly how the
                engine reached its verdict, turn by turn.</p>
            </div>
            <div className="el-card">
              <div className="el-ic"><ShieldCheck /></div>
              <h3>Provenance on every claim</h3>
              <p>Supporting and contradicting edges trace every score to the statement that
                produced it. Nothing is asserted without a source.</p>
            </div>
            <div className="el-card">
              <div className="el-ic"><Layers /></div>
              <h3>Layer-by-layer focus</h3>
              <p>Isolate competencies, hypotheses, evidence, or questions — or drill into any
                single node for its full detail.</p>
            </div>
            <div className="el-card">
              <div className="el-ic"><Workflow /></div>
              <h3>Self-correcting engine</h3>
              <p>New evidence keeps testing open hypotheses. The graph doesn't commit early —
                it waits until the proof settles.</p>
            </div>
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
            <span><span className="el-dot" style={{ background: '#fbbf24' }} />hypotheses</span>
            <span><span className="el-dot" style={{ background: '#34d399' }} />evidence</span>
            <span><span className="el-dot" style={{ background: '#94a3b8' }} />questions</span>
            <span><span className="el-line" style={{ background: '#34d399' }} />supporting</span>
            <span><span className="el-line" style={{ background: '#fb7185' }} />contradicting</span>
          </div>
        </section>
      </div>

      <div className="el-wrap">
        <section className="el-cta" id="cta">
          <div className="el-kicker">get started</div>
          <h2 className="el-h2">Run an interview. Watch the brain grow.</h2>
          <p className="el-sub">Create a free account — the first interview builds its own graph for you.</p>
          <Link className="el-btn el-btn-primary" to="/register">
            <Play size={15} /> get started free
          </Link>
        </section>
      </div>

      <footer className="el-foot el-wrap">
        <div>© {new Date().getFullYear()} AURA — AI Interview Agent</div>
        <div style={{ display: 'flex', gap: 18 }}>
          <Link to="/login">sign in</Link>
          <Link to="/candidate/login">candidate login</Link>
          <Link to="/candidate/register">candidate register</Link>
        </div>
      </footer>
    </div>
  );
}
