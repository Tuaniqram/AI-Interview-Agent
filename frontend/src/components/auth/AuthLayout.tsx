import { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

interface AuthLayoutProps {
  role: 'org' | 'candidate';
  children: ReactNode;
}

/* Paper UI auth shell: quiet drafting-paper background with a bordered white panel. */

const EL = '.auth-shell';

const styles = `
${EL} {
  --al-page: #f6f7f4; --al-text: #17201d; --al-secondary: #3d4a44; --al-muted: #5a6660;
  --al-accent: #0c6b58; --al-accent-hover: #085244; --al-accent-soft: rgba(12,107,88,0.10);
  --al-success: #0c7a54; --al-warning: #b45309; --al-error: #dc2626;
  --al-glass: #ffffff; --al-glass-2: #fbfcfa;
  --al-glass-border: #e2e6e1; --al-glass-border-hi: #c9d1cb;
  --al-blur: none;
  --al-glass-shadow: 0 1px 2px rgba(23,32,29,0.05), 0 8px 24px rgba(23,32,29,0.06);
  min-height: 100vh; background: var(--al-page); color: var(--al-text);
  -webkit-font-smoothing: antialiased;
}
/* Pin app-level tokens to paper values inside the shell, so pages using
   var(--text-primary), bg-input, Button, Input etc. stay readable no matter
   which data-theme the app boots in. */
${EL} {
  --bg-page: #f6f7f4; --bg-section: #ffffff; --bg-elevated: #ffffff; --bg-input: #f0f2ef; --bg-hover: #e8ece8;
  --text-primary: #17201d; --text-secondary: #3d4a44; --text-tertiary: #5a6660; --text-muted: #5a6660; --text-inverse: #ffffff;
  --divider: #eaeeea; --border-color: #e2e6e1; --border-strong: #c9d1cb;
  --action-primary: #0c6b58; --action-primary-hover: #085244; --action-primary-text: #ffffff;
  --action-secondary: #e8ece8; --action-secondary-hover: #dce2dc; --action-secondary-text: #17201d;
  --action-ghost-text: #3d4a44; --action-ghost-hover: #e8ece8;
  --focus-ring: rgba(12,107,88,0.28);
}
body:has(${EL}) { margin: 0; background: var(--al-page); }
html:has(${EL}) { background: var(--al-page); }
${EL} h1, ${EL} h2, ${EL} h3 { font-family: 'Archivo', sans-serif; }
${EL} a { color: var(--al-accent); text-decoration: none; }
${EL} a:hover { color: var(--al-accent-hover); }

/* paper texture grid */
${EL} .al-grid { position: fixed; inset: 0; z-index: 0; pointer-events: none; opacity: 0.30;
  background-image: linear-gradient(to bottom, rgba(23,32,29,0.05) 1px, transparent 1px),
    linear-gradient(to right, rgba(23,32,29,0.05) 1px, transparent 1px);
  background-size: 46px 46px; }

/* content panel */
${EL} .al-panel { background: var(--al-glass); border: 1px solid var(--al-glass-border);
  border-radius: 16px; box-shadow: var(--al-glass-shadow); }
${EL} .al-back { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 600;
  color: var(--al-muted); padding: 4px 10px; border-radius: 999px; margin-bottom: 8px;
  background: var(--al-glass-2); border: 1px solid var(--al-glass-border);
  transition: color .15s, border-color .15s; }
${EL} .al-back:hover { color: var(--al-text); border-color: var(--al-glass-border-hi); }
${EL} .al-back-ic { display: grid; place-items: center; }
${EL} .al-brand { display: flex; align-items: center; gap: 9px; font-family: 'Archivo', sans-serif;
  font-weight: 800; font-size: 17px; letter-spacing: .18em; color: var(--al-text);
  justify-content: center; margin-bottom: 12px; }
${EL} .al-logo { width: 26px; height: 26px; border-radius: 8px; flex: none;
  box-shadow: 0 2px 8px rgba(12,107,88,0.22); }

/* reusable card for inner forms */
${EL} .glass-card { background: var(--al-glass-2); border: 1px solid var(--al-glass-border);
  border-radius: 12px; padding: 18px; }
${EL} .glass-divider { color: var(--al-secondary); }
${EL} .glass-or { background: var(--al-glass-2); }
`;

export function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <div className="auth-shell h-screen">
      <style>{styles}</style>
      <div className="al-grid" />

      <div className="relative z-10 flex items-center justify-center p-3 sm:p-4 h-full overflow-y-auto">
        <div className="w-full max-w-md al-panel px-6 sm:px-7 py-4">
          <Link to="/account" className="al-back"><span className="al-back-ic"><ArrowLeft size={13} /></span>back</Link>
          <Link to="/" className="al-brand"><img className="al-logo" src="/favicon.svg" alt="" />AURA</Link>
          {children}
        </div>
      </div>
    </div>
  );
}