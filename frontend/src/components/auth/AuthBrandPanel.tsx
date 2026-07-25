import { Link } from 'react-router-dom';

interface BrandFeature {
  icon: string;
  text: string;
}

interface AuthBrandPanelProps {
  role: 'org' | 'candidate';
}

const ORG_FEATURES: BrandFeature[] = [
  { icon: 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z', text: 'AI-powered evaluation with real-time scoring' },
  { icon: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z', text: 'Team management and role-based access' },
  { icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z', text: 'Analytics dashboard with detailed reports' },
  { icon: 'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z', text: 'Search and match candidates at scale' },
];

const CANDIDATE_FEATURES: BrandFeature[] = [
  { icon: 'M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z', text: 'Practice with lifelike 3D AI avatars' },
  { icon: 'M13 10V3L4 14h7v7l9-11h-7z', text: 'Real-time feedback on every answer' },
  { icon: 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z', text: 'Adaptive questions that match your skill level' },
  { icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z', text: 'Track your progress with detailed reports' },
];

export function AuthBrandPanel({ role }: AuthBrandPanelProps) {
  const features = role === 'org' ? ORG_FEATURES : CANDIDATE_FEATURES;
  const headline = role === 'org' ? 'For Teams' : 'For Candidates';
  const tagline = role === 'org'
    ? 'Run interviews at scale with AI. Evaluate, collaborate, and hire smarter.'
    : 'Practice interviews with AI. Get real-time feedback and improve faster.';

  return (
    <div className="relative flex flex-col justify-between min-h-screen p-8 lg:p-12">
      <div className="absolute inset-0 bg-gradient-to-br from-[#6366f1] via-[#4f46e5] to-[#7C3AED]" />
      <div className="absolute inset-0 opacity-[0.06]" style={{
        backgroundImage: `linear-gradient(rgba(255,255,255,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.5) 1px, transparent 1px)`,
        backgroundSize: '40px 40px',
      }} />
      <div className="absolute top-1/4 -right-20 w-64 h-64 rounded-full bg-white/10 blur-[100px]" />
      <div className="absolute bottom-1/4 -left-20 w-48 h-48 rounded-full bg-white/5 blur-[80px]" />

      <div className="relative z-10">
        <Link to="/" className="inline-flex items-center gap-2.5">
          <img src="/favicon.svg" className="w-8 h-8" alt="" />
          <span className="text-lg font-bold text-white">AI Interview Agent</span>
        </Link>
      </div>

      <div className="relative z-10 space-y-8">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 text-white/80 text-xs font-medium mb-4">
            <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
            {headline}
          </div>
          <h2 className="text-3xl lg:text-4xl font-bold text-white leading-tight">
            {role === 'org' ? 'Hiring' : 'Practice'}
            <br />
            <span className="text-white/70">reimagined with AI</span>
          </h2>
          <p className="mt-4 text-sm text-white/70 max-w-sm leading-relaxed">
            {tagline}
          </p>
        </div>

        <div className="space-y-4">
          {features.map((f, i) => (
            <div key={i} className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-white/10 flex items-center justify-center shrink-0 mt-0.5">
                <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d={f.icon} />
                </svg>
              </div>
              <span className="text-sm text-white/80">{f.text}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="relative z-10 text-xs text-white/40">
        &copy; {new Date().getFullYear()} AI Interview Agent
      </div>
    </div>
  );
}
