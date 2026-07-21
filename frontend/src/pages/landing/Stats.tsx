import { Clock, Users, BarChart3, Globe } from 'lucide-react';

const stats = [
  { icon: Clock, value: '10K+', label: 'Interviews Conducted' },
  { icon: Users, value: '50+', label: 'Active Companies' },
  { icon: BarChart3, value: '92%', label: 'Candidate Satisfaction' },
  { icon: Globe, value: '15 min', label: 'Avg. Interview Duration' },
];

export function Stats() {
  return (
    <section className="py-16 px-6 bg-[#0a0a0b]">
      <div className="max-w-5xl mx-auto">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          {stats.map(s => {
            const Icon = s.icon;
            return (
              <div key={s.label} className="text-center">
                <div className="w-10 h-10 rounded-xl bg-action-primary/10 flex items-center justify-center mx-auto mb-3">
                  <Icon className="w-5 h-5 text-action-primary" />
                </div>
                <div className="text-2xl font-bold text-[#f2f2f5]">{s.value}</div>
                <div className="text-xs text-[#8a8a94] mt-1">{s.label}</div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
