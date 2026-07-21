import { Bot, BarChart3, Brain, Database, Mic, Sparkles } from 'lucide-react';

const features = [
  {
    icon: Bot,
    title: 'Avatar Mode',
    description: 'Lifelike 3D avatar interviews with lip-sync and real-time gesture animation for an immersive candidate experience.',
  },
  {
    icon: Brain,
    title: 'Real-time Evaluation',
    description: 'LLM-powered instant scoring with detailed feedback across technical skills, communication, and problem-solving.',
  },
  {
    icon: Sparkles,
    title: 'Adaptive Questions',
    description: 'Dynamic difficulty adjustment based on candidate performance. Questions evolve with each answer.',
  },
  {
    icon: Database,
    title: 'RAG Knowledge Base',
    description: 'Company-specific context retrieval via Pinecone vector search. Every interview is tailored to your requirements.',
  },
  {
    icon: Mic,
    title: 'Voice & Typing Input',
    description: 'Support for both voice dictation and typed answers, with real-time transcription across all interview modes.',
  },
  {
    icon: BarChart3,
    title: 'Analytics Dashboard',
    description: 'Comprehensive performance tracking with score distributions, session history, and company-level insights.',
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

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {features.map((f) => (
            <div
              key={f.title}
              className="group p-6 rounded-2xl bg-[#1c1c1f] border border-[#2c2c30] hover:border-action-primary/30 hover:bg-[#1c1c1f]/80 transition-all duration-300"
            >
              <div className="w-10 h-10 rounded-xl bg-action-primary/10 flex items-center justify-center mb-4 group-hover:bg-action-primary/20 transition-colors">
                <f.icon className="w-5 h-5 text-action-primary" />
              </div>
              <h3 className="text-sm font-semibold text-[#f2f2f5] mb-2">{f.title}</h3>
              <p className="text-sm text-[#a8a8b3] leading-relaxed">{f.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
