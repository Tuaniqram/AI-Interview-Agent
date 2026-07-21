import { ArrowRight, CheckCircle } from 'lucide-react';

const benefits = [
  'No credit card required',
  'Set up in under 5 minutes',
  'Free tier includes 10 interviews',
  'All features unlocked',
];

export function CTASection() {
  return (
    <section className="py-24 px-6 bg-[#0a0a0b] relative overflow-hidden">
      <div className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: `radial-gradient(circle at 25% 50%, rgba(139,111,245,0.8) 0%, transparent 50%), radial-gradient(circle at 75% 50%, rgba(139,111,245,0.5) 0%, transparent 50%)`,
        }}
      />

      <div className="relative z-10 max-w-3xl mx-auto text-center">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-action-primary/10 text-action-primary text-xs font-medium mb-6">
          Get started today
        </div>

        <h2 className="text-3xl md:text-4xl font-bold text-[#f2f2f5] mb-4">
          Ready to transform your hiring?
        </h2>
        <p className="text-[#a8a8b3] text-lg mb-8 max-w-lg mx-auto">
          Stop wasting hours on initial screenings. Let AI handle the first round while you focus on the best candidates.
        </p>

        <div className="flex flex-wrap items-center justify-center gap-4 mb-10">
          {benefits.map(b => (
            <span key={b} className="inline-flex items-center gap-1.5 text-sm text-[#a8a8b3]">
              <CheckCircle className="w-4 h-4 text-[#34d399]" />
              {b}
            </span>
          ))}
        </div>

        <a
          href="/new-interview"
          className="inline-flex items-center gap-2 px-8 py-3.5 text-sm font-semibold text-[#1a1a1e] bg-[#8b6ff5] rounded-xl hover:bg-[#a08aff] active:scale-[0.98] transition-all shadow-lg shadow-action-primary/25"
        >
          Start Your First Interview
          <ArrowRight className="w-4 h-4" />
        </a>
      </div>

      <footer className="relative z-10 mt-24 pt-8 max-w-5xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        <span className="text-xs text-[#8a8a94]">AI Interview Agent</span>
        <div className="flex items-center gap-6">
          <span className="text-xs text-[#6f6f7a]">Built with React + FastAPI + LangGraph</span>
          <span className="text-xs text-[#6f6f7a]">Groq LLM · Pinecone · SQLAlchemy</span>
        </div>
      </footer>
    </section>
  );
}
