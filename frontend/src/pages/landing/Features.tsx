import { Bot, BarChart3, Brain, Database, Mic, Sparkles, Shield, Zap } from 'lucide-react';

const features = [
  {
    icon: Bot,
    title: 'Lifelike Avatar Interviews',
    description: '3D avatar with real-time lip-sync, facial expressions, and gesture animation. Candidates interact with a natural, conversational AI interviewer.',
    highlight: 'Powered by Three.js + WebGL',
  },
  {
    icon: Brain,
    title: 'Real-time LLM Evaluation',
    description: 'Instant scoring across technical skills, communication, and problem-solving. Detailed feedback for every answer with contextual analysis.',
    highlight: 'Groq LLM ~0.5s response time',
  },
  {
    icon: Database,
    title: 'RAG Knowledge Retrieval',
    description: 'Company-specific context injection via Pinecone vector search. Every question is grounded in your actual requirements and documentation.',
    highlight: 'Sub-15s retrieval + generation',
  },
  {
    icon: Sparkles,
    title: 'Adaptive Questioning',
    description: 'Difficulty adjusts dynamically based on candidate performance. Stronger answers lead to harder questions; struggling candidates receive scaffolding.',
    highlight: 'LangGraph orchestrated',
  },
  {
    icon: Mic,
    title: 'Multi-modal Input',
    description: 'Voice dictation with real-time transcription, plus traditional typed answers. Seamless switching between modes during an interview.',
    highlight: 'Speech-to-text + keyboard',
  },
  {
    icon: BarChart3,
    title: 'Analytics & Reporting',
    description: 'Score distributions, per-company trends, session history, and exportable reports. Track improvement across multiple interview rounds.',
    highlight: 'Interactive Chart.js dashboards',
  },
  {
    icon: Shield,
    title: 'Enterprise Security',
    description: 'Session-scoped data isolation, async SQLite persistence, and stateless API design. No candidate data leaks between interviews.',
    highlight: 'SQLAlchemy async + FastAPI',
  },
  {
    icon: Zap,
    title: 'Template System',
    description: 'Save interview configurations per role per company. Reuse question sets, evaluation criteria, and company context across sessions.',
    highlight: 'Role-specific presets',
  },
];

export function Features() {
  return (
    <section className="py-24 px-6 bg-[#141416]">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-[#f2f2f5] mb-4">Everything you need</h2>
          <p className="text-[#a8a8b3] text-lg max-w-xl mx-auto">
            From avatar interviews to deep analytics — a complete AI interview platform.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {features.map((f) => (
            <div
              key={f.title}
              className="group p-5 rounded-2xl bg-[#1c1c1f] hover:bg-[#1c1c1f]/80 transition-all duration-300"
            >
              <div className="w-9 h-9 rounded-xl bg-action-primary/10 flex items-center justify-center mb-3 group-hover:bg-action-primary/20 transition-colors">
                <f.icon className="w-4.5 h-4.5 text-action-primary" />
              </div>
              <h3 className="text-sm font-semibold text-[#f2f2f5] mb-1.5">{f.title}</h3>
              <p className="text-xs text-[#a8a8b3] leading-relaxed mb-3">{f.description}</p>
              <span className="text-[10px] font-medium text-[#6f6f7a] uppercase tracking-wider">{f.highlight}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
