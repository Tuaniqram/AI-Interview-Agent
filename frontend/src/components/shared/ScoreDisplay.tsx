interface ScoreDisplayProps {
  score: number | null;
  max?: number;
  /** `inline` is for table rows: the figure and a short bar, one line high. */
  size?: 'inline' | 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

function scoreColor(score: number): string {
  if (score >= 7) return 'text-success';
  if (score >= 5) return 'text-warning';
  return 'text-error';
}

function scoreBg(score: number): string {
  if (score >= 7) return 'stroke-success';
  if (score >= 5) return 'stroke-warning';
  return 'stroke-error';
}

const sizes = {
  sm: { outer: 40, stroke: 4, text: 'text-sm' },
  md: { outer: 56, stroke: 5, text: 'text-lg' },
  lg: { outer: 80, stroke: 6, text: 'text-2xl' },
};

function barColor(score: number): string {
  if (score >= 7) return 'bg-success';
  if (score >= 5) return 'bg-warning';
  return 'bg-error';
}

export function ScoreDisplay({ score, max = 10, size = 'md', showLabel = true }: ScoreDisplayProps) {
  if (size === 'inline') {
    if (score === null || score === undefined) return <span className="text-tertiary">—</span>;
    const pct = Math.max(0, Math.min(score / max, 1)) * 100;
    return (
      <span className="inline-flex items-center gap-2" aria-label={`${score.toFixed(1)} out of ${max}`}>
        <span className="w-7 text-right font-medium text-primary tabular">{score.toFixed(1)}</span>
        <span className="relative w-14 h-1.5 rounded-full bg-hover overflow-hidden" aria-hidden>
          <span className={`absolute inset-y-0 left-0 rounded-full ${barColor(score)}`} style={{ width: `${pct}%` }} />
        </span>
      </span>
    );
  }
  const ring = sizes[size as 'sm' | 'md' | 'lg'];
  if (score === null || score === undefined) {
    return (
      <div className="flex flex-col items-center gap-1">
        <div className={`rounded-full bg-hover flex items-center justify-center ${ring.text} text-muted`}
          style={{ width: ring.outer, height: ring.outer }}>
          —
        </div>
        {showLabel && <span className="text-xs text-muted">No score</span>}
      </div>
    );
  }

  const { outer, stroke, text } = ring;
  const radius = (outer - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const pct = Math.min(score / max, 1);
  const offset = circumference * (1 - pct);
  const center = outer / 2;

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative" style={{ width: outer, height: outer }}>
        <svg width={outer} height={outer} className="transform -rotate-90">
          <circle cx={center} cy={center} r={radius} fill="none" stroke="currentColor" strokeWidth={stroke}
            className="text-hover" />
          <circle cx={center} cy={center} r={radius} fill="none" strokeWidth={stroke}
            strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round"
            className={scoreBg(score)} />
        </svg>
        <span className={`absolute inset-0 flex items-center justify-center font-semibold ${text} ${scoreColor(score)}`}>
          {score.toFixed(1)}
        </span>
      </div>
      {showLabel && <span className="text-xs text-muted">/ {max}</span>}
    </div>
  );
}
