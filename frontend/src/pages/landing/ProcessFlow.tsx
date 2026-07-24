import { Upload, Settings, Play, BarChart } from 'lucide-react';

const steps = [
  {
    icon: Upload,
    title: 'Upload Company Docs',
    desc: 'Upload job descriptions, tech specs, and culture documents. The system indexes them into a vector database for context-aware questioning.',
    detail: 'PDF, Markdown, or text files',
  },
  {
    icon: Settings,
    title: 'Configure Interview',
    desc: 'Pick a template or configure from scratch — set role, question count, difficulty, and interview mode (typing, voice, or avatar).',
    detail: 'Templates save for reuse',
  },
  {
    icon: Play,
    title: 'Candidate Interviews',
    desc: 'Share the interview link. The AI conducts the full session — asking adaptive questions, evaluating answers in real time, and adjusting difficulty.',
    detail: 'Runs 24/7, no scheduling',
  },
  {
    icon: BarChart,
    title: 'Review Results',
    desc: 'Access detailed score reports with per-question breakdowns, strengths/weaknesses analysis, and comparison across candidates.',
    detail: 'Exportable reports',
  },
];

export function ProcessFlow() {
  return (
    <section className="py-24 px-6 bg-section">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-primary mb-4">From setup to results in minutes</h2>
          <p className="text-secondary text-lg max-w-xl mx-auto">
            Four simple steps to run your first AI-powered interview.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 relative">
          {/* Connector line */}
          <div className="hidden md:block absolute top-16 left-[12.5%] right-[12.5%] h-px bg-gradient-to-r from-action-primary via-action-primary/50 to-transparent" />

          {steps.map((step, i) => {
            const Icon = step.icon;
            return (
              <div key={step.title} className="relative">
                <div className="flex flex-col items-center text-center">
                  <div className="w-14 h-14 rounded-2xl bg-action-primary/15 flex items-center justify-center mb-4 relative z-10">
                    <Icon className="w-6 h-6 text-action-primary" />
                  </div>
                  <div className="w-8 h-8 rounded-full bg-action-primary text-inverse text-sm font-bold flex items-center justify-center absolute -top-1 -right-1 z-20 shadow-lg">
                    {i + 1}
                  </div>
                  <h3 className="text-sm font-semibold text-primary mb-2">{step.title}</h3>
                  <p className="text-xs text-secondary leading-relaxed mb-2">{step.desc}</p>
                  <span className="text-[10px] text-tertiary font-medium">{step.detail}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
