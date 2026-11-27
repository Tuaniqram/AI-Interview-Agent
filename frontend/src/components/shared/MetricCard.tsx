import { KeyboardEvent, ReactNode } from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface MetricCardProps {
  label: string;
  value: string | number;
  trend?: 'up' | 'down' | 'neutral';
  trendLabel?: string;
  icon?: ReactNode;
  className?: string;
  onClick?: () => void;
}

/** One figure and what it counts. The number leads; the label explains it in plain words. */
export function MetricCard({ label, value, trend, trendLabel, icon, className = '', onClick }: MetricCardProps) {
  const onKeyDown = onClick
    ? (e: KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick(); } }
    : undefined;
  return (
    <div
      className={`bg-section border border-border rounded-xl px-4 py-3.5 ${onClick ? 'cursor-pointer transition-colors hover:border-border-strong hover:bg-subtle' : ''} ${className}`}
      onClick={onClick}
      onKeyDown={onKeyDown}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      <div className="flex items-center gap-1.5 text-[13px] text-secondary">
        {icon && <span className="text-tertiary [&_svg]:w-3.5 [&_svg]:h-3.5">{icon}</span>}
        <span className="truncate">{label}</span>
      </div>
      <div className="mt-1.5 flex items-baseline gap-2">
        <span className="text-[26px] leading-8 font-semibold tracking-[-0.02em] text-primary tabular">{value}</span>
        {trend === 'up' && <TrendingUp className="w-4 h-4 text-success" />}
        {trend === 'down' && <TrendingDown className="w-4 h-4 text-error" />}
      </div>
      {trendLabel && (
        <span className={`block mt-0.5 text-xs ${trend === 'up' ? 'text-success' : trend === 'down' ? 'text-error' : 'text-tertiary'}`}>
          {trendLabel} vs last period
        </span>
      )}
    </div>
  );
}
