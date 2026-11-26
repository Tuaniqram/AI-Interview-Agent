import { Code, Palette, BarChart, Brain, PenTool, Database, Shield, TrendingUp } from 'lucide-react';

interface CategoryCardProps {
  name: string;
  icon: string;
  count: number;
  onClick: () => void;
}

const ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  engineering: Code,
  design: Palette,
  marketing: BarChart,
  'machine-learning': Brain,
  writing: PenTool,
  data: Database,
  security: Shield,
  product: TrendingUp,
};

export function CategoryCard({ name, icon, count, onClick }: CategoryCardProps) {
  const Icon = ICON_MAP[icon] || Code;

  return (
    <button
      onClick={onClick}
      className="flex items-center gap-3 p-4 rounded-xl bg-[var(--bg-section)] border border-[var(--border-color)] hover:border-border-strong card-hover group text-left"
    >
      <div className="w-10 h-10 rounded-lg bg-action-primary-soft flex items-center justify-center shrink-0 transition-colors">
        <Icon className="w-5 h-5 text-[var(--action-primary)]" />
      </div>
      <div className="min-w-0">
        <p className="text-sm font-medium text-primary font-heading">{name}</p>
        <p className="text-xs text-muted">{count} open{count === 1 ? '' : 's'}</p>
      </div>
    </button>
  );
}
