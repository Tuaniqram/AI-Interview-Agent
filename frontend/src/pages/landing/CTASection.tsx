import { ArrowRight } from 'lucide-react';

export function CTASection() {
  return (
    <section className="py-24 px-6 bg-[#0a0a0b] relative overflow-hidden">
      <div className="absolute inset-0 opacity-[0.02]"
        style={{
          backgroundImage: `radial-gradient(circle at 25% 50%, rgba(139,111,245,0.8) 0%, transparent 50%), radial-gradient(circle at 75% 50%, rgba(139,111,245,0.5) 0%, transparent 50%)`,
        }}
      />

      <div className="relative z-10 max-w-3xl mx-auto text-center">
        <h2 className="text-3xl md:text-4xl font-bold text-[#f2f2f5] mb-4">
          Ready to transform your hiring?
        </h2>
        <p className="text-[#a8a8b3] text-lg mb-10 max-w-lg mx-auto">
          Start conducting intelligent, AI-powered interviews in minutes. No setup required.
        </p>
        <a
          href="/new-interview"
          className="inline-flex items-center gap-2 px-8 py-3.5 text-sm font-semibold text-[#1a1a1e] bg-[#8b6ff5] rounded-xl hover:bg-[#a08aff] active:scale-[0.98] transition-all shadow-lg shadow-action-primary/25"
        >
          Start Your First Interview
          <ArrowRight className="w-4 h-4" />
        </a>
      </div>

      <footer className="relative z-10 mt-24 pt-8 border-t border-[#2c2c30] max-w-5xl mx-auto flex items-center justify-between">
        <span className="text-xs text-[#8a8a94]">AI Interview Agent</span>
        <span className="text-xs text-[#6f6f7a]">Built with React + FastAPI + LangGraph</span>
      </footer>
    </section>
  );
}
