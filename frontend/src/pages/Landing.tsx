import { Link } from 'react-router-dom';
import { Hero } from './landing/Hero';
import { Stats } from './landing/Stats';
import AnimatedFlow from './landing/AnimatedFlow';
import { ProcessFlow } from './landing/ProcessFlow';
import LangGraphFlow from './landing/LangGraphFlow';
import { Features } from './landing/Features';
import { Testimonials } from './landing/Testimonials';
import { UseCases } from './landing/UseCases';
import { FAQ } from './landing/FAQ';
import { CTASection } from './landing/CTASection';

export function Landing() {
  return (
    <div className="min-h-screen bg-[#0a0a0b]">
      {/* Top Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-[#0a0a0b]/80 backdrop-blur-lg border-b border-white/5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
          <Link to="/" className="text-lg font-bold text-[#f2f2f5]">
            AI Interview Agent
          </Link>
          <div className="flex items-center gap-3">
            <Link
              to="/candidate/login"
              className="text-sm text-[#a8a8b3] hover:text-[#f2f2f5] transition-colors"
            >
              Candidate Login
            </Link>
            <Link
              to="/login"
              className="text-sm text-[#a8a8b3] hover:text-[#f2f2f5] transition-colors"
            >
              Sign In
            </Link>
            <Link
              to="/register"
              className="text-sm px-4 py-1.5 rounded-lg bg-[#8b6ff5] text-white font-medium hover:bg-[#a08aff] transition-colors"
            >
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      <Hero />

      <Stats />

      <section id="how-it-works" className="py-24 px-6 bg-[#141416]">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-[#f2f2f5] mb-4">How It Works</h2>
            <p className="text-[#a8a8b3] text-lg max-w-xl mx-auto">
              Your data flows through our intelligent pipeline — from document indexing to final evaluation.
            </p>
          </div>
          <AnimatedFlow />
        </div>
      </section>

      <ProcessFlow />

      <section id="langgraph" className="py-24 px-6 bg-[#0a0a0b]">
        <div className="max-w-5xl mx-auto">
          <LangGraphFlow />
        </div>
      </section>

      <Features />
      <Testimonials />
      <UseCases />
      <FAQ />
      <CTASection />
    </div>
  );
}
