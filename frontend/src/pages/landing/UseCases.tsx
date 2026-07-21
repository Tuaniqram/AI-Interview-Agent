import { Building2, GraduationCap, Users, Briefcase } from 'lucide-react';

const cases = [
  {
    icon: Building2,
    title: 'Enterprise Hiring',
    description: 'Screen hundreds of candidates consistently with the same evaluation criteria. Company-specific RAG ensures every question is relevant to your tech stack.',
    topics: ['Technical screenings', 'Culture fit assessment', 'Bulk candidate filtering'],
  },
  {
    icon: GraduationCap,
    title: 'Educational Assessment',
    description: 'Use for mock interviews, skill assessments, and exam preparation. Adaptive difficulty helps students identify knowledge gaps.',
    topics: ['Mock interviews', 'Skill benchmarking', 'Progress tracking'],
  },
  {
    icon: Users,
    title: 'Recruitment Agencies',
    description: 'Pre-screen candidates before presenting to clients. Generate detailed score reports and shareable evaluation summaries.',
    topics: ['Client-ready reports', 'Skill verification', 'Multi-company profiles'],
  },
  {
    icon: Briefcase,
    title: 'Internal Mobility',
    description: 'Assess current employees for promotions or role changes. Keep institutional knowledge while evaluating new competencies.',
    topics: ['Promotion assessments', 'Role transition', 'Skills inventory'],
  },
];

export function UseCases() {
  return (
    <section className="py-24 px-6 bg-[#0a0a0b]">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-[#f2f2f5] mb-4">Built for every scenario</h2>
          <p className="text-[#a8a8b3] text-lg max-w-xl mx-auto">
            From startups to enterprises — flexible enough for any hiring workflow.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {cases.map(c => {
            const Icon = c.icon;
            return (
              <div key={c.title} className="p-6 rounded-2xl bg-[#141416] hover:bg-[#1c1c1f] transition-colors">
                <div className="flex items-start gap-4">
                  <div className="w-10 h-10 rounded-xl bg-action-primary/10 flex items-center justify-center shrink-0">
                    <Icon className="w-5 h-5 text-action-primary" />
                  </div>
                  <div>
                    <h3 className="text-base font-semibold text-[#f2f2f5] mb-1.5">{c.title}</h3>
                    <p className="text-sm text-[#a8a8b3] leading-relaxed mb-3">{c.description}</p>
                    <div className="flex flex-wrap gap-2">
                      {c.topics.map(t => (
                        <span key={t} className="text-[11px] text-[#6f6f7a] bg-[#1c1c1f] px-2.5 py-1 rounded-full">{t}</span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
