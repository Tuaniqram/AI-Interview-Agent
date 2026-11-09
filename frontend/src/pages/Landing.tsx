import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Moon, Sun } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';
import { EvidenceTranscript } from '../components/landing/EvidenceTranscript';
import { CandidateScreenPreview } from '../components/landing/CandidateScreenPreview';
import { ScorecardPreview } from '../components/landing/ScorecardPreview';
import { FairnessSection } from '../components/landing/FairnessSection';
import { ProofSection } from '../components/landing/ProofSection';
import { sampleExcerpts } from '../components/landing/sampleInterview';

/**
 * Marketing landing page. Calm and plain on purpose: thin borders instead of shadows, one accent (the amber
 * evidence highlight) beside the green primary, and real product components in place of illustrations.
 * It uses the app's colour tokens, so light and dark themes both work.
 */

const NAV_LINKS: Array<[string, string]> = [
  ['#how', 'How it works'],
  ['#candidates', 'For candidates'],
  ['#fairness', 'Fairness'],
  ['#proof', 'Proof'],
];

const PRIMARY_BUTTON =
  'inline-flex items-center justify-center gap-2 rounded-ui-md bg-action-primary px-4 py-2.5 text-sm font-semibold text-action-primary-text transition-colors hover:bg-action-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]';
const SECONDARY_BUTTON =
  'inline-flex items-center justify-center gap-2 rounded-ui-md border border-border-strong px-4 py-2.5 text-sm font-semibold text-primary transition-colors hover:bg-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]';

function Step({ number, title, children, preview, reverse = false }: {
  number: string;
  title: string;
  children: ReactNode;
  preview: ReactNode;
  reverse?: boolean;
}) {
  return (
    <div className="grid items-start gap-6 border-t border-border py-10 md:grid-cols-12 md:gap-10">
      <div className={`md:col-span-4 ${reverse ? 'md:order-2' : ''}`}>
        <p className="font-mono text-xs text-muted">{number}</p>
        <h3 className="mt-2 text-xl font-bold text-primary">{title}</h3>
        <p className="mt-2 text-sm leading-relaxed text-secondary">{children}</p>
      </div>
      <div className={`md:col-span-8 ${reverse ? 'md:order-1' : ''}`}>{preview}</div>
    </div>
  );
}

export function Landing() {
  const { isDark, toggle } = useTheme();
  const excerpts = sampleExcerpts();

  return (
    <div className="min-h-screen bg-page text-primary">
      <header className="sticky top-0 z-30 border-b border-border bg-page">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
          <a href="#top" className="flex items-center gap-2 font-display text-lg text-primary">
            <img src="/favicon.svg" alt="" className="h-6 w-6" />
            AURA
          </a>
          <nav className="hidden items-center gap-6 md:flex" aria-label="Sections">
            {NAV_LINKS.map(([href, label]) => (
              <a key={href} href={href} className="text-sm text-secondary hover:text-primary">{label}</a>
            ))}
          </nav>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={toggle}
              aria-label={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
              className="rounded-ui-md p-2 text-secondary hover:bg-hover hover:text-primary"
            >
              {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </button>
            <Link to="/login" className="hidden text-sm text-secondary hover:text-primary sm:inline">Sign in</Link>
            <Link to="/account" className={PRIMARY_BUTTON}>Run an interview</Link>
          </div>
        </div>
      </header>

      <main id="top">
        {/* Hero: asymmetric, with the evidence beside the claim. */}
        <section className="mx-auto grid max-w-6xl gap-10 px-4 pb-16 pt-12 sm:px-6 md:pt-20 lg:grid-cols-12 lg:gap-12 lg:pb-24">
          <div className="lg:col-span-6">
            <p className="font-mono text-xs uppercase tracking-wide text-muted">Structured first-round interviews</p>
            <h1 className="font-display mt-4 text-4xl leading-[1.05] text-primary sm:text-5xl lg:text-[3.4rem]">
              First-round interviews, done overnight. Every score explained.
            </h1>
            <p className="mt-6 max-w-xl text-base leading-relaxed text-secondary">
              AURA interviews each candidate, scores every answer against a fixed rubric, and shows the exact words
              each score rests on. You get a recommendation with its reasons, and the hiring decision stays with you.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to="/account" className={PRIMARY_BUTTON}>
                Run an interview <ArrowRight className="h-4 w-4" />
              </Link>
              <a href="#how" className={SECONDARY_BUTTON}>See how it works</a>
            </div>
          </div>
          <div className="lg:col-span-6 lg:mt-10">
            <EvidenceTranscript excerpt={excerpts[0]} />
          </div>
        </section>

        {/* How it works: three steps, each shown with the product itself. */}
        <section id="how" className="border-t border-border">
          <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 md:py-24">
            <p className="font-mono text-xs uppercase tracking-wide text-muted">How it works</p>
            <h2 className="font-display mt-3 max-w-3xl text-3xl text-primary md:text-4xl">
              From a conversation to a recommendation you can check.
            </h2>

            <div className="mt-10">
              <Step
                number="01"
                title="The candidate answers, one question at a time"
                preview={<CandidateScreenPreview compact />}
              >
                Questions follow the role’s competencies and adapt to what the candidate says. Candidates type or speak,
                and can ask for a question to be repeated.
              </Step>
              <Step
                number="02"
                title="Every answer is scored against evidence"
                reverse
                preview={<EvidenceTranscript excerpt={excerpts[2]} />}
              >
                Each answer is scored on the competency it tests. The words that carry the score are highlighted, with
                what went well and what was missing beside them.
              </Step>
              <Step
                number="03"
                title="You get a recommendation, with its reasons"
                preview={<ScorecardPreview />}
              >
                The report opens with the recommendation, how confident it is, and, when a rule lowered it, which rule
                and why. Below it: results per competency and the full transcript.
              </Step>
            </div>
          </div>
        </section>

        {/* Candidate experience. */}
        <section id="candidates" className="border-t border-border">
          <div className="mx-auto grid max-w-6xl gap-10 px-4 py-16 sm:px-6 md:py-24 lg:grid-cols-12 lg:gap-12">
            <div className="lg:col-span-5">
              <p className="font-mono text-xs uppercase tracking-wide text-muted">For candidates</p>
              <h2 className="font-display mt-3 text-3xl text-primary md:text-4xl">
                A calm interview, with the rules stated first.
              </h2>
              <ul className="mt-6 space-y-3 text-sm leading-relaxed text-secondary">
                <li>You read the conduct rules before the interview starts.</li>
                <li>Type your answers or speak them.</li>
                <li>If a question is unclear, ask. A request to repeat or explain it is not scored.</li>
                <li>Create an account to keep your applications and interview history in one place.</li>
              </ul>
              <div className="mt-8 flex flex-wrap gap-3">
                <Link to="/opportunity-hub" className={SECONDARY_BUTTON}>Browse open roles</Link>
                <Link to="/candidate/login" className="inline-flex items-center px-1 py-2.5 text-sm font-semibold text-action-primary hover:underline">
                  Candidate sign in
                </Link>
              </div>
            </div>
            <div className="lg:col-span-7">
              <CandidateScreenPreview index={0} />
            </div>
          </div>
        </section>

        <FairnessSection />
        <ProofSection />

        {/* Closing call to action. */}
        <section className="border-t border-border">
          <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 md:py-24">
            <h2 className="font-display max-w-3xl text-3xl text-primary md:text-4xl">
              See a recommendation you can check.
            </h2>
            <p className="mt-4 max-w-xl text-base text-secondary">
              Set up a role, invite a candidate and read the report. Every score links back to the answer behind it.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to="/account" className={PRIMARY_BUTTON}>Run an interview <ArrowRight className="h-4 w-4" /></Link>
              <Link to="/contact" className={SECONDARY_BUTTON}>Talk to us</Link>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-border">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-8 text-xs text-muted sm:px-6">
          <span className="font-mono">AURA · {new Date().getFullYear()}</span>
          <nav className="flex flex-wrap gap-x-6 gap-y-2" aria-label="Footer">
            <Link to="/opportunity-hub" className="hover:text-primary">Open roles</Link>
            <Link to="/candidate/login" className="hover:text-primary">Candidate sign in</Link>
            <Link to="/login" className="hover:text-primary">Recruiter sign in</Link>
            <Link to="/contact" className="hover:text-primary">Contact</Link>
          </nav>
        </div>
      </footer>
    </div>
  );
}
