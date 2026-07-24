import { ArrowRight, Play, CheckCircle, Star } from 'lucide-react';

export function Hero() {
  const scrollToFlow = () => {
    document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <section className="relative min-h-[90vh] flex items-center justify-center overflow-hidden bg-page">
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: `linear-gradient(rgba(139,111,245,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(139,111,245,0.5) 1px, transparent 1px)`,
          backgroundSize: '60px 60px',
        }}
      />

      <div className="absolute top-1/4 -left-32 w-96 h-96 rounded-full bg-action-primary/10 blur-[120px]" />
      <div className="absolute bottom-1/4 -right-32 w-96 h-96 rounded-full bg-action-primary/5 blur-[120px]" />

      <div className="relative z-10 text-center px-6 py-6 max-w-4xl mx-auto">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-action-primary/10 text-action-primary text-xs font-medium mb-8">
          <span className="w-1.5 h-1.5 rounded-full bg-action-primary animate-pulse" />
          AI-Powered Interview Platform
        </div>

        <h1 className="text-5xl md:text-7xl font-bold text-primary leading-tight mb-6 tracking-tight">
          AI Interview
          <br />
          <span className="bg-gradient-to-r from-[#8b6ff5] to-[#a08aff] bg-clip-text text-transparent">
            Agent
          </span>
        </h1>

        <p className="text-lg md:text-xl text-secondary max-w-2xl mx-auto mb-6 leading-relaxed">
          Practice interviews with AI. Or run them at scale for your company.
          <br />
          Real-time evaluation. Adaptive questions. Lifelike 3D avatars.
        </p>

        <div className="flex flex-wrap items-center justify-center gap-3 mb-10">
          {['RAG-powered context', 'Instant scoring', 'Avatar mode', 'Voice support'].map(item => (
            <span key={item} className="inline-flex items-center gap-1.5 text-xs text-secondary bg-elevated px-3 py-1 rounded-full">
              <CheckCircle className="w-3 h-3 text-[#34d399]" />
              {item}
            </span>
          ))}
        </div>

        <div className="flex items-center justify-center gap-4">
          <a
            href="/candidate/register"
            className="inline-flex items-center gap-2 px-6 py-3 text-sm font-semibold text-inverse bg-action-primary rounded-xl hover:bg-action-primary-hover active:scale-[0.98] transition-all shadow-lg shadow-action-primary/25"
          >
            Practice Interview
            <ArrowRight className="w-4 h-4" />
          </a>
          <a
            href="/register"
            className="inline-flex items-center gap-2 px-6 py-3 text-sm font-medium text-secondary bg-elevated rounded-xl hover:bg-elevated hover:text-primary active:scale-[0.98] transition-all"
          >
            For Companies
          </a>
          <button
            onClick={scrollToFlow}
            className="inline-flex items-center gap-2 px-6 py-3 text-sm font-medium text-secondary hover:text-primary active:scale-[0.98] transition-all"
          >
            <Play className="w-4 h-4" />
            See How It Works
          </button>
        </div>

        {/* Stats bar */}
        <div className="mt-12 grid grid-cols-3 gap-8 max-w-lg mx-auto">
          <div>
            <div className="text-2xl font-bold text-primary">10K+</div>
            <div className="text-xs text-muted mt-0.5">Interviews Conducted</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-primary">50+</div>
            <div className="text-xs text-muted mt-0.5">Companies Using</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-primary">4.8 <Star size={20} className="inline text-warning align-text-top" /></div>
            <div className="text-xs text-muted mt-0.5">Avg. Rating</div>
          </div>
        </div>

        {/* Floating dashboard mockup */}
        <div className="mt-12 relative max-w-3xl mx-auto">
          <div className="bg-section rounded-2xl shadow-[0_40px_80px_-20px_rgba(0,0,0,0.8)] overflow-hidden">
            <div className="flex items-center gap-1.5 px-4 py-3">
              <div className="w-2.5 h-2.5 rounded-full bg-[#f87171]" />
              <div className="w-2.5 h-2.5 rounded-full bg-[#fbbf24]" />
              <div className="w-2.5 h-2.5 rounded-full bg-[#34d399]" />
              <span className="ml-3 text-xs text-muted font-mono">AI Interview Agent — Dashboard</span>
            </div>
            <div className="p-5 grid grid-cols-2 gap-4">
              <div className="space-y-3">
                <div className="h-3 w-24 bg-[#2f2f33] rounded" />
                <div className="h-8 bg-[#2f2f33] rounded-lg" />
                <div className="h-8 bg-[#252528] rounded-lg" />
                <div className="h-8 bg-[#252528] rounded-lg" />
              </div>
              <div className="space-y-3">
                <div className="h-3 w-20 bg-[#2f2f33] rounded" />
                <div className="h-20 bg-[#252528] rounded-lg flex items-end gap-2 p-3">
                  <div className="w-6 bg-[#8b6ff5] rounded-t" style={{ height: '60%' }} />
                  <div className="w-6 bg-[#8b6ff5]/70 rounded-t" style={{ height: '40%' }} />
                  <div className="w-6 bg-[#8b6ff5]/50 rounded-t" style={{ height: '80%' }} />
                  <div className="w-6 bg-[#8b6ff5]/30 rounded-t" style={{ height: '30%' }} />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
