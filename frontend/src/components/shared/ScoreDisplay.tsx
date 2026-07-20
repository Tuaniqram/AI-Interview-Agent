interface ScoreDisplayProps {
  score: number | null;
  max?: number;
  size?: 'sm' | 'md' | 'lg';
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

export function ScoreDisplay({ score, max = 10, size = 'md', showLabel = true }: ScoreDisplayProps) {
  if (score === null || score === undefined) {
    return (
      <div className="flex flex-col items-center gap-1">
        <div className={`rounded-full bg-hover flex items-center justify-center ${sizes[size].text} text-muted`}
          style={{ width: sizes[size].outer, height: sizes[size].outer }}>
          —
        </div>
        {showLabel && <span className="text-xs text-muted">No score</span>}
      </div>
    );
  }

  const { outer, stroke, text } = sizes[size];
  const radius = (outer - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const pct = Math.min(score / max, 1);
  const offset = circumference * (1 - pct);
  const center = outer / 2;

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={outer} height={outer} className="transform -rotate-90">
        <circle cx={center} cy={center} r={radius} fill="none" stroke="currentColor" strokeWidth={stroke}
          className="text-hover" />
        <circle cx={center} cy={center} r={radius} fill="none" strokeWidth={stroke}
          strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round"
          className={scoreBg(score)} />
      </svg>
      <span className={`font-semibold ${text} ${scoreColor(score)}`} style={{ marginTop: -outer }}>
        {score.toFixed(1)}
      </span>
      {showLabel && <span className="text-xs text-muted">/ {max}</span>}
    </div>
  );
}
