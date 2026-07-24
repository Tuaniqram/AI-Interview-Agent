import { Quote } from 'lucide-react';

const testimonials = [
  {
    name: 'Sarah Chen',
    role: 'Head of Talent Acquisition',
    company: 'TechScale Inc.',
    quote: 'We reduced our initial screening time by 80% without sacrificing quality. The adaptive questioning surfaces skills gaps we used to miss in phone screens.',
    rating: 5,
  },
  {
    name: 'Marcus Rivera',
    role: 'CTO',
    company: 'DataFlow Labs',
    quote: 'The RAG context is a game-changer. It asks questions specifically about our stack and architecture — not generic LeetCode problems. Candidates come to the onsite already aligned.',
    rating: 5,
  },
  {
    name: 'Emily Torres',
    role: 'Engineering Manager',
    company: 'Sprint Studios',
    quote: 'Setup took 10 minutes. We uploaded our engineering docs, picked a template, and ran 50 interviews that same week. The avatar mode feels surprisingly natural.',
    rating: 4,
  },
];

function Stars({ count }: { count: number }) {
  return (
    <div className="flex gap-0.5">
      {Array.from({ length: 5 }).map((_, i) => (
        <svg key={i} className={`w-3.5 h-3.5 ${i < count ? 'text-[#fbbf24]' : 'text-[var(--border-strong)]'}`} fill="currentColor" viewBox="0 0 20 20">
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
        </svg>
      ))}
    </div>
  );
}

export function Testimonials() {
  return (
    <section className="py-24 px-6 bg-section">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-14">
          <h2 className="text-3xl md:text-4xl font-bold text-primary mb-4">Trusted by engineering teams</h2>
          <p className="text-secondary text-lg max-w-xl mx-auto">
            Companies of all sizes use AI Interview Agent to scale their hiring.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {testimonials.map(t => (
            <div
              key={t.name}
              className="p-6 rounded-2xl bg-elevated hover:bg-elevated/80 transition-all duration-300 flex flex-col"
            >
              <Quote className="w-6 h-6 text-action-primary/30 mb-3" />
              <p className="text-sm text-secondary leading-relaxed flex-1 mb-5">&ldquo;{t.quote}&rdquo;</p>
              <Stars count={t.rating} />
              <div className="mt-3 pt-3 border-t border-[var(--border-strong)]">
                <div className="text-sm font-semibold text-primary">{t.name}</div>
                <div className="text-xs text-tertiary">{t.role}, {t.company}</div>
              </div>
            </div>
          ))}
        </div>

        {/* Logo bar */}
        <div className="mt-14 pt-8 border-t border-[var(--border-strong)]">
          <p className="text-xs text-center text-tertiary uppercase tracking-widest mb-6">Used by teams at</p>
          <div className="flex flex-wrap items-center justify-center gap-x-10 gap-y-4">
            {['TechScale', 'DataFlow', 'Sprint', 'Neuralis', 'CloudHive', 'StackForge'].map(name => (
              <span key={name} className="text-sm font-semibold text-[var(--border-strong)] tracking-wider">{name}</span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
