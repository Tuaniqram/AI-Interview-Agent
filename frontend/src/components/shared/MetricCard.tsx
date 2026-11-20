import { TrendingUp, TrendingDown } from 'lucide-react';

interface MetricCardProps {
  label: string;
  value: string | number;
  trend?: 'up' | 'down' | 'neutral';
  trendLabel?: string;
  icon?: React.ReactNode;
  className?: string;
  onClick?: () => void;
}

export function MetricCard({ label, value, trend, trendLabel, icon, className = '', onClick }: MetricCardProps) {
  return (
    <div className={`bg-elevated rounded-xl p-4 ${onClick ? 'cursor-pointer hover:shadow-md transition-shadow' : ''} ${className}`}
      onClick={onClick}>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium text-secondary uppercase tracking-wider">{label}</span>
        <span className="text-muted">{icon}</span>
      </div>
      <div className="flex items-end gap-2">
        <span className="text-2xl font-semibold text-primary">{value}</span>
        {trend === 'up' && <TrendingUp className="w-4 h-4 text-success mb-1" />}
        {trend === 'down' && <TrendingDown className="w-4 h-4 text-error mb-1" />}
      </div>
      {trendLabel && (
        <span className={`block mt-0.5 text-[10px] ${trend === 'up' ? 'text-success' : trend === 'down' ? 'text-error' : 'text-muted'}`}>
          {trend === 'up' ? '\u2191' : trend === 'down' ? '\u2193' : '\u2192'} {trendLabel} vs last period
        </span>
      )}
    </div>
  );
}
