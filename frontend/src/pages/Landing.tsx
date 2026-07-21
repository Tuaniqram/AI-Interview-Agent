import { Hero } from './landing/Hero';
import { Stats } from './landing/Stats';
import AnimatedFlow from './landing/AnimatedFlow';
import { Features } from './landing/Features';
import { UseCases } from './landing/UseCases';
import { CTASection } from './landing/CTASection';

export function Landing() {
  return (
    <div className="min-h-screen bg-[#0a0a0b]">
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

      <Features />
      <UseCases />
      <CTASection />
    </div>
  );
}
