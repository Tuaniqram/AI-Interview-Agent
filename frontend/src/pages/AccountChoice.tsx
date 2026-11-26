import { Link } from 'react-router-dom';
import { Building2, UserRound } from 'lucide-react';

/** The fork before sign-in: hiring teams and candidates have separate accounts. */
const SIDES = [
  {
    icon: Building2,
    title: 'I’m hiring',
    text: 'Run AI interviews for your open roles and get a recommendation for each candidate, with the answers it is based on.',
    signIn: { to: '/login', label: 'Sign in as a hiring team' },
    create: { to: '/register', label: 'Create a team account' },
  },
  {
    icon: UserRound,
    title: 'I’m a candidate',
    text: 'Practise with mock interviews, apply to open roles and take your interviews, with your scores and feedback in one place.',
    signIn: { to: '/candidate/login', label: 'Sign in as a candidate' },
    create: { to: '/candidate/register', label: 'Create a candidate account' },
  },
];

export function AccountChoice() {
  return (
    <div className="min-h-screen bg-page text-primary flex flex-col">
      <header className="px-5 sm:px-10 py-6">
        <Link to="/" className="inline-flex items-center gap-2">
          <img src="/favicon.svg" className="w-7 h-7" alt="" />
          <span className="text-[15px] font-semibold tracking-[-0.01em]">AURA</span>
        </Link>
      </header>

      <main className="flex-1 flex items-center justify-center px-5 pb-16">
        <div className="w-full max-w-3xl">
          <h1 className="text-[28px] leading-9 font-semibold tracking-[-0.02em]">How will you use AURA?</h1>
          <p className="mt-2 text-[15px] text-secondary">Hiring teams and candidates sign in separately.</p>

          <div className="mt-8 grid gap-4 md:grid-cols-2">
            {SIDES.map(({ icon: Icon, title, text, signIn, create }) => (
              <section key={title} className="flex flex-col rounded-xl border border-border bg-section p-6">
                <span className="w-9 h-9 rounded-lg border border-border bg-subtle text-secondary flex items-center justify-center">
                  <Icon className="w-[18px] h-[18px]" />
                </span>
                <h2 className="mt-4 text-base font-semibold">{title}</h2>
                <p className="mt-1.5 text-sm text-secondary leading-relaxed flex-1">{text}</p>
                <div className="mt-6 flex flex-col gap-2">
                  <Link
                    to={signIn.to}
                    className="h-10 rounded-md bg-action-primary text-action-primary-text text-sm font-medium flex items-center justify-center hover:bg-action-primary-hover transition-colors"
                  >
                    {signIn.label}
                  </Link>
                  <Link
                    to={create.to}
                    className="h-10 rounded-md border border-border-strong bg-section text-sm font-medium flex items-center justify-center hover:bg-hover transition-colors"
                  >
                    {create.label}
                  </Link>
                </div>
              </section>
            ))}
          </div>

          <p className="mt-8 text-[13px] text-secondary">
            Just looking? <Link to="/opportunity-hub" className="text-action-primary hover:underline">Browse open interviews</Link>
            {' '}or go <Link to="/" className="text-action-primary hover:underline">back to the home page</Link>.
          </p>
        </div>
      </main>
    </div>
  );
}
