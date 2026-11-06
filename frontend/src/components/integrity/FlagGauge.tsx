import { ShieldAlert } from 'lucide-react';

interface FlagGaugeProps {
  count: number;
  max: number;
  className?: string;
}

/**
 * Live integrity flag gauge for the interview room (contract §4.5). Candidates
 * can always see how many flags they have accumulated and how close they are
 * to the termination limit — no surprises at termination time.
 */
export function FlagGauge({ count, max, className = '' }: FlagGaugeProps) {
  if (max <= 0) return null;
  const safeCount = Math.min(Math.max(count, 0), max);
  const atRisk = safeCount >= max;

  return (
    <div
      className={`flex items-center gap-2 px-3 py-1.5 rounded-full border transition-colors ${
        atRisk
          ? 'bg-error/10 border-error/30 text-error'
          : safeCount >= Math.ceil(max / 2)
            ? 'bg-warning/10 border-warning/30 text-warning'
            : 'bg-overlay border-border text-muted'
      } ${className}`}
      title={atRisk ? 'Flag limit reached — session will be terminated' : `${safeCount} of ${max} integrity flags used`}
    >
      <ShieldAlert className="w-3.5 h-3.5" />
      <span className="text-[11px] font-medium tracking-wide whitespace-nowrap">
        Integrity {safeCount}/{max}
      </span>
      <span className="flex items-center gap-1">
        {Array.from({ length: max }, (_, i) => (
          <span
            key={i}
            className={`w-1.5 h-1.5 rounded-full ${
              i < safeCount
                ? atRisk
                  ? 'bg-error'
                  : 'bg-warning'
                : 'bg-border'
            }`}
          />
        ))}
      </span>
    </div>
  );
}