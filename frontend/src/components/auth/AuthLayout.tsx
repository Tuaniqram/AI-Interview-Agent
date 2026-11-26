import { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

interface AuthLayoutProps {
  role: 'org' | 'candidate';
  children: ReactNode;
}

/*
 * Sign-in shell: the form on the left, and on wide screens a panel showing what the product actually does —
 * an answer with the words its score rests on highlighted. The excerpt is a written sample and says so.
 */

/** Pages written for the old boxed shell wrap their form in `.glass-card`; here the form sits on the page. */
const styles = `
.auth-shell .glass-card { background: transparent; border: 0; padding: 0; border-radius: 0; }
.auth-shell .glass-or { background: var(--bg-section); }
.auth-shell .glass-divider { color: var(--text-secondary); }
.auth-shell a { color: var(--action-primary); }
.auth-shell a:hover { color: var(--action-primary-hover); }
`;

const COPY = {
  org: {
    title: 'Every score shows the words it rests on.',
    text: 'AURA interviews each applicant, scores every answer against your rubric, and marks the phrases each score is based on, so you can check a recommendation instead of trusting it.',
  },
  candidate: {
    title: 'Interview when it suits you, and see how you did.',
    text: 'Practice as often as you like. In a real interview you answer at your own pace, and the feedback points to the parts of your answers that counted.',
  },
};

function SampleAnswer() {
  return (
    <figure className="rounded-xl border border-border bg-section p-5 shadow-sm">
      <figcaption className="flex items-center justify-between text-xs text-tertiary mb-3">
        <span>Sample answer · Caching</span>
        <span className="h-5 px-1.5 rounded-md bg-success-bg text-success-text font-medium flex items-center tabular">7.8</span>
      </figcaption>
      <p className="text-sm font-medium text-primary leading-relaxed">How do you keep a cache consistent when the database changes?</p>
      <blockquote className="mt-3 text-[13px] text-secondary leading-relaxed">
        I invalidate the key on every write, then{' '}
        <mark className="evidence-mark">keep a 30 second TTL as a safety net</mark>. After the change{' '}
        <mark className="evidence-mark">the hit rate went from 78 to 96 percent</mark>, and stale reads stopped.
      </blockquote>
      <p className="mt-4 pt-3 border-t border-border text-xs text-tertiary">
        <mark className="evidence-mark">Highlighted words</mark> are what the score is based on.
      </p>
    </figure>
  );
}

export function AuthLayout({ role, children }: AuthLayoutProps) {
  const copy = COPY[role];
  return (
    <div className="auth-shell min-h-screen bg-section text-primary flex">
      <style>{styles}</style>

      <div className="flex-1 min-w-0 flex flex-col px-5 sm:px-10 py-6">
        <div className="flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 !text-primary">
            <img src="/favicon.svg" className="w-7 h-7" alt="" />
            <span className="text-[15px] font-semibold tracking-[-0.01em]">AURA</span>
          </Link>
          <Link to="/account" className="inline-flex items-center gap-1.5 text-[13px] !text-secondary hover:!text-primary">
            <ArrowLeft className="w-3.5 h-3.5" /> Back
          </Link>
        </div>

        <main className="flex-1 flex items-center justify-center py-10">
          <div className="w-full max-w-[380px]">{children}</div>
        </main>

      </div>

      <aside className="hidden lg:flex w-[46%] max-w-[640px] shrink-0 bg-page border-l border-border flex-col justify-center px-14 xl:px-20">
        <div className="max-w-[440px]">
          <h2 className="[text-wrap:balance] text-[26px] leading-[1.25] font-semibold tracking-[-0.02em] text-primary">{copy.title}</h2>
          <p className="mt-3 [text-wrap:pretty] text-[15px] leading-relaxed text-secondary">{copy.text}</p>
          <div className="mt-10"><SampleAnswer /></div>
        </div>
      </aside>
    </div>
  );
}
