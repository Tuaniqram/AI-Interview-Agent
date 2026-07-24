import { Brain, GitBranch, ArrowRight, Cog, Search, FileText, BarChart, CheckCircle } from 'lucide-react';

const workflows = [
  {
    title: 'Question Generation',
    desc: 'LangGraph workflow that generates one interview question per run',
    color: 'var(--action-primary)',
    nodes: [
      { id: 'init', label: 'Session Init', icon: Cog, sub: 'Initialize state & load session' },
      { id: 'phase', label: 'Phase Decision', icon: GitBranch, sub: 'Determine phase & difficulty' },
      { id: 'context', label: 'Company Context', icon: Search, sub: 'Retrieve RAG documents' },
      { id: 'generate', label: 'Question Gen', icon: FileText, sub: 'AI generates question' },
    ],
  },
  {
    title: 'Answer Evaluation',
    desc: 'LangGraph workflow that evaluates each candidate answer',
    color: '#4ade80',
    nodes: [
      { id: 'eval', label: 'Answer Eval', icon: BarChart, sub: 'Score & provide feedback' },
      { id: 'flow', label: 'Interview Flow', icon: GitBranch, sub: 'Adjust phase/difficulty' },
      { id: 'decision', label: 'Decision', icon: CheckCircle, sub: 'Continue or finish' },
    ],
  },
];

function FlowChart({ workflow }: { workflow: typeof workflows[0] }) {
  const { nodes, color, title, desc } = workflow;

  return (
    <div className="flex-1 min-w-0">
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-1">
          <div className="w-3 h-3 rounded-full" style={{ background: color }} />
          <h3 className="text-lg font-bold text-primary">{title}</h3>
        </div>
        <p className="text-sm text-secondary">{desc}</p>
      </div>

      <div className="relative">
        {nodes.map((node, i) => {
          const Icon = node.icon;
          const isLast = i === nodes.length - 1;

          return (
            <div key={node.id}>
              <div
                className="flex items-center gap-4 p-4 rounded-xl backdrop-blur-xl transition-all duration-300 hover:scale-[1.02]"
                style={{
                  background: 'rgba(20,20,25,.85)',
                  boxShadow: `0 0 0 1px ${color}22, 0 4px 20px rgba(0,0,0,.3)`,
                }}
              >
                <div
                  className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                  style={{ background: `${color}18` }}
                >
                  <Icon size={20} color={color} />
                </div>
                <div className="min-w-0">
                  <div className="text-sm font-semibold text-white">{node.label}</div>
                  <div className="text-[11px] text-zinc-400 truncate">{node.sub}</div>
                </div>
                {!isLast && <ArrowRight size={16} className="text-zinc-500 shrink-0 ml-auto" />}
              </div>

              {!isLast && (
                <div className="flex justify-center py-1.5">
                  <div className="w-px h-6" style={{ background: `${color}40` }} />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function LangGraphFlow() {
  return (
    <div>
      <div className="text-center mb-12">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold mb-4"
          style={{
            background: 'rgba(139,111,245,.15)',
color: 'var(--action-primary)',
          }}
        >
          <Brain size={14} />
          LangGraph Architecture
        </div>
        <h2 className="text-3xl md:text-4xl font-bold text-primary mb-3">
          Two Separate Workflows
        </h2>
        <p className="text-secondary text-lg max-w-2xl mx-auto">
          The interview runs as two independent LangGraph state machines — one generates questions,
          the other evaluates answers. Each is a deterministic DAG that executes in a single pass.
        </p>
      </div>

      <div className="flex flex-col lg:flex-row gap-10 lg:gap-16 max-w-5xl mx-auto">
        <FlowChart workflow={workflows[0]} />
        <div className="hidden lg:flex items-stretch">
          <div className="w-px self-stretch" style={{ background: 'linear-gradient(to bottom, transparent, rgba(255,255,255,.08), transparent)' }} />
        </div>
        <FlowChart workflow={workflows[1]} />
      </div>

      <div className="mt-12 max-w-3xl mx-auto">
        <div
          className="p-5 rounded-xl backdrop-blur-xl text-sm leading-relaxed"
          style={{
            background: 'rgba(20,20,25,.6)',
            boxShadow: '0 0 0 1px rgba(255,255,255,.04)',
          }}
        >
          <p className="text-secondary mb-3">
            <span className="font-semibold text-primary">Single-pass execution:</span> Each workflow has no branching,
            conditional edges, or cycles — it runs start-to-end every time.
          </p>
          <div className="flex flex-wrap gap-3 text-xs">
            {[
              { label: 'Question Workflow', desc: '4 sequential nodes', color: '#8b6ff5' },
              { label: 'Evaluation Workflow', desc: '3 sequential nodes', color: '#4ade80' },
              { label: 'Memory Checkpointer', desc: 'Persists state between runs', color: '#38bdf8' },
              { label: 'State Object', desc: 'Single TypedDict shared by both', color: '#fb923c' },
            ].map(item => (
              <div
                key={item.label}
                className="px-3 py-2 rounded-lg flex items-center gap-2"
                style={{ background: `${item.color}10` }}
              >
                <div className="w-2 h-2 rounded-full shrink-0" style={{ background: item.color }} />
                <div>
                  <span className="font-medium text-primary">{item.label}</span>
                  <span className="text-zinc-400 ml-1">— {item.desc}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
