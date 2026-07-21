import { TrendingUp, TrendingDown } from 'lucide-react';

interface MetricCardProps {
  label: string;
  value: string | number;
  trend?: 'up' | 'down' | 'neutral';
  icon?: React.ReactNode;
  className?: string;
}

export function MetricCard({ label, value, trend, icon, className = '' }: MetricCardProps) {
  return (
    <div className={`bg-elevated rounded-xl p-4 ${className}`}>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium text-secondary uppercase tracking-wider">{label}</span>
        <span className="text-muted">{icon}</span>
      </div>
      <div className="flex items-end gap-2">
        <span className="text-2xl font-semibold text-primary">{value}</span>
        {trend === 'up' && <TrendingUp className="w-4 h-4 text-success mb-1" />}
        {trend === 'down' && <TrendingDown className="w-4 h-4 text-error mb-1" />}
      </div>
    </div>
  );
}
