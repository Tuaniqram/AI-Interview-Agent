import { Hero } from './landing/Hero';
import AnimatedFlow from './landing/AnimatedFlow';
import { Features } from './landing/Features';
import { CTASection } from './landing/CTASection';

export function Landing() {
  return (
    <div className="min-h-screen bg-[#0a0a0b]">
      <Hero />

      <section id="how-it-works" className="py-24 px-6 bg-[#141416]">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-[#f2f2f5] mb-4">How It Works</h2>
            <p className="text-[#a8a8b3] text-lg max-w-xl mx-auto">
              Your data flows through our intelligent pipeline — from input to evaluation and beyond.
            </p>
          </div>
          <AnimatedFlow />
        </div>
      </section>

      <Features />
      <CTASection />
    </div>
  );
}
