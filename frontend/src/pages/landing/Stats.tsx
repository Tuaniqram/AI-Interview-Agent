import { useState, useEffect, useRef } from 'react';
import { Clock, Users, BarChart3, Globe } from 'lucide-react';

function AnimatedCounter({ value: raw }: { value: string }) {
  const [count, setCount] = useState(0);
  const [visible, setVisible] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const match = raw.match(/^(\d+)(.*)$/);
  const target = match ? parseInt(match[1], 10) : 0;
  const suffix = match ? match[2] : raw;

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) setVisible(true);
      },
      { threshold: 0.5 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!visible) return;
    let start: number | null = null;
    const duration = 1500;

    const animate = (timestamp: number) => {
      if (!start) start = timestamp;
      const elapsed = timestamp - start;
      const progress = Math.min(elapsed / duration, 1);
      setCount(Math.floor(progress * target));
      if (progress < 1) requestAnimationFrame(animate);
    };

    requestAnimationFrame(animate);
  }, [visible, target]);

  return <div ref={ref} className="text-2xl font-bold text-primary">{count}{suffix}</div>;
}

const stats = [
  { icon: Clock, value: '10K+', label: 'Interviews Conducted' },
  { icon: Users, value: '50+', label: 'Active Companies' },
  { icon: BarChart3, value: '92%', label: 'Candidate Satisfaction' },
  { icon: Globe, value: '15 min', label: 'Avg. Interview Duration' },
];

export function Stats() {
  return (
    <section data-reveal className="py-16 px-6 bg-page">
      <div className="max-w-5xl mx-auto">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          {stats.map(s => {
            const Icon = s.icon;
            return (
              <div key={s.label} className="text-center">
                <div className="w-10 h-10 rounded-xl bg-action-primary/10 flex items-center justify-center mx-auto mb-3">
                  <Icon className="w-5 h-5 text-action-primary" />
                </div>
                <AnimatedCounter value={s.value} />
                <div className="text-xs text-muted mt-1">{s.label}</div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}